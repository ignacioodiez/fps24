"""Self-check de GET /estrenos y GET /especiales con los datos de la BD local. Solo lectura, sin red.
Uso: docker compose exec api python tests/check_estrenos_especiales.py
Imprime los títulos de la semana actual para revisar a mano que no se cuela ballet, ópera ni conciertos."""
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.database.engine import engine
from app.database.models import Pelicula
from app.proximamente.estrenos import leer_estrenos
from app.services import destacadas as d
from app.services.tiempo import ahora_madrid
from main import Destacadas, PaginaSemana

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

# --- es_cine, sin BD ---
for titulo, generos in [("Carmen (Ópera EN DIRECTO desde The Royal Opera House)", None),
                        ("MANON - BALLET LIVE ROH 26-27", None), ("Met Opera: La Traviata", None),
                        ("SEVENTEEN WORLD TOUR NEW_", "Música, Documental"), ("El lago de los cisnes (en diferido)", None),
                        ("NT Live: Hamlet", "Drama"), ("Un concierto cualquiera", "Documental, Música")]:
    assert not d.es_cine(Pelicula(titulo=titulo, generos=generos)), titulo
for titulo, generos in [("El fantasma de la ópera", "Terror, Romance"), ("Cinema Paradiso", "Drama, Romance"),
                        ("My Fair Lady", "Comedia, Música, Drama"), ("El concierto", None)]:
    assert d.es_cine(Pelicula(titulo=titulo, generos=generos)), titulo
print("OK: es_cine")

ahora = ahora_madrid()
with Session(engine) as session:
    paginas = {}
    # /estrenos de la 0 a la 8 (con los próximos estrenos sin sesiones detrás), /especiales de la 0 a la 3
    for tipo, leer, maximo in (("estrenos", lambda n: leer_estrenos(session, n, ahora), d.SEMANAS_MAX_ESTRENOS),
                               ("especiales", lambda n: d.leer_pagina(session, d.seleccionar_especiales, n, ahora), d.SEMANAS_MAX)):
        for n in range(maximo + 1):
            completa = PaginaSemana.model_validate(leer(n))
            con = [x for x in completa.peliculas if not x.sin_sesiones]
            assert completa.peliculas[:len(con)] == con, "las sin sesiones van detrás"
            assert all(not x.sin_sesiones for x in con) and (tipo == "estrenos" or len(con) == len(completa.peliculas))
            p = completa.model_copy(update={"peliculas": con})  # el resto de comprobaciones, sobre las de sesiones
            paginas[tipo, n] = p
            assert (p.semana, p.hay_anterior, p.hay_siguiente) == (n, n > 0, n < maximo), p
            assert p.desde == d.semana(ahora)[0] + timedelta(weeks=n) and p.desde.weekday() == 0
            assert p.hasta == p.desde + timedelta(days=6)
            desde = ahora if n == 0 else datetime.combine(p.desde, time())
            assert len({x.pelicula.id for x in p.peliculas}) == len(p.peliculas)  # una entrada por película
            for x in p.peliculas:
                assert desde <= x.sesion.fecha_hora < datetime.combine(p.hasta + timedelta(days=1), time()), x
                assert x.n_sesiones >= 1 and 1 <= x.n_cines <= x.n_sesiones, x
    print("OK: estrenos 0..8 y especiales 0..3 (límites, hay_anterior/hay_siguiente, sesión dentro de la semana)")

    for n in range(d.SEMANAS_MAX + 1):
        p = paginas["estrenos", n]
        assert all(p.desde <= x.pelicula.fecha_estreno <= p.hasta for x in p.peliculas)
        assert all(d.es_cine(session.get(Pelicula, x.pelicula.id)) for x in p.peliculas)
        con = [x for x in p.peliculas if not x.sin_nota]
        sin = [x for x in p.peliculas if x.sin_nota]
        assert p.peliculas == con + sin, "las de sin nota van al final"
        assert all(x.pelicula.votos >= d.VOTOS_MIN_ESTRENO for x in con)
        assert [(-x.pelicula.nota_tmdb, x.pelicula.titulo.casefold()) for x in con] == sorted(
            (-x.pelicula.nota_tmdb, x.pelicula.titulo.casefold()) for x in con)
        assert [(-x.n_cines, -x.n_sesiones, x.pelicula.titulo.casefold()) for x in sin] == sorted(
            (-x.n_cines, -x.n_sesiones, x.pelicula.titulo.casefold()) for x in sin)

        e = paginas["especiales", n]
        ids_estreno = {x.pelicula.id for x in p.peliculas}
        assert len(e.peliculas) <= d.MAX_ESPECIALES_PAGINA
        assert [-x.pelicula.nota_tmdb for x in e.peliculas] == sorted(-x.pelicula.nota_tmdb for x in e.peliculas)
        for x in e.peliculas:
            peli = session.get(Pelicula, x.pelicula.id)
            assert peli.tmdb_id and peli.votos >= d.VOTOS_MIN_ESPECIAL and d.es_cine(peli), peli.titulo
            assert x.pelicula.id not in ids_estreno and x.sesion.es_evento_especial, peli.titulo
    print("OK: estrenos por nota (sin nota al final, por cines y sesiones; desempate por título) y especiales solo cine")

    # /destacadas: misma semana, mismos topes y especiales de la página (las que no son estreno ni evento)
    r = Destacadas.model_validate(d.leer_destacadas(session, ahora))
    assert (r.semana.inicio, r.semana.fin) == (paginas["estrenos", 0].desde, paginas["estrenos", 0].hasta)
    assert len(r.estrenos) <= d.MAX_ESTRENOS and len(r.especiales) <= d.MAX_ESPECIALES
    ids_pagina = {x.pelicula.id for x in paginas["estrenos", 0].peliculas}
    assert all(x.pelicula.id in ids_pagina for x in r.estrenos)
    print("OK: /destacadas coherente con las páginas")

    for tipo in ("estrenos", "especiales"):
        p = paginas[tipo, 0]
        print(f"\n{tipo.upper()} {p.desde} – {p.hasta} ({len(p.peliculas)}):")
        for x in p.peliculas:
            nota = f"{x.pelicula.nota_tmdb:.1f} ({x.pelicula.votos} votos)" if x.pelicula.nota_tmdb is not None else "sin nota"
            print(f"  {x.pelicula.titulo} | {nota} | {x.pelicula.generos} | {x.sesion.cine} {x.sesion.fecha_hora:%a %d %H:%M}"
                  f" | {x.n_sesiones} ses. / {x.n_cines} cines")
