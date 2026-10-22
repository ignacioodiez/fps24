"""Self-check del gestor de películas con la tabla de casos reales de las regresiones.
Uso: docker compose exec api python tests/check_gestor_peliculas.py           (TMDB simulado)
     docker compose exec -e RED=1 api python tests/check_gestor_peliculas.py  (+ TMDB real)
Lo que toca la BD ocurre en una sesión que vacía pase y pelicula y termina en rollback: no deja datos."""
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, text, update
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase, Pelicula, PeliculaAlias
from app.services import gestor_peliculas as gestor, tmdb
from app.services.correcciones_peliculas import IGNORAR, SIN_TMDB
from app.services.gestor_peliculas import (analizar_titulo, clave_titulo, elegir_candidato, es_especial,
                                           resolver_pelicula)
from app.services.pases import registrar_pase
from app.services.tiempo import hoy_madrid

CINE = "Cine de Prueba Gestor"
ANIO = hoy_madrid().year

# --- clave_titulo: quita tildes sin borrar letras ---
assert clave_titulo("Ágora") == "agora"
assert clave_titulo("Straße") == "strasse" and clave_titulo("Łódź") == "łodz" and clave_titulo("Søren") == "søren"
assert clave_titulo("笛吹川") == "笛吹川"
assert clave_titulo("La invitación.") == clave_titulo("LA INVITACION")
print("OK: clave_titulo")

# --- reglas de título ---
for titulo in ["BONO 10 FILMOTECA", "BONO ANUAL FILMOTECA", "Abono 5 sesiones"]:
    assert analizar_titulo(titulo).excluido, titulo
for titulo in ["BTS WORLD TOUR ARIRANG: BUENOS AIRES LIVE VIEWING", "MANON - BALLET LIVE ROH 26-27",
               "Manon (Ballet EN DIRECTO desde The Royal Ballet)", "Ballet Manon - Directo desde The Royal Ballet",
               "Carmen (Ópera EN DIRECTO desde The Royal Opera House)",
               "Pavarotti, live in Central Park", "Met Opera: La Traviata", "Gala de ballet: Giselle"]:
    assert analizar_titulo(titulo).evento and es_especial(titulo, ANIO), titulo
for titulo in ["El fantasma de la ópera", "El concierto", "Operación Valkiria", "Live by Night",
               "Nosferatu (Cine con piano en directo)", "Cold War", "Dune: Parte Tres", "ENHYPEN WORLD TOUR BLOOD SAGA"]:
    assert not analizar_titulo(titulo).evento, titulo
# WORLD TOUR: especial, pero se busca en TMDB con el título entero
assert es_especial("ENHYPEN WORLD TOUR BLOOD SAGA", ANIO)
assert analizar_titulo("ENHYPEN WORLD TOUR BLOOD SAGA").consultas == ["ENHYPEN WORLD TOUR BLOOD SAGA"]
assert es_especial("Nosferatu (Cine con piano en directo)", ANIO)        # especial, pero se busca en TMDB
assert es_especial("Domingo de clásicos: Lawrence de Arabia (VOSE)", ANIO)
assert not es_especial("Neoclásicos", ANIO)                               # palabra completa
assert not es_especial("Bicicleta", ANIO) and not es_especial("Eventos", ANIO)

t = analizar_titulo("EL ÚLTIMO (DER LETZTE MANN,1924)")
assert (t.limpio, t.anio, t.consultas) == ("EL ÚLTIMO", 1924, ["EL ÚLTIMO", "DER LETZTE MANN"]), t
t = analizar_titulo("El último (Der letzte Mann, 1924)")
assert (t.anio, t.consultas) == (1924, ["El último", "Der letzte Mann"]), t
t = analizar_titulo("ANDER ETA YUL (1988)")
assert (t.limpio, t.consultas, t.anio) == ("ANDER ETA YUL", ["ANDER ETA YUL"], 1988), t
assert analizar_titulo("Kakeru (V.O.S.E.)").consultas == ["Kakeru"]
assert analizar_titulo("LA BOLA NEGRA (35MM)").consultas == ["LA BOLA NEGRA"]
assert analizar_titulo("El resplandor (The Shining)").consultas == ["El resplandor", "The Shining"]
assert analizar_titulo("ELEMENTS OF(F) BALANCE").limpio == "ELEMENTS OF(F) BALANCE"
assert analizar_titulo("Cars - 20º aniversario").consultas == ["Cars - 20º aniversario", "Cars"]
t = analizar_titulo("Domingo de clásicos: Lawrence de Arabia (VOSE)")
assert t.limpio == "Lawrence de Arabia", t
t = analizar_titulo("Terror Total: Hereditary (VOSE)")
assert (t.consultas, t.respaldo) == (["Terror Total: Hereditary"], "Hereditary"), t
t = analizar_titulo("CIMA PROYECTA: LA MUJER RUBIA (LA MUJER SIN CABEZA) + LIBRA")
assert t.doble and t.consultas == ["CIMA PROYECTA: LA MUJER RUBIA + LIBRA"], t   # nada de "La mujer sin cabeza"
assert analizar_titulo("Humano: Deseos Mayores + Soy Tribulete 7").doble
assert analizar_titulo("SECCIÓN CORTOMETRAJES INTERNACIONAL - AWFF 26").consultas == [
    "SECCIÓN CORTOMETRAJES INTERNACIONAL - AWFF 26", "SECCIÓN CORTOMETRAJES INTERNACIONAL"]
print("OK: reglas de título")


# --- elegir_candidato ---
def r(id_, title, anio=None, original=None):
    return {"id": id_, "title": title, "original_title": original or title,
            "release_date": f"{anio}-01-01" if anio else ""}


assert elegir_candidato(["LOS DEMONIOS"], None, [r(1, "Los demonios del amanecer", 2024)]) is None
assert elegir_candidato(["LOS DEMONIOS"], None, [r(1, "Los demonios del amanecer", 2024), r(2, "Los demonios", 2025)])["id"] == 2
assert elegir_candidato(["Carmen"], None, [r(1, "Viva Carmen", 2025)]) is None
assert elegir_candidato(["Manon"], None, [r(1, "La venganza de Manon", 2024)]) is None
assert elegir_candidato(["EL ÚLTIMO"], 1924, [r(1, "El último gaucho", 2024)]) is None
assert elegir_candidato(["DER LETZTE MANN"], 1924, [r(1, "El último", 1924, "Der letzte Mann")])["id"] == 1
assert elegir_candidato(["Cold War"], None, [r(1, "Cold War in Philly", 2025), r(2, "Cold War", 2018)])["id"] == 2
assert elegir_candidato(["Cold War"], 2018, [r(1, "Cold War", 1990), r(2, "Cold War", 2018)])["id"] == 2
assert elegir_candidato(["SECCIÓN CORTOMETRAJES INTERNACIONAL - AWFF 26"], None,
                        [r(1, "Sección cortometrajes nacional - AWFF 26")]) is None
assert elegir_candidato(["CINEMA PARDISO"], None, [r(1, "Cinema Paradiso", 1988)])["id"] == 1   # errata
assert elegir_candidato(["Fuefuki River"], None, [r(1, "笛吹川", 1960)]) is None
assert elegir_candidato(["Fuefuki River"], None, [r(1, "Fuefuki River", 1960, "笛吹川")])["id"] == 1
# Empates exactos sin año: uno reciente si lo hay; si no, el orden de TMDB
assert elegir_candidato(["El odio"], None, [r(1, "El odio", 1995, "La Haine"), r(2, "El Odio", 2019)])["id"] == 1
assert elegir_candidato(["La vida de una mujer"], None, [r(1, "La vida de una mujer", 1951),
                                                         r(2, "La vida de una mujer", ANIO)])["id"] == 2
# Con año, el más cercano: Afterimage (Wajda, 2016) y no la de 2015
assert elegir_candidato(["AFTERIMAGE", "POWIDOKI"], 2016, [r(1, "Afterimage", 2015),
                        r(2, "Los últimos años del artista: Afterimage", 2016, "Powidoki")])["id"] == 2
# El paréntesis del título de TMDB tampoco cuenta
# Ciclo o especial: sin preferir recientes ("Domingo de clásicos: My Fair Lady")
assert elegir_candidato(["My Fair Lady"], None, [r(1, "My Fair Lady", 1964), r(2, "My Fair Lady", ANIO)],
                        preferir_recientes=False)["id"] == 1
# Lo reciente solo desempata si casa el título completo, no el de tras los dos puntos
assert elegir_candidato(["Terror Total: [REC]", "[REC]"], None, [r(1, "[•REC]", 2007), r(2, "REC", ANIO)])["id"] == 1
# Con año en la web, un resultado sin fecha no vale (TORRE BELA, 1975)
assert elegir_candidato(["TORRE BELA"], 1975, [r(1, "Torre Bela")]) is None
assert elegir_candidato(["Kakeru"], None, [r(1, "Kakeru (Sheep in the Box)", ANIO, "箱の中の羊")])["id"] == 1
assert elegir_candidato(["Chicho o mientras el cuerpo aguante"], 1982,
                        [r(1, "Chicho o Mientras el cuerpo aguante (una comedia didáctica)", 1982)])["id"] == 1
print("OK: elegir_candidato")

# --- título a guardar ---
assert tmdb.es_latino("Cold War") and tmdb.es_latino("Ágora: ¡sí!") and not tmdb.es_latino("笛吹川")
# Sin español: el de la web antes que el inglés
assert gestor._titulo_a_guardar({"titulo_es": None, "titulo_en": "The Maids of Wilko"}, "LAS SEÑORITAS DE WILKO") == "LAS SEÑORITAS DE WILKO"
assert gestor._titulo_a_guardar({"titulo_es": "笛吹川", "titulo_en": "The River Fuefuki"}, "FUEFUKI RIVER") == "FUEFUKI RIVER"
assert gestor._titulo_a_guardar({"titulo_es": None, "titulo_en": "Fuefuki River"}, "笛吹川") == "Fuefuki River"
assert gestor._titulo_a_guardar({"titulo_es": "آثار متلاشية", "titulo_en": None}, "VANISHING TRACKS") == "VANISHING TRACKS"
assert gestor._titulo_a_guardar({"titulo_es": "El último", "titulo_en": "The Last Laugh"}, "EL ÚLTIMO") == "El último"
print("OK: título a guardar")


# --- flujo con BD y TMDB simulado ---
BASE = 990_000_000  # tmdb_id falsos
FALSO_BUSCAR = {  # (clave de la consulta, idioma) -> resultados
    ("kakeru", "es-ES"): [r(BASE + 1, "Sheep in the Box", 2025, "Kakeru")],
    ("rose", "es-ES"): [r(BASE + 2, "Rosa", 2025, "Rose")],
    ("tangles", "es-ES"): [r(BASE + 3, "Enredos", 2025, "Tangles")],
    ("sucia", "es-ES"): [r(BASE + 4, "Dirty", 2025, "Sucia")],
    ("crimson king", "es-ES"): [r(BASE + 5, "In the Court", 2025, "Crimson King")],
    ("el ultimo", "es-ES"): [r(BASE + 6, "El último gaucho", 2024)],
    ("der letzte mann", "es-ES"): [r(BASE + 7, "El último", 1924, "Der letzte Mann")],
    ("fuefuki river", "es-ES"): [r(BASE + 8, "笛吹川", 1960)],
    ("fuefuki river", "en-US"): [r(BASE + 8, "Fuefuki River", 1960, "笛吹川")],
    ("romeo julieta", "es-ES"): [r(BASE + 9, "Romeo + Julieta", ANIO)],
    ("los demonios", "es-ES"): [r(BASE + 11, "Los demonios del amanecer", 2024), r(BASE + 12, "Los demonios", 2025)],
}
FALSO_DETALLES = {
    BASE + 8: {"titulo_es": "笛吹川", "titulo_en": "Fuefuki River", "titulo_original": "笛吹川", "anio": 1960},
}
llamadas = []


def falso_buscar(consulta, idioma="es-ES", anio=None):
    llamadas.append((consulta, idioma, anio))
    resultados = FALSO_BUSCAR.get((clave_titulo(consulta), idioma), [])
    return [x for x in resultados if not anio or x["release_date"].startswith(str(anio))]


def falso_datos_por_id(tmdb_id):
    llamadas.append(("datos_por_id", tmdb_id))
    todos = {x["id"]: x for lista in FALSO_BUSCAR.values() for x in lista}
    base = todos.get(tmdb_id, r(tmdb_id, f"Película {tmdb_id}", 2020))
    datos = dict(tmdb_id=tmdb_id, titulo_es=base["title"], titulo_en=None, titulo_original=base["original_title"],
                 poster=None, backdrop=None, imagenes_galeria=[], youtube_id=None, sinopsis="", nota=None,
                 duracion=None, anio=gestor._anio_resultado(base), generos="")
    return datos | FALSO_DETALLES.get(tmdb_id, {})


@contextmanager
def sesion_vacia():
    """Sesión con pase y pelicula vacíos (y pelicula_alias, en cascada) que acaba en rollback."""
    with Session(engine) as session:
        try:
            session.exec(delete(Pase))
            session.exec(delete(Pelicula))
            yield session
        finally:
            session.rollback()


def resolver(session, titulo, anio_web=None):
    pelicula_id, especial = resolver_pelicula(session, titulo, CINE, anio_web)
    return (session.get(Pelicula, pelicula_id) if pelicula_id else None), especial


tmdb_real = (tmdb.buscar, tmdb.datos_por_id)
correcciones_reales, gestor._CORRECCIONES = gestor._CORRECCIONES, {}  # el flujo simulado no usa las reales
tmdb.buscar, tmdb.datos_por_id = falso_buscar, falso_datos_por_id
try:
    with sesion_vacia() as session:
        # Excluidos: sin película
        assert resolver_pelicula(session, "BONO 10 FILMOTECA", CINE) == (None, False)

        # Títulos que TMDB guarda distinto: TMDB solo la primera vez, luego el alias
        for titulo in ["Kakeru", "Rose", "Tangles", "Sucia", "Crimson King"]:
            llamadas.clear()
            p1, _ = resolver(session, titulo)
            assert p1.tmdb_id and llamadas, titulo
            llamadas.clear()
            p2, _ = resolver(session, titulo)
            assert p2.id == p1.id and not llamadas, (titulo, llamadas)
        # Otra variante del mismo título: busca otra vez, pero no duplica la película
        assert resolver(session, "Kakeru (V.O.S.E.)")[0].tmdb_id == BASE + 1
        assert len(session.exec(select(Pelicula).where(Pelicula.tmdb_id == BASE + 1)).all()) == 1

        # Sin TMDB: cada sección es la suya, con su título; y la misma sección se reutiliza
        p_int, _ = resolver(session, "SECCIÓN CORTOMETRAJES INTERNACIONAL - AWFF 26")
        p_nac, _ = resolver(session, "SECCIÓN CORTOMETRAJES NACIONAL - AWFF 26")
        assert p_int.id != p_nac.id and p_int.tmdb_id is None and p_int.titulo.endswith("INTERNACIONAL - AWFF 26")
        assert resolver(session, "Sección cortometrajes internacional - AWFF 26 (VOSE)")[0].id == p_int.id

        # Año del paréntesis y título original
        p, especial = resolver(session, "EL ÚLTIMO (DER LETZTE MANN,1924)")
        assert (p.tmdb_id, p.titulo, especial) == (BASE + 7, "El último", True), p
        # Los demonios: el exacto, no el "del amanecer" reciente
        assert resolver(session, "LOS DEMONIOS")[0].tmdb_id == BASE + 12
        # Fuefuki River: es-ES no valida, en-US sí; se guarda el título en inglés
        p, _ = resolver(session, "FUEFUKI RIVER (FUEKUKIGAWA,1960)", anio_web=1960)
        assert (p.tmdb_id, p.titulo) == (BASE + 8, "FUEFUKI RIVER"), p   # sin español: el de la web

        # Eventos: sin TMDB, título crudo, especial
        llamadas.clear()
        p, especial = resolver(session, "MANON - BALLET LIVE ROH 26-27")
        assert (p.tmdb_id, p.titulo, especial, llamadas) == (None, "MANON - BALLET LIVE ROH 26-27", True, []), p
        # Sesión doble: especial si no está en TMDB; "Romeo + Julieta" es una película normal
        assert resolver(session, "MITOLOGÍA DE BARRIO + QUIÉN VIO LOS TEMPLOS CAER")[1] is True
        p, especial = resolver(session, "Romeo + Julieta")
        assert (p.tmdb_id, especial) == (BASE + 9, False), p
        # Programación: se guarda el título limpio aunque el pase sea especial
        session.add(Pelicula(titulo="Lawrence de Arabia", tmdb_id=BASE + 20, anio=1962))
        session.flush()
        llamadas.clear()
        p, especial = resolver(session, "Domingo de clásicos: Lawrence de Arabia (VOSE)")
        assert (p.tmdb_id, especial, llamadas) == (BASE + 20, True, []), p   # título exacto en la BD

        # Correcciones manuales: mandan sobre el alias, valen para las variantes del título
        p_mal, _ = resolver(session, "El odio (VOSE)")
        gestor._CORRECCIONES = {clave_titulo("El odio"): BASE + 30, clave_titulo("GATOS ENCARAMADOS"): SIN_TMDB,
                                clave_titulo("HYBE CHEERING PARTY"): IGNORAR}
        p, _ = resolver(session, "El odio (VOSE)")
        assert p.tmdb_id == BASE + 30 and p.id != p_mal.id
        assert session.get(PeliculaAlias, clave_titulo("El odio (VOSE)")).pelicula_id == p.id
        assert resolver(session, "El odio")[0].id == p.id
        llamadas.clear()
        assert resolver(session, "GATOS ENCARAMADOS")[0].tmdb_id is None and not llamadas
        assert resolver_pelicula(session, "HYBE CHEERING PARTY", CINE) == (None, False)
        gestor._CORRECCIONES = {}

        # Savepoint: si el tmdb_id ya existe, devuelve esa y la sesión sigue viva
        existente = session.exec(select(Pelicula).where(Pelicula.tmdb_id == BASE + 1)).one()
        assert gestor._crear(session, Pelicula(titulo="Duplicada", tmdb_id=BASE + 1)).id == existente.id
        assert session.exec(select(Pelicula).where(Pelicula.titulo == "Duplicada")).first() is None

        # Flush, no commit: otra conexión no ve las películas nuevas
        with Session(engine) as otra:
            assert otra.exec(select(Pelicula).where(Pelicula.tmdb_id == BASE + 1)).first() is None
    print("OK: emparejamiento con TMDB simulado")

    # TMDB caído: película sin TMDB y sin alias, para reintentarlo en la siguiente ejecución
    def tmdb_caido(*args, **kwargs):
        raise tmdb.TmdbNoDisponible("simulado")

    tmdb.buscar = tmdb_caido
    with sesion_vacia() as session:
        p, _ = resolver(session, "Una película cualquiera")
        assert p.tmdb_id is None and session.get(PeliculaAlias, clave_titulo("Una película cualquiera")) is None
        assert p.tmdb_reintentar_en <= gestor._ahora_utc()   # reintento en la siguiente ejecución
    print("OK: TMDB no disponible")

    # Cortacircuito: tras el primer fallo de red no se vuelve a llamar a TMDB
    peticiones_red = []

    def red_caida(*args, **kwargs):
        peticiones_red.append(args)
        raise tmdb.requests.ConnectionError("simulado")

    get_real, clave_real = tmdb.requests.get, tmdb.TMDB_API_KEY
    tmdb.buscar, tmdb.requests.get, tmdb.TMDB_API_KEY = tmdb_real[0], red_caida, "falsa"
    try:
        with sesion_vacia() as session:
            for titulo in ["Primera caída", "Segunda caída", "Tercera caída"]:
                p, _ = resolver(session, titulo)
                assert p.tmdb_id is None and p.tmdb_reintentar_en <= gestor._ahora_utc(), titulo
            assert len(peticiones_red) == 1, peticiones_red
    finally:
        tmdb.requests.get, tmdb.TMDB_API_KEY = get_real, clave_real
        tmdb.reiniciar_cortacircuito()
    print("OK: cortacircuito")

    # Reintento: rellena, fusiona sin duplicar pases, aplaza si no hay resultados y no toca eventos
    def pase(session, pelicula, hora, sala="1"):
        registrar_pase(session, cine=CINE, pelicula_id=pelicula.id, fecha_hora=datetime(ANIO + 1, 1, 1, hora),
                       sala=sala, idioma="VOSE", precio=None, link_compra=None, es_evento_especial=False)

    FALSO_BUSCAR[("pelicula tardia", "es-ES")] = [r(BASE + 40, "Película tardía", 2025)]
    with sesion_vacia() as session:
        tmdb.buscar = tmdb_caido
        tardia, _ = resolver(session, "Película tardía")
        sucia, _ = resolver(session, "Sucia")
        tmdb.buscar = falso_buscar
        nada, _ = resolver(session, "Nada de nada")
        evento, _ = resolver(session, "MANON - BALLET LIVE ROH 26-27")
        assert nada.tmdb_reintentar_en > gestor._ahora_utc() + timedelta(days=6) and evento.tmdb_reintentar_en is None
        destino = Pelicula(titulo="Película tardía", tmdb_id=BASE + 40)
        session.add(destino)
        session.add(PeliculaAlias(titulo_norm="pelicula tardia vose", pelicula_id=tardia.id))
        session.flush()
        for pelicula in (tardia, sucia, nada, evento):
            pase(session, pelicula, 18)
        pase(session, tardia, 21)
        pase(session, destino, 18)   # el mismo pase que el de tardia a las 18: no se duplica
        nada.tmdb_reintentar_en = gestor._ahora_utc() - timedelta(minutes=1)
        session.add(nada)
        tardia_id = tardia.id

        assert gestor.reintentar_sin_tmdb(session) == dict(rellenadas=1, fusionadas=1, sin_resultados=1)
        assert session.get(Pelicula, tardia_id) is None
        horas = sorted(p.fecha_hora.hour for p in session.exec(select(Pase).where(Pase.pelicula_id == destino.id)))
        assert horas == [18, 21], horas
        assert session.get(PeliculaAlias, "pelicula tardia vose").pelicula_id == destino.id
        session.refresh(sucia)
        assert (sucia.tmdb_id, sucia.tmdb_reintentar_en) == (BASE + 4, None), sucia
        assert nada.tmdb_id is None and nada.tmdb_reintentar_en > gestor._ahora_utc() + timedelta(days=6)
        llamadas.clear()
        assert gestor.reintentar_sin_tmdb(session) == dict(rellenadas=0, fusionadas=0, sin_resultados=0)
        assert not llamadas   # nada pendiente: ni el evento ni lo aplazado
    print("OK: reintento sin TMDB")

    # Limpieza: BONO (con sus pases) y películas sin pases; no las que tienen pases, aunque inactivos
    with sesion_vacia() as session:
        bono, huerfana, inactiva, normal = (Pelicula(titulo=t) for t in ["BONO 10 FILMOTECA", "Sin pases",
                                                                          "Con pase inactivo", "Con pase"])
        session.add_all([bono, huerfana, inactiva, normal])
        session.flush()
        for pelicula in (bono, inactiva, normal):
            pase(session, pelicula, 18)
        session.exec(update(Pase).where(Pase.pelicula_id == inactiva.id).values(activo=False))
        ids = [p.id for p in (bono, huerfana, inactiva, normal)]
        assert gestor.limpiar_peliculas(session) == dict(excluidas=1, pases_excluidos=1, sin_pases=1)
        assert [session.exec(select(Pelicula.id).where(Pelicula.id == i)).first() for i in ids] == [None, None] + ids[2:]
        assert not session.exec(select(Pase).where(Pase.pelicula_id == ids[0])).all()
    print("OK: limpiar_peliculas")

    # Un error de BD sube: no se traga ni se confunde con "TMDB no disponible"
    def tmdb_con_error_bd(*args, **kwargs):
        session.exec(text("SELECT 1/0"))

    tmdb.buscar = tmdb_con_error_bd
    with sesion_vacia() as session:
        try:
            resolver_pelicula(session, "Otra película cualquiera", CINE)
            raise AssertionError("el error de BD no ha subido")
        except Exception as e:
            assert "division by zero" in str(e), e
    print("OK: los errores de BD suben")
finally:
    tmdb.buscar, tmdb.datos_por_id = tmdb_real
    gestor._CORRECCIONES = correcciones_reales


# --- RED=1: la tabla de casos con TMDB real ---
if os.getenv("RED") == "1":
    peticiones = []
    _get_real = tmdb._get
    tmdb._get = lambda ruta, **p: peticiones.append(ruta) or _get_real(ruta, **p)
    # (título de la web, año de la web, comprobación sobre (película, especial), qué se espera)
    CASOS = [
        ("LOS DEMONIOS", None, lambda p, e: p.titulo != "Los demonios del amanecer", "no 'Los demonios del amanecer'"),
        ("Manon (Ballet EN DIRECTO desde The Royal Ballet)", None, lambda p, e: p.tmdb_id is None and e, "evento"),
        ("Carmen (Ópera EN DIRECTO desde The Royal Opera House)", None, lambda p, e: p.tmdb_id is None and e, "evento"),
        ("El odio (VOSE)", None, lambda p, e: p.anio == 1995, "La Haine (1995)"),
        ("EL ÚLTIMO (DER LETZTE MANN,1924)", 1924, lambda p, e: p.anio == 1924, "Der letzte Mann (1924)"),
        ("SECCIÓN CORTOMETRAJES INTERNACIONAL - AWFF 26", None, lambda p, e: "INTERNACIONAL" in p.titulo, "su propia fila"),
        ("SECCIÓN CORTOMETRAJES NACIONAL - AWFF 26", None, lambda p, e: "INTERNACIONAL" not in p.titulo, "su propia fila"),
        ("Cold War", 2018, lambda p, e: p.titulo == "Cold War" and p.anio == 2018, "Cold War (2018)"),
        ("FUEFUKI RIVER (FUEKUKIGAWA,1960)", 1960, lambda p, e: p.tmdb_id == 219233 and tmdb.es_latino(p.titulo),
         "笛吹川 (1960) con título latino"),
        ("VANISHING TRACKS", 2026, lambda p, e: tmdb.es_latino(p.titulo), "título latino"),
        ("CINEMA PARDISO (NUOVO CINEMA PARADISO,1988)", 1988, lambda p, e: p.tmdb_id is not None, "con TMDB"),
        ("LAS SEÑORITAS DE WILKO (PANNY Z WILKA,1979)", 1979, lambda p, e: p.tmdb_id is not None, "con TMDB"),
        ("LOS BRUJOS INOCENTES (NIEWINNI CZARODZIEJE,1960)", 1960, lambda p, e: p.tmdb_id is not None, "con TMDB"),
        ("CIMA PROYECTA: LA MUJER RUBIA (LA MUJER SIN CABEZA) + LIBRA", None, lambda p, e: p.tmdb_id is None and e, "sin TMDB, especial"),
        ("GATOS ENCARAMADOS", 2003, lambda p, e: True, "(informativo)"),
        ("BTS WORLD TOUR ARIRANG: BUENOS AIRES LIVE VIEWING", None, lambda p, e: p.tmdb_id is None and e, "evento"),
        ("MANON - BALLET LIVE ROH 26-27", None, lambda p, e: p.tmdb_id is None and e, "evento"),
    ]
    fallos = 0
    with sesion_vacia() as session:
        for titulo, anio_web, ok, esperado in CASOS:
            p, especial = resolver(session, titulo, anio_web)
            bien = ok(p, especial)
            fallos += not bien
            print(f"{'✔' if bien else '✘'} {titulo!r} -> {p.titulo!r} tmdb={p.tmdb_id} año={p.anio} "
                  f"especial={especial} | se espera: {esperado}")
        for titulo in ["Kakeru", "Rose", "Tangles", "Sucia", "IN THE COURT OF THE CRIMSON KING"]:
            resolver(session, titulo)
            antes = len(peticiones)
            p, _ = resolver(session, titulo)
            bien = len(peticiones) == antes
            fallos += not bien
            print(f"{'✔' if bien else '✘'} {titulo!r} -> {p.titulo!r} tmdb={p.tmdb_id}: la 2.ª vez sin TMDB")
        assert resolver_pelicula(session, "BONO ANUAL FILMOTECA", CINE) == (None, False)
    tmdb._get = _get_real
    print(f"RED: {len(CASOS) + 5 - fallos}/{len(CASOS) + 5} casos como se esperan, {len(peticiones)} peticiones a TMDB")
    sys.exit(1 if fallos else 0)
