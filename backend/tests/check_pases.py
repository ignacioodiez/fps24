"""Self-check de registrar_pase y cerrar_ejecucion. Uso: docker compose exec api python tests/check_pases.py
Todo ocurre en una sesión que termina en rollback: no deja datos."""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase, Pelicula
from app.services.pases import _ahora_utc, cerrar_ejecucion, registrar_pase

CINE = "Cine de Prueba Check"
OTRO_CINE = "Cine de Prueba Check Otro"
FECHA = datetime(2099, 1, 1, 20, 0)

with Session(engine) as session:
    try:
        pelicula_id = session.exec(select(Pelicula.id)).first()
        assert pelicula_id, "hace falta al menos una película en la BD"
        base = dict(cine=CINE, pelicula_id=pelicula_id, fecha_hora=FECHA, idioma="VOSE",
                    precio="7€", link_compra="https://a", es_evento_especial=False)

        def pases():
            return session.exec(select(Pase).where(Pase.cine == CINE)).all()

        # Crear
        assert registrar_pase(session, sala="Sala 1", **base) == "creado"
        [p] = pases()
        assert p.cine == CINE and p.cine_id and p.activo and p.visto_ultima_vez
        assert p.visto_ultima_vez.tzinfo is None
        visto_antes = p.visto_ultima_vez

        # Actualizar sin duplicar
        p.activo = False
        assert registrar_pase(session, sala="Sala 1", **{**base, "precio": "9€",
                              "link_compra": "https://b", "es_evento_especial": True}) == "actualizado"
        [p] = pases()
        assert (p.precio, p.link_compra, p.es_evento_especial, p.activo) == ("9€", "https://b", True, True)
        assert p.visto_ultima_vez >= visto_antes

        # Otra sala es otro pase
        assert registrar_pase(session, sala="Sala 2", **base) == "creado"
        assert len(pases()) == 2

        # Sala None equivale a ""
        assert registrar_pase(session, sala=None, **base) == "creado"
        assert registrar_pase(session, sala="", **base) == "actualizado"
        assert registrar_pase(session, sala=None, **base) == "actualizado"
        assert len(pases()) == 3

        print("OK: registrar_pase pasa todas las comprobaciones")

        # --- cerrar_ejecucion ---
        salas = ["Sala 1", "Sala 2", "Sala 3", "Sala 4"]
        for sala in salas:
            registrar_pase(session, sala=sala, **base)
        registrar_pase(session, sala="Sala 1", **{**base, "fecha_hora": datetime(2000, 1, 1)})  # pasado
        registrar_pase(session, sala="Sala 1", **{**base, "cine": OTRO_CINE})
        cine = session.get(Cine, pases()[0].cine_id)
        otro = session.exec(select(Pase).where(Pase.cine == OTRO_CINE)).one()

        def nueva_ejecucion(salas_vistas):
            """Simula una ejecución que solo ve `salas_vistas` de los pases futuros de CINE."""
            antes = _ahora_utc() - timedelta(hours=1)
            for p in pases() + [otro]:
                p.activo, p.visto_ultima_vez = True, antes
            cine.ultima_ejecucion_ok = None
            session.flush()
            previos = {cine.id: sum(p.fecha_hora == FECHA for p in pases())}
            inicio = _ahora_utc()
            for sala in salas_vistas:
                registrar_pase(session, sala=sala, **base)
            return cerrar_ejecucion(session, inicio, previos)

        # Cierre normal: 3 de 5 pases (Sala None/Sala 1..4 en FECHA) vistos = más de la mitad
        assert len([p for p in pases() if p.fecha_hora == FECHA]) == 5
        r = nueva_ejecucion(["Sala 1", "Sala 2", "Sala 3"])
        assert r[cine.slug] == dict(vistos=3, desactivados=3, saltado_por_salvaguarda=False), r
        activos = {(p.sala, p.fecha_hora.year) for p in pases() if p.activo}
        assert activos == {("Sala 1", 2099), ("Sala 2", 2099), ("Sala 3", 2099)}, activos
        assert cine.ultima_ejecucion_ok is not None
        # Un cine sin pases tocados no se procesa
        assert otro.activo and session.get(Cine, otro.cine_id).slug not in r

        # Salvaguarda: 2 de 5 < la mitad -> no desactiva nada
        r = nueva_ejecucion(["Sala 1", "Sala 2"])
        assert r[cine.slug] == dict(vistos=2, desactivados=0, saltado_por_salvaguarda=True), r
        assert all(p.activo for p in pases())
        assert cine.ultima_ejecucion_ok is None

        print("OK: cerrar_ejecucion pasa todas las comprobaciones")
    finally:
        session.rollback()
