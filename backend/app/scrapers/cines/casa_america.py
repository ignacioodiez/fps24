"""Lee: https://www.casamerica.es/agenda (mes en curso) y /agenda/AAAAMM (el siguiente), HTML de servidor.
Extrae: grupos .view-grouping con el día en h2 .fecha ("05 de Noviembre"; vacío = el día del grupo anterior) y una fila por
actividad: solo categoría CINE, título y enlace del h3, "Horario: 18:00" y .condiciones como precio. Se proyecta en la Sala Iberia.
Se rompe si: cambian esas clases, el texto "Horario:" o las rutas /agenda. Sin Crawl-delay en su robots.txt: PAUSA de cortesía."""
import html
import re
import time
from dataclasses import dataclass
from datetime import datetime

from app.scrapers.comun import (FuenteNoDisponible, guardar_sesiones, hoy_madrid, numero_mes, obtener_html,
                                obtener_logger, resolver_anio)

BASE = "https://www.casamerica.es"
URL = BASE + "/agenda"
CINES = ["Casa de América"]
SALA = "Sala Iberia"
USER_AGENT = "fps24-bot (+https://fps24.es)"
PAUSA = 5  # segundos entre las dos páginas

log = obtener_logger(__name__)


@dataclass(frozen=True)
class Sesion:
    titulo: str
    fecha_hora: datetime
    precio: str
    link: str


def _texto(fragmento):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def precio_de(condiciones):
    """Texto de .condiciones tal cual ("Entrada libre hasta completar aforo"); si remite a consultar, "Consultar"."""
    return "Consultar" if not condiciones or "consultar precio" in condiciones.lower() else condiciones


def leer_agenda(pagina, contadores):
    """HTML de una agenda mensual -> [Sesion] de la categoría CINE (puede no haber). Año con resolver_anio.
    FuenteNoDisponible si no es una agenda (sin grupos de día)."""
    if 'class="view-grouping"' not in pagina:
        raise FuenteNoDisponible("La agenda no tiene grupos de día (¿ha cambiado la web?)")
    sesiones, dia = [], None
    for grupo in pagina.split('class="view-grouping"')[1:]:
        fecha = re.search(r'class="fecha[^"]*">\s*(\d{1,2}) de (\w+)', grupo)
        if fecha:
            try:
                mes, d = numero_mes(fecha.group(2)), int(fecha.group(1))
                dia = (resolver_anio(mes, d), mes, d)
            except ValueError:
                log.warning("Día no reconocido: %r", fecha.group(0))
                dia = None
        for fila in grupo.split('<li class="row')[1:]:
            categoria = re.search(r'class="categoria[^"]*">([^<]*)<', fila)
            if not categoria or _texto(categoria.group(1)).upper() != "CINE":
                continue
            titulo = re.search(r'(?s)<h3 class="titulo[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', fila)
            horario = re.search(r"Horario:([^<]*)", fila)
            horas = re.findall(r"(\d{1,2}):(\d{2})", horario.group(1)) if horario else []
            if not (titulo and horas and dia):
                log.warning("Fila de cine sin título, horario o día: %r", _texto(fila)[:120])
                contadores["descartado"] += 1
                continue
            condiciones = re.search(r'(?s)class="condiciones">(.*?)</span>', fila)
            precio = precio_de(_texto(condiciones.group(1)) if condiciones else "")
            enlace = titulo.group(1) if titulo.group(1).startswith("http") else BASE + titulo.group(1)
            for h, m in horas:
                sesiones.append(Sesion(_texto(titulo.group(2)), datetime(*dia, int(h), int(m)), precio, enlace))
    return sesiones


def paginas(hoy=None):
    """La agenda del mes en curso y la del siguiente."""
    hoy = hoy or hoy_madrid()
    anio, mes = (hoy.year + 1, 1) if hoy.month == 12 else (hoy.year, hoy.month + 1)
    return [URL, f"{URL}/{anio}{mes:02d}"]


def leer_cine(contadores, obtener=lambda url: obtener_html(url, USER_AGENT), dormir=time.sleep):
    sesiones = []
    for i, url in enumerate(paginas()):
        if i:
            dormir(PAUSA)
        sesiones += leer_agenda(obtener(url), contadores)
        contadores["peticiones"] += 1
    return sesiones


def scrapear_casa_america():
    contadores = {"creado": 0, "actualizado": 0, "descartado": 0, "peticiones": 0}
    # Un mes sin cine es normal en un centro cultural: no es un fallo (no se cierra nada sin pases vistos)
    return guardar_sesiones(CINES[0], leer_cine(contadores), SALA, contadores)


if __name__ == "__main__":
    scrapear_casa_america()
