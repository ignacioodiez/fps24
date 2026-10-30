"""Self-check de los especiales de cines comerciales (services/destacadas.py) contra la BD local. Sin red.
Uso: docker compose exec api python tests/check_especiales_comerciales.py
Primero la selección en memoria (objetos sin guardar). Después, en la BD: un cine comercial de prueba (chk-esp-*) con
pases en una semana de 2099 sobre películas que ya existen, y una de ellas oculta un momento. Al final borra sus pases,
su cine y la ocultación que haya puesto; no crea ni borra películas."""
import itertools
import subprocess
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlmodel import Session, delete, select

from app.database.engine import engine
from app.database.models import Cine, Pase, Pelicula, PeliculaOculta
from app.newsletter import contenido
from app.services import destacadas as d
from app.services.gestor_peliculas import es_especial
from app.services.tiempo import hoy_madrid

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)

# --- La señal: la misma marca del scraper en todos los cines (resolver_pelicula -> es_especial) ---
anio = hoy_madrid().year
assert not es_especial("Una película de estreno", anio)            # estreno normal: no
assert es_especial("El resplandor", 1980)                           # reposición (película antigua)
assert es_especial("REESTRENO 4K Akira", anio) and es_especial("CICLO Terror: Carrie", anio)  # programación
print("OK: un estreno normal no lleva marca; reposiciones y ciclos sí")

# --- Ruido: fuera aunque lleven la marca, en cualquier cine ---
for titulo, generos in [("ENHYPEN WORLD TOUR BLOOD SAGA", "Música, Documental"), ("Final Champions League 2027", None),
                        ("Retransmisión: Real Madrid - Barça", None), ("Cine infantil: Coco", "Animación, Familia"),
                        ("Coco (sesión en familia)", None), ("Matinal: Los Goonies", "Aventura"),
                        ("Carmen (Ópera EN DIRECTO desde The Royal Opera House)", None), ("MANON - BALLET LIVE ROH 26-27", None),
                        ("NT Live: Hamlet", "Drama"), ("Velada de boxeo", None), ("Fórmula 1: Gran Premio", None)]:
    assert not d.es_especial_de_cine(Pelicula(titulo=titulo, generos=generos)), titulo
for titulo, generos in [("El fantasma de la ópera", "Terror, Romance"), ("Pesadilla antes de Navidad", "Fantasía, Animación, Familia"),
                        ("Mi vecino Totoro", "Animación, Familia"), ("La familia Addams", "Comedia"), ("Kids", "Drama"),
                        ("El pequeño Nicolás", "Comedia"), ("El concierto", None)]:
    assert d.es_especial_de_cine(Pelicula(titulo=titulo, generos=generos)), titulo
print("OK: el filtro de ruido quita conciertos, directos, ópera/ballet, deportes e infantiles, y deja el cine")

# --- Selección en memoria: comercial con marca sí; estreno normal o sin marca, no; ruido, no ---
LUNES, DOMINGO = date(2099, 1, 5), date(2099, 1, 11)
ids = itertools.count(1)
comercial = Cine(id=1, slug="comercial", nombre="Yelmo de prueba", tipo="comercial")
autor = Cine(id=2, slug="autor", nombre="Autor de prueba", tipo="autor")


def peli(titulo, estreno=None, generos="Drama"):
    return Pelicula(id=next(ids), titulo=titulo, tmdb_id=next(ids), nota_tmdb=8.0, votos=999, fecha_estreno=estreno, generos=generos)


def pase(p, cine, dia, especial=True):
    x = Pase(id=next(ids), pelicula_id=p.id, cine_id=cine.id, fecha_hora=datetime(2099, 1, dia, 20), es_evento_especial=especial)
    x.pelicula, x.cine_rel = p, cine
    return x


resplandor, estreno, normal, gira, autoral = (peli("El resplandor"), peli("Estreno comercial", date(2099, 1, 9)),
                                               peli("Película en cartel"), peli("BTS WORLD TOUR"), peli("Cinema Paradiso"))
pases_de = {p.id: ps for p, ps in [(resplandor, [pase(resplandor, comercial, 6)]),
                                   (estreno, [pase(estreno, comercial, 9, especial=False)]),
                                   (normal, [pase(normal, comercial, 7, especial=False)]),
                                   (gira, [pase(gira, comercial, 8)]),
                                   (autoral, [pase(autoral, autor, 7), pase(autoral, comercial, 8)])]}
elegidas = {s.pelicula.titulo: (s, ps) for s, ps, _ in d.seleccionar_especiales(pases_de, LUNES, DOMINGO)}
assert set(elegidas) == {"El resplandor", "Cinema Paradiso"}, elegidas
assert elegidas["El resplandor"][0].cine_rel.tipo == "comercial"
assert {p.cine_rel.tipo for p in elegidas["Cinema Paradiso"][1]} == {"autor", "comercial"}  # los dos cines, como alternativas
assert [s.pelicula.titulo for s, _, _ in d.seleccionar_estrenos(pases_de, LUNES, DOMINGO)] == ["Estreno comercial"]
print("OK: en memoria, el especial comercial entra; el estreno normal va a estrenos y no a especiales; ruido fuera")

# --- En la BD: /especiales, la portada y la newsletter, con una película oculta ---
SLUG = f"chk-esp-{uuid.uuid4().hex[:6]}"
LUNES_BD = datetime(2099, 1, 5, 0, 0)
oculta_puesta = None
try:
    with Session(engine) as session:
        ya_ocultas = select(PeliculaOculta.pelicula_id)
        aptas = [p for p in session.exec(select(Pelicula).where(Pelicula.tmdb_id.is_not(None), Pelicula.votos >= d.VOTOS_MIN_ESPECIAL,
                                                                  Pelicula.id.not_in(ya_ocultas))
                                         .order_by(Pelicula.votos.desc(), Pelicula.id).limit(50)).all() if d.es_especial_de_cine(p)]
        assert len(aptas) >= 3, "hacen falta 3 películas con nota en la BD local"
        visible, oculta, sin_marca = aptas[0], aptas[1], aptas[2]
        cine = Cine(slug=SLUG, nombre="Cine comercial de prueba", tipo="comercial")
        session.add(cine)
        session.flush()
        mios = [Pase(pelicula_id=visible.id, cine_id=cine.id, fecha_hora=datetime(2099, 1, 6, 20), es_evento_especial=True),
                Pase(pelicula_id=oculta.id, cine_id=cine.id, fecha_hora=datetime(2099, 1, 6, 22), es_evento_especial=True),
                Pase(pelicula_id=sin_marca.id, cine_id=cine.id, fecha_hora=datetime(2099, 1, 7, 20), es_evento_especial=False)]
        session.add_all(mios)
        session.add(PeliculaOculta(pelicula_id=oculta.id, motivo="check_especiales_comerciales"))
        session.commit()
        oculta_puesta = oculta.id
        ids_bd = dict(visible=visible.id, oculta=oculta.id, sin_marca=sin_marca.id)

        pagina = d.leer_pagina(session, d.seleccionar_especiales, 0, LUNES_BD)
        por_peli = {x["pelicula"].id: x for x in pagina["peliculas"]}
        assert ids_bd["visible"] in por_peli, pagina
        assert por_peli[ids_bd["visible"]]["sesion"].cine_slug == SLUG  # la tarjeta enlaza a /cines/<slug>
        assert ids_bd["oculta"] not in por_peli and ids_bd["sin_marca"] not in por_peli
        portada = d.leer_destacadas(session, LUNES_BD)
        assert [x["pelicula"].id for x in portada["especiales"]] == [ids_bd["visible"]], portada["especiales"]
        news = contenido.datos_semana(session, datetime(2099, 1, 5, 16))
        assert [(x["id"], x["cine"]) for x in news["especiales"]] == [(ids_bd["visible"], "Cine comercial de prueba")], news
        print("OK: /especiales, portada y newsletter: el especial comercial entra con su cine; sin marca y oculta, no")
finally:
    with Session(engine) as session:
        if oculta_puesta:
            session.exec(delete(PeliculaOculta).where(PeliculaOculta.pelicula_id == oculta_puesta,
                                                      PeliculaOculta.motivo == "check_especiales_comerciales"))
        session.exec(delete(Pase).where(Pase.cine_id.in_(select(Cine.id).where(Cine.slug == SLUG))))
        session.exec(delete(Cine).where(Cine.slug == SLUG))
        session.commit()
    print("Limpieza: pases, cine y ocultación de prueba borrados")

print("TODO OK: check_especiales_comerciales")
