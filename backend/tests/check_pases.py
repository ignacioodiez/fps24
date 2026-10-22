"""Self-check de registrar_pase. Uso: docker compose exec api python tests/check_pases.py
Todo ocurre en una sesión que termina en rollback: no deja datos."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase, Pelicula
from app.services.pases import registrar_pase

CINE = "Cine de Prueba Check"
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
    finally:
        session.rollback()
