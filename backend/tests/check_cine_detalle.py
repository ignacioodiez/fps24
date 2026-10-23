"""Self-check de GET /cines/{slug} con los datos de la BD local. Solo lectura, sin red.
Uso: docker compose exec api python tests/check_cine_detalle.py"""
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import HTTPException
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Cine, Pase
from app.services.cines import CINES_DATOS, detalle_cine, listar_cines
from app.services.tiempo import ahora_madrid
from main import CineDetalle, CineSalida, leer_cine, leer_cines

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

ahora = ahora_madrid()
hoy = datetime.combine(ahora.date(), time())
with Session(engine) as session:
    # /cines sigue igual: mismos campos y sin los de la ficha
    lista = [CineSalida.model_validate(c) for c in leer_cines(session)]
    assert len(lista) == len(CINES_DATOS) == 21, len(lista)
    assert all(not hasattr(c, "dias") for c in lista)
    assert list(CineSalida.model_fields) == ["id", "slug", "nombre", "zona", "tipo", "direccion", "web", "telefono",
                                             "lat", "lng", "tarifas", "sesiones_hoy", "peliculas_hoy"]

    try:
        leer_cine("no-existe", session)
        raise AssertionError("un slug inexistente debería dar 404")
    except HTTPException as e:
        assert e.status_code == 404

    for c in lista:
        d = CineDetalle.model_validate(detalle_cine(session, c.slug, ahora))
        # misma ficha que /cines (salvo sesiones_hoy si cambia el minuto entre consultas: aquí mismo `ahora`)
        assert CineSalida.model_validate(d.model_dump()) == CineSalida.model_validate(
            next(x for x in listar_cines(session, ahora) if x["slug"] == c.slug)), c.slug
        assert [x.fecha for x in d.dias] == [ahora.date() + timedelta(days=i) for i in range(7)], c.slug

        vistas = []
        for dia in d.dias:
            assert len({p.id for p in dia.peliculas}) == len(dia.peliculas), (c.slug, dia.fecha)
            primeras = [(p.sesiones[0].fecha_hora, p.sesiones[0].id) for p in dia.peliculas]
            assert primeras == sorted(primeras), (c.slug, dia.fecha)  # películas por su primera sesión
            for p in dia.peliculas:
                claves = [(s.fecha_hora, s.id) for s in p.sesiones]
                assert claves == sorted(claves) and claves, (c.slug, p.titulo)  # sesiones en orden
                for s in p.sesiones:
                    assert s.fecha_hora.date() == dia.fecha and s.hora == s.fecha_hora.strftime("%H:%M")
                    vistas.append((s.id, p.id))

        # Ni falta ni sobra ninguna sesión respecto a la consulta directa
        esperadas = session.exec(select(Pase.id, Pase.pelicula_id).where(
            Pase.cine_id == c.id, Pase.activo, Pase.fecha_hora >= hoy, Pase.fecha_hora < hoy + timedelta(days=7))).all()
        assert sorted(vistas) == sorted(map(tuple, esperadas)), c.slug

        # solo_hoy: sesiones hoy y ninguna activa desde mañana
        desde_manana = session.exec(select(Pase.id).where(
            Pase.cine_id == c.id, Pase.activo, Pase.fecha_hora >= hoy + timedelta(days=1))).first()
        assert d.solo_hoy == (bool(d.dias[0].peliculas) and desde_manana is None), c.slug
        print(f"  {c.slug}: {len(vistas)} sesiones en 7 días, solo_hoy={d.solo_hoy}")
    print("OK: 21 cines con 7 días, 404, orden y sesiones = consulta directa")

    # solo_hoy = True: con `ahora` en el último día con sesiones de un cine, todo lo que queda es de "hoy"
    ultimo = session.exec(select(Pase.cine_id, Pase.fecha_hora).where(Pase.activo)
                          .order_by(Pase.fecha_hora.desc())).first()
    if ultimo:
        slug = session.get(Cine, ultimo[0]).slug
        d = detalle_cine(session, slug, datetime.combine(ultimo[1].date(), time()))
        assert d["solo_hoy"] is True and d["dias"][0]["peliculas"] and not any(x["peliculas"] for x in d["dias"][1:])
        print(f"OK: solo_hoy=True para {slug} con ahora={ultimo[1].date()}")
