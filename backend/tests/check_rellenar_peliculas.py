"""Self-check de los datos nuevos de TMDB (migración 0007) y del backfill app.rellenar_peliculas, sin red.
Uso: docker compose exec api python tests/check_rellenar_peliculas.py
Lo que toca la BD va en una transacción que acaba en rollback (los commits del backfill son savepoints)."""
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete
from sqlmodel import Session, select

from app import rellenar_peliculas
from app.database.engine import engine
from app.database.models import Pase, Pelicula
from app.services import tmdb
from app.services.pases import registrar_pase


def respuesta(tmdb_id, paises):
    """Respuesta de /movie/{id} con append_to_response, recortada a lo que se lee."""
    return {
        "id": tmdb_id, "original_title": "Anatomie d'une chute", "original_language": "fr",
        "release_date": "2023-05-21", "vote_average": 7.7, "vote_count": 3210, "imdb_id": "tt17009710",
        "genres": [{"name": "Drama"}], "translations": {"translations": []},
        "credits": {"crew": [{"job": "Director", "name": "Justine Triet"}, {"job": "Writer", "name": "Arthur Harari"},
                             {"job": "Director", "name": "Otra Persona"}]},
        "release_dates": {"results": [{"iso_3166_1": p, "release_dates": f} for p, f in paises.items()]},
    }


CON_ES = respuesta(1, {
    "FR": [{"type": 3, "release_date": "2023-08-23T00:00:00.000Z"}],
    "ES": [{"type": 1, "release_date": "2023-09-25T00:00:00.000Z"},   # festival (San Sebastián): no cuenta
           {"type": 3, "release_date": "2023-11-03T00:00:00.000Z"},
           {"type": 2, "release_date": "2023-10-27T00:00:00.000Z"},   # limitado: el más temprano
           {"type": 4, "release_date": "2023-01-01T00:00:00.000Z"}],  # digital: no cuenta
})
SIN_ES = respuesta(2, {"FR": [{"type": 3, "release_date": "2023-08-23T00:00:00.000Z"}],
                       "ES": [{"type": 4, "release_date": "2024-02-01T00:00:00.000Z"}]})

get_real = tmdb._get
tmdb._get = lambda ruta, **p: {"/movie/1": CON_ES, "/movie/2": SIN_ES}[ruta]
try:
    d = tmdb.datos_por_id(1)
    assert (d["votos"], d["nota"], d["idioma_original"], d["imdb_id"]) == (3210, 7.7, "fr", "tt17009710"), d
    assert d["director"] == "Justine Triet, Otra Persona", d["director"]
    assert d["fecha_estreno"] == date(2023, 10, 27), d["fecha_estreno"]
    assert tmdb.datos_por_id(2)["fecha_estreno"] is None
    assert tmdb.estreno_es({}) is None
    print("OK: datos_por_id (votos, director, imdb, estreno ES)")

    # --- backfill ---
    with engine.connect() as conn, conn.begin() as externa:
        with Session(bind=conn, join_transaction_mode="create_savepoint") as session:
            session.exec(delete(Pase))
            session.exec(delete(Pelicula))
            session.add_all([Pelicula(titulo="Anatomía de una caída", tmdb_id=1, nota_tmdb=7.0),
                             Pelicula(titulo="Sin estreno", tmdb_id=2),
                             Pelicula(titulo="Sin TMDB")])
            session.commit()

            r = rellenar_peliculas.rellenar(session, dry_run=True, pausa=0)
            assert r == dict(revisadas=2, cambiadas=2, con_estreno_es=1, sin_estreno_es=1, interrumpido=False), r
            assert session.exec(select(Pelicula).where(Pelicula.tmdb_id == 1)).one().votos is None  # dry-run no escribe

            r = rellenar_peliculas.rellenar(session, pausa=0)
            assert r["cambiadas"] == 2, r
            p = session.exec(select(Pelicula).where(Pelicula.tmdb_id == 1)).one()
            assert (p.nota_tmdb, p.votos, p.fecha_estreno, p.director) == (7.7, 3210, date(2023, 10, 27),
                                                                           "Justine Triet, Otra Persona")
            assert rellenar_peliculas.rellenar(session, pausa=0)["cambiadas"] == 0  # idempotente
            assert rellenar_peliculas.rellenar(session, limite=1, pausa=0)["revisadas"] == 1

            # Cortacircuito: para en la primera que falla
            def falla(ruta, **p):
                raise tmdb.TmdbNoDisponible("simulado")
            tmdb._get = falla
            assert rellenar_peliculas.rellenar(session, pausa=0) == dict(
                revisadas=0, cambiadas=0, con_estreno_es=0, sin_estreno_es=0, interrumpido=True)
            print("OK: rellenar_peliculas (dry-run, idempotente, límite, cortacircuito)")

            # --- registrar_pase: creado_en solo al crear ---
            antes = datetime.now(timezone.utc).replace(tzinfo=None)
            datos = dict(cine="Cine de Prueba Rellenar", pelicula_id=p.id, fecha_hora=datetime(2030, 1, 1, 20),
                         sala=None, idioma="VOSE", precio=None, link_compra=None, es_evento_especial=False)
            assert registrar_pase(session, **datos) == "creado"
            pase = session.exec(select(Pase).where(Pase.pelicula_id == p.id)).one()
            creado = pase.creado_en
            assert creado and creado >= antes.replace(microsecond=0), creado
            assert registrar_pase(session, **datos) == "actualizado" and pase.creado_en == creado
            print("OK: registrar_pase creado_en")
        externa.rollback()
finally:
    tmdb._get = get_real
    tmdb.reiniciar_cortacircuito()
