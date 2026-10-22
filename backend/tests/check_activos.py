"""Self-check: GET /pases y GET /pelicula/{id} solo devuelven pases activos, en orden (fecha_hora, id).
Uso: docker compose exec api python tests/check_activos.py
Llama a los endpoints como funciones, sin servidor. Todo termina en rollback: no deja datos."""
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase, Pelicula
from app.services.cines import obtener_o_crear_cine
from main import PaseConPelicula, PeliculaDetalle, leer_detalle_pelicula, leer_pases

CINE = "Cine de Prueba Check Activos"
FECHA = datetime(2099, 1, 1, 20, 0)

with Session(engine) as session:
    try:
        pelicula_id = session.exec(select(Pelicula.id)).first()
        assert pelicula_id, "hace falta al menos una película en la BD"
        cine_id = obtener_o_crear_cine(session, CINE).id
        # Misma fecha_hora en los tres: el desempate tiene que ser por id
        for sala, activo in [("Sala A", True), ("Sala B", False), ("Sala C", True)]:
            session.add(Pase(cine_id=cine_id, sala=sala, fecha_hora=FECHA, pelicula_id=pelicula_id, activo=activo))
        session.flush()
        ids_activos = sorted(p.id for p in session.exec(select(Pase).where(Pase.cine_id == cine_id, Pase.activo)).all())

        pases = leer_pases(session)
        assert all(p.activo for p in pases)
        assert [p.id for p in pases if p.cine == CINE] == ids_activos
        assert [(p.fecha_hora, p.id) for p in pases] == sorted((p.fecha_hora, p.id) for p in pases)
        print("OK: /pases solo devuelve activos, ordenados por (fecha_hora, id)")

        detalle = PeliculaDetalle.model_validate(leer_detalle_pelicula(pelicula_id, session))
        mios = [p for p in detalle.pases if p.cine == CINE]
        assert [p.sala for p in mios] == ["Sala A", "Sala C"], mios
        activos = session.exec(select(Pase).where(Pase.pelicula_id == pelicula_id, Pase.activo)).all()
        assert len(detalle.pases) == len(activos)
        assert [p.fecha_hora for p in detalle.pases] == sorted(p.fecha_hora for p in detalle.pases)
        # leer_detalle_pelicula no debe desvincular los pases inactivos de la película
        session.flush()
        assert len(session.exec(select(Pase).where(Pase.cine_id == cine_id, Pase.pelicula_id == pelicula_id)).all()) == 3
        print("OK: /pelicula/{id} solo devuelve activos, ordenados")

        # fecha_estreno: campo opcional en la película de /pases y de /pelicula/{id} (null si no hay)
        pelicula = session.get(Pelicula, pelicula_id)
        for valor in (date(2026, 10, 23), None):
            pelicula.fecha_estreno = valor
            session.add(pelicula)
            session.flush()
            salida = [PaseConPelicula.model_validate(p).model_dump(mode="json") for p in leer_pases(session)]
            mio = next(p for p in salida if p["cine"] == CINE)
            assert mio["pelicula"]["fecha_estreno"] == (valor and valor.isoformat()), mio["pelicula"]
            detalle = PeliculaDetalle.model_validate(leer_detalle_pelicula(pelicula_id, session)).model_dump(mode="json")
            assert detalle["fecha_estreno"] == (valor and valor.isoformat()), detalle["fecha_estreno"]
        print("OK: fecha_estreno en /pases y /pelicula/{id}")

        # votos y director: opcionales solo en /pelicula/{id} (null si no hay); /pases no cambia
        for votos, director in ((6, "Justine Triet, Otra Persona"), (None, None)):
            pelicula.votos, pelicula.director = votos, director
            session.add(pelicula)
            session.flush()
            detalle = PeliculaDetalle.model_validate(leer_detalle_pelicula(pelicula_id, session)).model_dump(mode="json")
            assert (detalle["votos"], detalle["director"]) == (votos, director), detalle
            mio = next(PaseConPelicula.model_validate(p).model_dump(mode="json") for p in leer_pases(session) if p.cine == CINE)
            assert "votos" not in mio["pelicula"] and "director" not in mio["pelicula"], mio["pelicula"]
        print("OK: votos y director en /pelicula/{id}")
    finally:
        session.rollback()
