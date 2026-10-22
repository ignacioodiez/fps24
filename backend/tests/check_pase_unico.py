"""Self-check de la migración 0006: identidad única de pase, cine_id NOT NULL y la carrera en registrar_pase.
Uso: docker compose exec api python tests/check_pase_unico.py
La carrera necesita commits de verdad: lo que crea lo borra al final."""
import sys
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase, Pelicula
from app.services.cines import obtener_o_crear_cine
from app.services.pases import registrar_pase

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

CINE = "Cine de Prueba Check Unico"
FECHA = datetime(2099, 3, 1, 20, 0)


def choca(session, **campos):
    try:
        with session.begin_nested():
            session.add(Pase(fecha_hora=FECHA, **campos))
        return False
    except IntegrityError:
        return True


with Session(engine) as session:
    pelicula_id = session.exec(select(Pelicula.id)).first()
    assert pelicula_id, "hace falta al menos una película en la BD"
    cine_id = obtener_o_crear_cine(session, CINE).id
    session.commit()

try:
    with Session(engine) as session:
        try:
            assert not choca(session, cine_id=cine_id, pelicula_id=pelicula_id, sala=None, idioma="VOSE")
            # NULL y '' son la misma sala
            assert choca(session, cine_id=cine_id, pelicula_id=pelicula_id, sala=None, idioma="VOSE")
            assert choca(session, cine_id=cine_id, pelicula_id=pelicula_id, sala="", idioma="VOSE")
            assert not choca(session, cine_id=cine_id, pelicula_id=pelicula_id, sala="Sala 2", idioma="VOSE")
            assert not choca(session, cine_id=cine_id, pelicula_id=pelicula_id, sala=None, idioma="Español")
            assert choca(session, cine_id=None, pelicula_id=pelicula_id, sala="Sala 3", idioma="VOSE"), "cine_id NULL"
            print("OK: índice único de pase y cine_id NOT NULL")
        finally:
            session.rollback()

    # Carrera: b no ve el pase sin commit de a; su INSERT espera al índice y choca cuando a hace commit
    base = dict(cine=CINE, pelicula_id=pelicula_id, fecha_hora=FECHA, sala="Sala 1", idioma="VOSE",
                precio=None, link_compra=None, es_evento_especial=False)
    with Session(engine) as a, Session(engine) as b:
        assert registrar_pase(a, **base) == "creado"
        threading.Timer(1, a.commit).start()
        assert registrar_pase(b, **base) == "actualizado"
        b.commit()
        assert len(b.exec(select(Pase).where(Pase.cine_id == cine_id)).all()) == 1
    print("OK: registrar_pase sobrevive a la carrera con otra ejecución")
finally:
    with Session(engine) as session:
        session.exec(delete(Pase).where(Pase.cine_id == cine_id))
        session.exec(delete(Cine).where(Cine.id == cine_id))
        session.commit()
