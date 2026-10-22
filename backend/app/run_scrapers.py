"""Lanza los scrapers del registro y el mantenimiento de películas.
Uso: python -m app.run_scrapers [--solo dore,equis]"""
import argparse
import sys
import time
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import text
from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.cines import (cine_estudio, cine_paz, cinesa, cineteca, dore, embajadores, equis, golem,
                                mk2_palacio_hielo, renoir, verdi, yelmo_ideal)
from app.scrapers.comun import obtener_logger
from app.services import tmdb
from app.services.gestor_peliculas import limpiar_peliculas, reintentar_sin_tmdb
from app.services.pases import ejecutar_scraper

log = obtener_logger("app.scrapers.run_scrapers")

# Clave del advisory lock de Postgres: una sola ejecución a la vez (cron + /actualizar).
CANDADO = 240_024


@dataclass(frozen=True)
class Scraper:
    nombre: str        # nombre corto, el del módulo: para --solo
    funcion: Callable  # scrapear_<nombre>
    cines: list        # la constante CINES del módulo


def _desde(modulo) -> Scraper:
    nombre = modulo.__name__.rsplit(".", 1)[1]
    return Scraper(nombre, getattr(modulo, f"scrapear_{nombre}"), modulo.CINES)


# En el orden de ejecución
REGISTRO = [_desde(m) for m in (dore, cineteca, cine_estudio, equis, renoir, golem, embajadores,
                                cine_paz, mk2_palacio_hielo, yelmo_ideal, cinesa)]

# Fuera de la ejecución normal (con el motivo); siguen funcionando con --solo
DESHABILITADOS = {"verdi": "captcha de SiteGround desde IPs de Render; pendiente de nueva fuente"}
_MODULOS_DESHABILITADOS = {"verdi": verdi}


def elegir(solo: str = None) -> list:
    """Scrapers de "dore,equis" en el orden del registro (los deshabilitados al final, solo si se piden);
    todos los del registro si solo es None. ValueError si no existe."""
    if solo is None:
        return REGISTRO
    nombres = {n.strip() for n in solo.split(",") if n.strip()}
    desconocidos = nombres - {s.nombre for s in REGISTRO} - DESHABILITADOS.keys()
    if desconocidos or not nombres:
        raise ValueError(f"Scraper desconocido: {', '.join(sorted(desconocidos)) or '(vacío)'}. "
                         f"Válidos: {', '.join([s.nombre for s in REGISTRO] + list(DESHABILITADOS))}")
    return ([s for s in REGISTRO if s.nombre in nombres]
            + [_desde(_MODULOS_DESHABILITADOS[n]) for n in DESHABILITADOS if n in nombres])


class _Candado:
    """pg_try_advisory_lock en una conexión propia (autocommit, para no dejar una transacción abierta
    durante toda la ejecución). Sin Postgres (SQLite) no hace nada y siempre se obtiene."""

    def __enter__(self):
        self.conn = None
        if engine.dialect.name != "postgresql":
            return True
        self.conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        obtenido = self.conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": CANDADO}).scalar()
        if not obtenido:
            self.conn.close()
            self.conn = None
        return obtenido

    def __exit__(self, *exc):
        if self.conn is not None:
            try:
                self.conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": CANDADO})
            finally:
                self.conn.close()  # cerrar la conexión también libera el candado


def lanzar_todo(solo: str = None):
    """Ejecuta los scrapers (todos o los de `solo`) y el mantenimiento. Devuelve {nombre: resultado}
    o None si ya había otra ejecución en marcha."""
    scrapers = elegir(solo)
    inicio = time.time()
    with _Candado() as obtenido:
        if not obtenido:
            log.warning("Ya hay otra ejecución de lanzar_todo en marcha: esta no hace nada")
            return None
        tmdb.reiniciar_cortacircuito()
        peticiones_previas = tmdb.peticiones
        resultados = {}
        try:
            for scraper in scrapers:
                log.info("=== %s ===", scraper.nombre)
                t0 = time.time()
                try:
                    cierre, ok = ejecutar_scraper(scraper.funcion, scraper.cines), True
                except Exception:
                    log.error("%s: falla; no se cierra su ejecución y se sigue con el siguiente",
                              scraper.nombre, exc_info=True)
                    cierre, ok = {}, False
                resultados[scraper.nombre] = dict(ok=ok, segundos=time.time() - t0, cines=cierre)

            log.info("=== mantenimiento de películas ===")
            try:
                with Session(engine) as session:
                    log.info("Limpieza de películas: %s", limpiar_peliculas(session))
                    log.info("Reintento TMDB: %s", reintentar_sin_tmdb(session))
                    session.commit()
            except Exception:
                log.error("Falla el mantenimiento de películas", exc_info=True)
        finally:
            tmdb.reiniciar_cortacircuito()

    _imprimir_resumen(resultados, tmdb.peticiones - peticiones_previas, time.time() - inicio)
    return resultados


def _imprimir_resumen(resultados: dict, peticiones_tmdb: int, segundos: float):
    print("\n===========================================================")
    for nombre, motivo in DESHABILITADOS.items():
        if nombre not in resultados:
            print(f"{nombre:<18} DESHABILITADO: {motivo}")
    for nombre, r in resultados.items():
        print(f"{nombre:<18} {'OK' if r['ok'] else 'FALLO':<6} {r['segundos']:6.0f} s")
        for slug, c in r["cines"].items():
            salvaguarda = "  (SALVAGUARDA: no se desactiva nada)" if c["saltado_por_salvaguarda"] else ""
            print(f"    {slug:<24} creados {c.get('creados', '?'):>4} · actualizados {c.get('actualizados', '?'):>4}"
                  f" · desactivados {c['desactivados']:>4}{salvaguarda}")
    print(f"Peticiones a TMDB: {peticiones_tmdb}")
    print(f"⏱️ Tiempo total de ejecución: {int(segundos // 60)} min {int(segundos % 60)} s")
    print("===========================================================\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo", help="nombres cortos separados por comas: " + ",".join(s.nombre for s in REGISTRO))
    args = parser.parse_args(argv)
    try:
        elegir(args.solo)
    except ValueError as e:
        parser.error(str(e))
    resultados = lanzar_todo(args.solo)
    # 1 si algún scraper falla, para que el cron de Render lo marque
    return 1 if resultados and not all(r["ok"] for r in resultados.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
