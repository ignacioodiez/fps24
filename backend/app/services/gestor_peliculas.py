import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Optional

from sqlalchemy import delete, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlmodel import Session, select
from thefuzz import fuzz

from app.database.models import Pase, Pelicula, PeliculaAlias
from app.services import tmdb
from app.services.cines import limpiar_espacios
from app.services.correcciones_peliculas import CORRECCIONES, IGNORAR, SIN_TMDB
from app.services.tiempo import hoy_madrid

logger = logging.getLogger(__name__)

# --- REGLAS DE TÍTULO ---
# Todas se comparan como palabra completa y sin distinguir mayúsculas.

# No son películas: resolver_pelicula devuelve None y el scraper descarta el pase.
EXCLUIDOS = [r"^BONO\b", r"^ABONO\b", r"\bTARJETA REGALO\b"]

# Programación de una película: marca especial y se quita del título antes de buscarlo.
PROGRAMACION = [
    "MIERCOLES DE IMPRESCINDIBLES", "MIÉRCOLES DE IMPRESCINDIBLES",
    "CINE DE SIEMPRE", "LOS JUEVES DEL", "SESIÓN ESPECIAL",
    "PROYECCIÓN Y COLOQUIO", "PRESENTACIÓN Y COLOQUIO", "COLOQUIO",
    "REESTRENO 4K", "REESTRENO", "CLÁSICOS", "CICLO", "CUTRECON 15",
    "NUEVAS MIRADAS DE CINE ASIÁTICO", "FILMOTECA", "MARATÓN",
    "EVENTO", "PREESTRENO", "PRESENTACIÓN", "JUEVES DE IMPRESCINDIBLES:",
    "ANIME DAY:", "MIERCOLES CULTURAL", "[WILDER CINEMA]", "DOMINGO DE CLÁSICOS:", "UNIVERSO RAFAEL AZCONA:", "BERTOLUCCI:",
]

# Solo marcan especial: no se quitan del título y la película se busca igual.
# WORLD TOUR va aquí y no en PROGRAMACION: TMDB guarda los conciertos con esas palabras en el título.
ESPECIAL = ["EN DIRECTO", "DIFERIDO", "PROYECCIÓN ESPECIAL", "WORLD TOUR"]

# Eventos que no son una película (ópera, ballet, conciertos): especial y sin buscar en TMDB.
EVENTO = ["MET OPERA", "ROYAL BALLET", "ROYAL OPERA", "ROH", "LIVE VIEWING"]
# Estas solo en cabecera: al inicio, antes de ":", tras " - " o al abrir paréntesis
# ("Carmen (Ópera…)"), para no marcar "El fantasma de la ópera" o "El concierto".
EVENTO_CABECERA = ["ÓPERA", "OPERA", "BALLET", "CONCIERTO", "RECITAL"]

# Paréntesis que no son un título alternativo: versión, formato, sala...
ETIQUETAS = re.compile(r"\bV\.?\s?O\.?\s?S|^\s*V\.?\s?O\.?\s*$|DOBLAD|VERSI[OÓ]N|\d+\s?MM\b|DIGITAL|OCAP|"
                       r"ISENSE|IMAX|\b3D\b|\b4K\b|ANIVERSARIO|DIRECTO|INFINITY VISION", re.IGNORECASE)

# Una película es "clásico" si es de antes de (año actual en Madrid - ANTIGUEDAD_CLASICO).
ANTIGUEDAD_CLASICO = 3

# Parecido mínimo para aceptar un resultado de TMDB: mismo número de palabras y cada pareja de
# palabras con fuzz.ratio >= UMBRAL_PARECIDO. Admite erratas ("PARDISO") pero no una palabra
# distinta: con el ratio del título entero, "...INTERNACIONAL - AWFF 26" y "...NACIONAL..." dan 94.
UMBRAL_PARECIDO = 80

# Sin resultados en TMDB: se vuelve a buscar pasado este tiempo (si sigue con pases activos).
REINTENTO_SIN_RESULTADOS = timedelta(days=7)


def _palabras(lista):
    # (?<!\w)/(?!\w) en vez de \b: también vale para "[WILDER CINEMA]" o "BERTOLUCCI:"
    return "|".join(rf"(?<!\w){re.escape(p)}(?!\w)" for p in sorted(lista, key=len, reverse=True))


_EXCLUIDOS = re.compile("|".join(EXCLUIDOS), re.IGNORECASE)
_PROGRAMACION = re.compile(_palabras(PROGRAMACION), re.IGNORECASE)
_ESPECIAL = re.compile(_palabras(ESPECIAL), re.IGNORECASE)
_CABECERA = "|".join(map(re.escape, EVENTO_CABECERA))
_EVENTO = re.compile(
    rf"{_palabras(EVENTO)}|.\bLIVE\b"  # LIVE salvo al inicio: "BALLET LIVE ROH" sí, "Live by Night" no
    rf"|(?:^|\(|\s[-–—]\s)\s*(?:{_CABECERA})\b|\b(?:{_CABECERA})\s*:", re.IGNORECASE)
_PARENTESIS = re.compile(r"(?<!\w)\(([^()]*)\)")  # "ELEMENTS OF(F) BALANCE" no es un paréntesis
_ANIO_FINAL = re.compile(r"^(.*?)[\s,]*\b((?:18|19|20)\d{2})$")
_GUION = re.compile(r"\s[-–—]\s")


def clave_titulo(titulo: str) -> str:
    """Minúsculas, sin tildes ni puntuación. A diferencia de normalizar() (cines.py), no borra
    las letras sin forma ASCII ("Straße" -> "strasse", "Łódź" -> "łodz", "笛吹川" se queda)."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", titulo or "") if not unicodedata.combining(c))
    return " ".join(re.sub(r"[\W_]+", " ", sin_tildes.casefold()).split())


class Titulo(NamedTuple):
    limpio: str            # sin paréntesis ni programación: el que se guarda si no hay TMDB
    consultas: list        # para TMDB, por orden: limpio, antes de " - ", paréntesis
    respaldo: Optional[str]  # lo que va tras ":": solo si no casa ninguna consulta
    anio: Optional[int]    # de "(Título original, 1924)"
    excluido: bool
    evento: bool
    doble: bool            # sesión doble "A + B": solo se busca el título entero


def analizar_titulo(titulo_raw: str) -> Titulo:
    raw = limpiar_espacios(titulo_raw or "")
    anio, alternativos = None, []
    for dentro in _PARENTESIS.findall(raw):
        match = _ANIO_FINAL.match(dentro.strip())
        if match:
            anio, dentro = int(match.group(2)), match.group(1)
        dentro = dentro.strip(" ,")
        if dentro and not ETIQUETAS.search(dentro):
            alternativos.append(dentro)

    limpio = _PROGRAMACION.sub(" ", _PARENTESIS.sub(" ", raw))
    limpio = limpiar_espacios(limpio).strip(" :-–—.,") or raw
    doble = " + " in limpio

    consultas, respaldo = [limpio], None
    if not doble:
        if _GUION.search(limpio):
            consultas.append(_GUION.split(limpio, 1)[0])
        consultas += alternativos
        if ":" in limpio:
            respaldo = limpiar_espacios(limpio.split(":", 1)[1]).strip(" :-–—.,")
    vistas, unicas = set(), []
    for consulta in (limpiar_espacios(c).strip(" :-–—.,") for c in consultas):
        if len(consulta) >= 2 and clave_titulo(consulta) not in vistas:
            vistas.add(clave_titulo(consulta))
            unicas.append(consulta)
    if respaldo and (len(respaldo) < 2 or clave_titulo(respaldo) in vistas):
        respaldo = None

    return Titulo(limpio=limpio, consultas=unicas, respaldo=respaldo, anio=anio,
                  excluido=bool(_EXCLUIDOS.search(raw)), evento=bool(_EVENTO.search(raw)), doble=doble)


def es_especial(titulo_raw: str, anio: int = None) -> bool:
    """Programación, palabra especial o evento en el título, o película antigua."""
    titulo = titulo_raw or ""
    if _PROGRAMACION.search(titulo) or _ESPECIAL.search(titulo) or _EVENTO.search(titulo):
        return True
    return bool(anio and anio < hoy_madrid().year - ANTIGUEDAD_CLASICO)


# --- EMPAREJAMIENTO ---

def _anio_resultado(resultado: dict):
    fecha = resultado.get("release_date") or ""
    return int(fecha[:4]) if fecha[:4].isdigit() else None


def _parecido(a: str, b: str) -> int:
    """0-100 entre dos claves: el peor parecido palabra a palabra; 0 si no tienen las mismas palabras."""
    if a.replace(" ", "") == b.replace(" ", ""):  # "spider man" / "spiderman"
        return 100
    palabras_a, palabras_b = a.split(), b.split()
    if not palabras_a or len(palabras_a) != len(palabras_b):
        return 0
    return min(fuzz.ratio(x, y) for x, y in zip(palabras_a, palabras_b))


def elegir_candidato(consultas: list, anio: int, resultados: list, preferir_recientes: bool = True):
    """El resultado de TMDB más parecido a alguna consulta (título, título original o título sin su
    paréntesis), con parecido >= UMBRAL_PARECIDO y, si hay año, a ±1 año. Entre los igual de parecidos:
    con año, el más cercano; sin año, uno estrenado desde el año pasado si casa con el título completo
    y preferir_recientes (la cartelera suele ser de estrenos; las reposiciones traen año o ciclo);
    y si no, el primero en el orden de TMDB."""
    claves = [clave_titulo(c) for c in consultas]
    reciente = hoy_madrid().year - 1
    mejor, mejor_orden = None, (UMBRAL_PARECIDO - 1,)
    for resultado in resultados:
        anio_resultado = _anio_resultado(resultado)
        if anio and (not anio_resultado or abs(anio_resultado - anio) > 1):
            continue
        titulos = [resultado.get("title"), resultado.get("original_title"),
                   _PARENTESIS.sub(" ", resultado.get("title") or "")]  # "Kakeru (Sheep in the Box)"
        parecidos = [max(_parecido(c, clave_titulo(t)) for t in titulos) for c in claves]
        parecido = max(parecidos)
        if anio:
            desempate = -abs(anio_resultado - anio)
        else:
            desempate = int(preferir_recientes and parecidos[0] == parecido
                            and bool(anio_resultado and anio_resultado >= reciente))
        orden = (parecido, desempate)
        if parecido >= UMBRAL_PARECIDO and orden > mejor_orden:
            mejor, mejor_orden = resultado, orden
    return mejor


def _buscar_en_tmdb(t: Titulo, anio: int, especial: bool):
    """tmdb_id del primer candidato válido, o None. Con año, primero se filtra por él.
    Lo que va tras ":" (t.respaldo) solo se busca, y solo cuenta, si no casa el título entero."""
    for consultas in ([t.consultas, [t.respaldo]] if t.respaldo else [t.consultas]):
        recientes = not especial and consultas is t.consultas  # tras ":" suele ser un ciclo: "Terror Total: [REC]"
        for idioma in ("es-ES", "en-US"):  # en-US: títulos sin traducción ("Fuefuki River")
            for consulta in consultas:
                for filtro in ([anio, None] if anio else [None]):
                    resultados = tmdb.buscar(consulta, idioma, filtro)
                    elegido = elegir_candidato(consultas, anio, resultados, preferir_recientes=recientes)
                    if elegido:
                        return elegido["id"]
                    exactos = [r for r in resultados if _anio_resultado(r) == anio]
                    if filtro and len(exactos) == 1:
                        logger.info("Rechazado el único resultado de %s para %r: %r (tmdb_id %s)",
                                    anio, consulta, exactos[0].get("title"), exactos[0].get("id"))
    return None


def _crear(session: Session, pelicula: Pelicula) -> Pelicula:
    """Inserta en un savepoint: si otra ejecución ha creado ya ese tmdb_id, devuelve esa."""
    try:
        with session.begin_nested():
            session.add(pelicula)
    except IntegrityError:
        if pelicula.tmdb_id is None:
            raise
        return session.exec(select(Pelicula).where(Pelicula.tmdb_id == pelicula.tmdb_id)).one()
    return pelicula


def _titulo_a_guardar(datos: dict, titulo_web: str) -> str:
    """Español si está en alfabeto latino; si no, el título limpio de la web; si no, inglés."""
    return next((t for t in (datos["titulo_es"], titulo_web, datos["titulo_en"]) if tmdb.es_latino(t)),
                titulo_web)


def _campos_tmdb(datos: dict, titulo_web: str) -> dict:
    return dict(
        titulo=_titulo_a_guardar(datos, titulo_web),
        titulo_original=datos["titulo_original"],
        tmdb_id=datos["tmdb_id"],
        poster_url=datos["poster"],
        sinopsis=datos["sinopsis"],
        nota_tmdb=datos["nota"],
        anio=datos["anio"],
        generos=datos["generos"],
        backdrop_url=datos["backdrop"],
        duracion=datos["duracion"],
        youtube_id=datos["youtube_id"],
        imagenes_galeria=datos["imagenes_galeria"],
    )


def _por_tmdb_id(session: Session, tmdb_id: int, titulo_web: str) -> Pelicula:
    pelicula = session.exec(select(Pelicula).where(Pelicula.tmdb_id == tmdb_id)).first()
    if pelicula:
        return pelicula
    return _crear(session, Pelicula(**_campos_tmdb(tmdb.datos_por_id(tmdb_id), titulo_web)))


def _por_titulo_exacto(session: Session, t: Titulo, anio: int):
    """Película de TMDB ya guardada con el mismo título (o título original). Solo si hay una."""
    clave = clave_titulo(t.limpio)
    candidatas = [p for p in session.exec(select(Pelicula).where(Pelicula.tmdb_id.is_not(None))).all()
                  if clave in (clave_titulo(p.titulo), clave_titulo(p.titulo_original))
                  and not (anio and p.anio and abs(p.anio - anio) > 1)]
    return candidatas[0] if len(candidatas) == 1 else None


def _ahora_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _sin_tmdb(session: Session, titulo: str, sinopsis: str = None, reintentar_en: datetime = None) -> Pelicula:
    """Película sin TMDB: reutiliza la que tenga el mismo título normalizado (y su fecha de reintento).
    reintentar_en None: no se vuelve a buscar en TMDB (eventos y correcciones SIN_TMDB)."""
    clave = clave_titulo(titulo)
    for pelicula in session.exec(select(Pelicula).where(Pelicula.tmdb_id.is_(None))).all():
        if clave_titulo(pelicula.titulo) == clave:
            return pelicula
    return _crear(session, Pelicula(titulo=titulo, sinopsis=sinopsis, tmdb_reintentar_en=reintentar_en))


_CORRECCIONES = {clave_titulo(k): v for k, v in CORRECCIONES.items()}


def _correccion(titulo_raw: str, t: Titulo):
    for clave in (clave_titulo(titulo_raw), clave_titulo(t.limpio)):
        if clave in _CORRECCIONES:
            return _CORRECCIONES[clave]
    return None


def _emparejar(session: Session, titulo_raw: str, cine: str, t: Titulo, anio: int, correccion):
    """Devuelve (película, si se puede guardar el alias). Sin alias cuando TMDB no responde,
    para que la siguiente ejecución lo vuelva a intentar."""
    titulo = limpiar_espacios(titulo_raw) if t.evento else t.limpio
    if correccion == SIN_TMDB or (correccion is None and t.evento):
        return _sin_tmdb(session, titulo), True
    try:
        if correccion is not None:
            return _por_tmdb_id(session, correccion, titulo), True
        pelicula = _por_titulo_exacto(session, t, anio)
        if pelicula:
            return pelicula, True
        tmdb_id = _buscar_en_tmdb(t, anio, es_especial(titulo_raw))
        if tmdb_id:
            return _por_tmdb_id(session, tmdb_id, titulo), True
        logger.warning("Sin TMDB: %r en %s; se guarda como %r", titulo_raw, cine, titulo)
        return _sin_tmdb(session, titulo, "No encontrada en TMDB", _ahora_utc() + REINTENTO_SIN_RESULTADOS), True
    except tmdb.TmdbNoDisponible as e:
        logger.warning("TMDB no disponible para %r en %s; se guarda sin TMDB: %s", titulo_raw, cine, e)
        return _sin_tmdb(session, titulo, "No encontrada en TMDB", _ahora_utc()), False


def _guardar_alias(session: Session, clave: str, pelicula_id: int):
    alias = session.get(PeliculaAlias, clave)
    if alias is None:
        try:
            with session.begin_nested():
                session.add(PeliculaAlias(titulo_norm=clave, pelicula_id=pelicula_id))
        except IntegrityError:
            pass  # otra ejecución ha guardado el mismo alias a la vez: vale el suyo
    elif alias.pelicula_id != pelicula_id:
        alias.pelicula_id = pelicula_id
        session.add(alias)


def resolver_pelicula(session: Session, titulo_raw: str, cine: str, anio_web: int = None):
    """Para scrapers del contrato: recibe el título tal como sale en la web y devuelve
    (pelicula_id o None, es_especial). El año de la web, si lo hay, manda sobre el de TMDB.
    Hace flush, no commit. Los errores de BD suben: no se capturan aquí."""
    t = analizar_titulo(titulo_raw)
    correccion = _correccion(titulo_raw, t)
    if t.excluido or correccion == IGNORAR:
        logger.info("Ignorado (no es una película): %r en %s", titulo_raw, cine)
        return None, False

    anio = anio_web or t.anio
    clave = clave_titulo(titulo_raw)
    alias = session.get(PeliculaAlias, clave) if correccion is None else None
    if alias:
        pelicula = session.get(Pelicula, alias.pelicula_id)
    else:
        pelicula, cachear = _emparejar(session, titulo_raw, cine, t, anio, correccion)
        if cachear:
            _guardar_alias(session, clave, pelicula.id)

    especial = es_especial(titulo_raw, anio or pelicula.anio) or (t.doble and pelicula.tmdb_id is None)
    return pelicula.id, especial


# --- MANTENIMIENTO (al final de cada ejecución) ---

def fusionar_peliculas(session: Session, origen: Pelicula, destino: Pelicula):
    """Pasa los pases y alias de origen a destino y borra origen. Los pases de origen que ya
    existen en destino (mismo cine, fecha, idioma y sala) se borran. Hace flush, no commit."""
    otro = aliased(Pase)
    choca = select(otro.id).where(
        otro.pelicula_id == destino.id, otro.cine_id == Pase.cine_id, otro.fecha_hora == Pase.fecha_hora,
        func.coalesce(otro.idioma, "") == func.coalesce(Pase.idioma, ""),
        func.coalesce(otro.sala, "") == func.coalesce(Pase.sala, "")).exists()
    session.exec(delete(Pase).where(Pase.pelicula_id == origen.id, choca))
    session.exec(update(Pase).where(Pase.pelicula_id == origen.id).values(pelicula_id=destino.id))
    session.exec(update(PeliculaAlias).where(PeliculaAlias.pelicula_id == origen.id).values(pelicula_id=destino.id))
    # Sentencia y no session.delete(): el ORM pondría a NULL la película de los pases ya cargados
    session.exec(delete(Pelicula).where(Pelicula.id == origen.id))
    session.flush()


def reintentar_sin_tmdb(session: Session, limite: int = 50) -> dict:
    """Vuelve a buscar en TMDB, por su título y sus alias, las películas sin TMDB con pases activos
    y el reintento cumplido. Si encuentra, rellena sus datos o la fusiona con la que ya tiene ese
    tmdb_id. Si TMDB no responde, para: el resto queda para la siguiente ejecución. Flush, no commit."""
    ahora = _ahora_utc()
    pendientes = session.exec(select(Pelicula).where(
        Pelicula.tmdb_id.is_(None), Pelicula.tmdb_reintentar_en <= ahora,
        select(Pase.id).where(Pase.pelicula_id == Pelicula.id, Pase.activo).exists(),
    ).order_by(Pelicula.tmdb_reintentar_en).limit(limite)).all()
    resumen = dict(rellenadas=0, fusionadas=0, sin_resultados=0)
    for pelicula in pendientes:
        alias = session.exec(select(PeliculaAlias.titulo_norm).where(PeliculaAlias.pelicula_id == pelicula.id)).all()
        try:
            tmdb_id = None
            for titulo in dict.fromkeys([pelicula.titulo, *alias]):
                t = analizar_titulo(titulo)
                tmdb_id = _buscar_en_tmdb(t, t.anio, es_especial(titulo))
                if tmdb_id:
                    break
            if not tmdb_id:
                pelicula.tmdb_reintentar_en = ahora + REINTENTO_SIN_RESULTADOS
                session.add(pelicula)
                resumen["sin_resultados"] += 1
                continue
            destino = session.exec(select(Pelicula).where(Pelicula.tmdb_id == tmdb_id)).first()
            if destino is None:
                datos = tmdb.datos_por_id(tmdb_id)
                try:
                    with session.begin_nested():  # otra ejecución puede haber creado ya ese tmdb_id
                        for campo, valor in _campos_tmdb(datos, pelicula.titulo).items():
                            setattr(pelicula, campo, valor)
                        pelicula.tmdb_reintentar_en = None
                        session.add(pelicula)
                    resumen["rellenadas"] += 1
                    continue
                except IntegrityError:
                    destino = session.exec(select(Pelicula).where(Pelicula.tmdb_id == tmdb_id)).one()
            logger.info("Reintento TMDB: %r se fusiona con %r (tmdb_id %s)", pelicula.titulo, destino.titulo, tmdb_id)
            fusionar_peliculas(session, pelicula, destino)
            resumen["fusionadas"] += 1
        except tmdb.TmdbNoDisponible as e:
            logger.warning("Reintento TMDB interrumpido, TMDB no disponible: %s", e)
            break
    session.flush()
    return resumen


def limpiar_peliculas(session: Session) -> dict:
    """Borra las películas cuyo título encaja en EXCLUIDOS (con sus pases y, en cascada, sus alias)
    y las que no tienen ningún pase, activo o no. Flush, no commit."""
    excluidas = [id_ for id_, titulo in session.exec(select(Pelicula.id, Pelicula.titulo)).all()
                 if _EXCLUIDOS.search(titulo or "")]
    pases = session.exec(delete(Pase).where(Pase.pelicula_id.in_(excluidas))).rowcount
    session.exec(delete(Pelicula).where(Pelicula.id.in_(excluidas)))
    sin_pases = session.exec(delete(Pelicula).where(
        ~select(Pase.id).where(Pase.pelicula_id == Pelicula.id).exists())).rowcount
    session.flush()
    return dict(excluidas=len(excluidas), pases_excluidos=pases, sin_pases=sin_pases)
