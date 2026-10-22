"""Self-check: GET /pases y GET /pelicula/{id} solo devuelven pases activos, en orden (fecha_hora, id).
Uso: docker compose exec api python tests/check_activos.py
Llama a los endpoints como funciones, sin servidor. Todo termina en rollback: no deja datos."""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase, Pelicula
from main import PeliculaDetalle, leer_detalle_pelicula, leer_pases

CINE = "Cine de Prueba Check Activos"
FECHA = datetime(2099, 1, 1, 20, 0)

with Session(engine) as session:
    try:
        pelicula_id = session.exec(select(Pelicula.id)).first()
        assert pelicula_id, "hace falta al menos una película en la BD"
        # Misma fecha_hora en los tres: el desempate tiene que ser por id
        for sala, activo in [("Sala A", True), ("Sala B", False), ("Sala C", True)]:
            session.add(Pase(cine=CINE, sala=sala, fecha_hora=FECHA, pelicula_id=pelicula_id, activo=activo))
        session.flush()
        ids_activos = sorted(p.id for p in session.exec(select(Pase).where(Pase.cine == CINE, Pase.activo)).all())

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
        assert len(session.exec(select(Pase).where(Pase.cine == CINE, Pase.pelicula_id == pelicula_id)).all()) == 3
        print("OK: /pelicula/{id} solo devuelve activos, ordenados")
    finally:
        session.rollback()
