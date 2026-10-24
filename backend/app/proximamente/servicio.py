"""Próximos estrenos en cines en España desde TMDB: /discover/movie (region=ES, estreno en cines limitado o normal) y,
de las que pasan los filtros, /movie/{id} con release_dates para la fecha española, el título y la sinopsis.

Umbrales (los dos primeros por variable de entorno, para ajustarlos en Render sin desplegar):
- PROXIMAMENTE_POPULARIDAD_MIN (3): popularidad de TMDB mínima. Lo que aún no se ha estrenado casi no tiene votos, así
  que la popularidad es lo que separa un estreno real de una ficha que nadie mira. Basta con cumplir uno de los dos.
- PROXIMAMENTE_VOTOS_MIN (10): o al menos estos votos (las que ya pasaron por festivales).
- PAGINAS_MAX (5): discover va por popularidad, 20 por página: se miran las 100 más populares.
Fuera también: sin póster, adultas y eventos (es_cine: giras, óperas, directos, documentales musicales), que ya salen
como especiales cuando tienen pases."""
import os
import time
from datetime import date

from app.database.models import Pelicula
from app.services import tmdb
from app.services.destacadas import es_cine

POPULARIDAD_MIN = float(os.getenv("PROXIMAMENTE_POPULARIDAD_MIN", "3"))
VOTOS_MIN = int(os.getenv("PROXIMAMENTE_VOTOS_MIN", "10"))
PAGINAS_MAX = 5
PAUSA = 0.1  # s entre peticiones: unas 10/s, muy por debajo del límite de TMDB (~40/s)


def descubrir(desde: date, hasta: date) -> list:
    """Resultados de discover con estreno en España entre `desde` y `hasta`, por popularidad."""
    resultados = []
    for pagina in range(1, PAGINAS_MAX + 1):
        datos = tmdb._get("/discover/movie", region="ES", with_release_type="2|3", language="es-ES",
                          sort_by="popularity.desc", include_adult="false", page=pagina,
                          **{"release_date.gte": desde.isoformat(), "release_date.lte": hasta.isoformat()})
        resultados += datos.get("results", [])
        if pagina >= datos.get("total_pages", 0):
            break
        time.sleep(PAUSA)
    return resultados


def pasa_umbral(r: dict) -> bool:
    return bool(r.get("poster_path")) and not r.get("adult") and (
        (r.get("popularity") or 0) >= POPULARIDAD_MIN or (r.get("vote_count") or 0) >= VOTOS_MIN)


def fecha_espanola(detalles: dict, desde: date, hasta: date):
    """(fecha, confirmada) del estreno en cines en España entre `desde` y `hasta`, o None si no es un próximo estreno.
    Confirmada: TMDB tiene una sola fecha española de cine (tipo 2 limitado o 3) en la ventana. Prevista (False): tiene
    varias distintas (se toma la primera) o ninguna española y la fecha es la general. None: ya se estrenó en cines en
    España (reestreno) o la fecha española cae fuera de la ventana."""
    fechas = {(f["type"], date.fromisoformat(f["release_date"][:10]))
              for pais in detalles.get("release_dates", {}).get("results", []) if pais.get("iso_3166_1") == "ES"
              for f in pais.get("release_dates", []) if f.get("type") in (2, 3) and f.get("release_date")}
    if any(tipo == 3 and f < desde for tipo, f in fechas):
        return None
    if fechas:
        en_ventana = sorted({f for _, f in fechas if desde <= f <= hasta})
        return (en_ventana[0], len(en_ventana) == 1) if en_ventana else None
    general = (detalles.get("release_date") or "")[:10]
    return (date.fromisoformat(general), False) if general and desde <= date.fromisoformat(general) <= hasta else None


def candidatos(desde: date, hasta: date) -> list:
    """Filas para estreno_proximo. Lanza tmdb.TmdbNoDisponible si TMDB falla (el cron no toca la tabla)."""
    vistos, filas = set(), []
    for r in descubrir(desde, hasta):
        if r["id"] in vistos or not pasa_umbral(r):
            continue
        vistos.add(r["id"])
        time.sleep(PAUSA)
        det = tmdb._get(f"/movie/{r['id']}", language="es-ES", append_to_response="release_dates")
        generos = ", ".join(g["name"] for g in det.get("genres", []))
        titulo = det.get("title") or r.get("title")
        fecha = fecha_espanola(det, desde, hasta)
        if not fecha or not det.get("poster_path") or not titulo or not es_cine(Pelicula(titulo=titulo, generos=generos)):
            continue
        filas.append(dict(
            tmdb_id=r["id"], titulo=titulo, titulo_original=det.get("original_title"), fecha_es=fecha[0],
            fecha_confirmada=fecha[1], poster_path=det["poster_path"], sinopsis=det.get("overview") or None,
            popularidad=det.get("popularity"), votos=det.get("vote_count"), generos=generos or None,
            idioma_original=det.get("original_language")))
    return filas
