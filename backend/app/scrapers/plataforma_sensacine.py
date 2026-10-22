"""Cartelera de un cine en SensaCine por su id (E0609...): un JSON por día en /_/showtimes/theater-<id>/d-AAAA-MM-DD/,
paginado de 10 en 10 películas (/p-N/, pagination.totalPages). Cada resultado trae movie (null en algunos eventos)
y showtimes agrupados por versión (original_st, local, dubbed, dubbed_st...), cada sesión con startsAt y ticketing."""
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.scrapers.comun import FuenteNoDisponible, hoy_madrid, obtener_json, obtener_logger

URL_DIA = "https://www.sensacine.com/_/showtimes/theater-{id}/d-{dia}/"
URL_CINE = "https://www.sensacine.com/cines/cine/{id}/"
DIAS = 60
PAUSA = 1.0          # segundos entre peticiones: con 0,3 s Cloudflare respondió 429 hacia la petición 270
MAX_PETICIONES = 80   # por cine
FIN_TRAS_VACIOS = 7   # días seguidos sin sesiones y sin nextDate tras los que se deja de pedir
# Días sin sesiones: vienen con error=true y uno de estos mensajes (con nextDate o sin él)
DIA_VACIO = {"next.showtime.on", "no.showtime.error"}

log = obtener_logger(__name__)


@dataclass(frozen=True)
class Sesion:
    titulo: str
    anio: int | None
    fecha_hora: datetime
    idioma: str
    link: str


def idioma_de(version, code, tags=(), link=""):
    """Grupo de versión de SensaCine + `code` del enlace relay -> 'VOSE' o 'Español'.
    dubbed_st es doblada o en español con subtítulos: solo es VOSE si el code dice subtítulos en castellano
    (hoy solo sale "V.O. SUB. INGLÉS" en películas españolas: Español).
    Sin tags Localization.* (Artistic Metropol lo pone todo en dubbed) la versión no dice nada: se mira el enlace
    de compra del cine ("...-v-o-s-e/")."""
    if version.startswith("original"):
        return "VOSE"
    if not any(t.startswith("Localization.") for t in tags or ()):
        return "VOSE" if "v-o-s" in link.lower() else "Español"
    code = (code or "").upper()
    if version == "dubbed_st" and ("SUB. CASTELLANO" in code or "SUB. ESPAÑOL" in code):
        return "VOSE"
    return "Español"


def _enlaces(showtime):
    """[(provider, url)] de data.ticketing, en orden."""
    return [(t.get("provider"), url) for t in (showtime.get("data") or {}).get("ticketing") or []
            for url in t.get("urls") or []]


def _code_relay(enlaces):
    for provider, url in enlaces:
        if provider == "relay" and "code=" in url:
            return url.split("code=", 1)[1]
    return None


def normalizar_pagina(datos, id_cine, contadores):
    """Una respuesta JSON -> [Sesion]. Las películas sin movie se cuentan en contadores['sin_titulo'];
    las sesiones que no se entienden, en contadores['descartado']."""
    sesiones = []
    for resultado in datos["results"]:
        movie = resultado.get("movie")
        grupos = resultado.get("showtimes") or {}
        if not movie or not movie.get("title"):
            n = sum(len(v or []) for v in grupos.values())
            log.info("%s: %d sesiones sin película (movie null), se saltan", id_cine, n)
            contadores["sin_titulo"] += n
            continue
        anio = ((movie.get("data") or {}).get("productionYear")) or None
        for version, showtimes in grupos.items():
            for st in showtimes or []:
                try:
                    fecha_hora = datetime.fromisoformat(st["startsAt"]).replace(tzinfo=None, second=0, microsecond=0)
                    enlaces = _enlaces(st)
                    link = (next((u for p, u in enlaces if p == "default"), None)
                            or next((u for _, u in enlaces), None) or URL_CINE.format(id=id_cine))
                    idioma = idioma_de(version, _code_relay(enlaces), st.get("tags"), link)
                    sesiones.append(Sesion(movie["title"], anio, fecha_hora, idioma, link))
                except (KeyError, TypeError, ValueError):
                    log.warning("%s: sesión descartada de %r: %r", id_cine, movie["title"], st, exc_info=True)
                    contadores["descartado"] += 1
    return sesiones


def leer_cine(id_cine, contadores, obtener=obtener_json, dormir=time.sleep, hoy: date = None):
    """Sesiones de hoy a DIAS vista. Salta con nextDate los huecos sin sesiones, para tras FIN_TRAS_VACIOS días
    vacíos seguidos sin nextDate (hay huecos de 4 días sin él) y pagina con /p-N/.
    Lanza FuenteNoDisponible si falla una petición, el JSON no tiene la forma esperada o se pasa del tope."""
    hoy = hoy or hoy_madrid()
    dia, fin, sesiones, vacios = hoy, hoy + timedelta(days=DIAS), [], 0
    while dia <= fin and vacios < FIN_TRAS_VACIOS:
        pagina = 1
        while True:
            if contadores["peticiones"] >= MAX_PETICIONES:
                raise FuenteNoDisponible(f"{id_cine}: tope de {MAX_PETICIONES} peticiones")
            if contadores["peticiones"]:
                dormir(PAUSA)
            url = URL_DIA.format(id=id_cine, dia=dia) + (f"p-{pagina}/" if pagina > 1 else "")
            datos = obtener(url)
            contadores["peticiones"] += 1
            try:
                if datos.get("error") and datos.get("message") not in DIA_VACIO:
                    raise FuenteNoDisponible(f"{url}: error {datos.get('message')!r}")
                sesiones += normalizar_pagina(datos, id_cine, contadores)
                total_paginas = datos["pagination"]["totalPages"] or 1
                # nextDate solo viene en días vacíos; si falta no significa que no haya más (hay huecos de varios días)
                siguiente = date.fromisoformat(datos["nextDate"]) if datos.get("nextDate") else None
            except (AttributeError, KeyError, TypeError, ValueError) as e:
                raise FuenteNoDisponible(f"{url}: JSON con forma inesperada") from e
            if pagina >= total_paginas:
                break
            pagina += 1
        vacios = 0 if siguiente or datos["results"] else vacios + 1
        dia = max(dia + timedelta(days=1), siguiente or dia)
    return sesiones
