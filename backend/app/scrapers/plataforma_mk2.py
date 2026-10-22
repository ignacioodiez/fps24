"""Plantilla web común de los cines mk2 (cinepazmadrid.es y mk2palaciodehielo.es, ruta /es/cartelera).
Cada día es una pestaña .rotulo_dia[data-num] ("Hoy", "Mañana", "Sábado 24/10") y su cartelera está, ya cargada
y oculta salvo la activa, en .contenedor_cines.cines-<data-num>, con un .horarios por película."""
import re
from datetime import date, timedelta

from app.scrapers.comun import hoy_madrid, obtener_logger, resolver_anio

log = obtener_logger(__name__)


def parsear_rotulo(texto):
    """'Hoy', 'Mañana', 'Sábado 24/10' -> date. ValueError si no cuadra."""
    texto = texto.strip().lower()
    if "hoy" in texto:
        return hoy_madrid()
    if "mañana" in texto:
        return hoy_madrid() + timedelta(days=1)
    match = re.search(r"(\d{1,2})/(\d{1,2})", texto)
    if not match:
        raise ValueError(f"Día no reconocido: {texto!r}")
    dia, mes = map(int, match.groups())
    return date(resolver_anio(mes, dia), mes, dia)


def parsear_hora(texto):
    """'35mm15:45' -> (15, 45). ValueError si no hay HH:MM."""
    match = re.search(r"(\d{2}):(\d{2})", texto)
    if not match:
        raise ValueError(f"Hora no reconocida: {texto!r}")
    return int(match.group(1)), int(match.group(2))


def leer_dias(page, cine, max_dias):
    """Las max_dias primeras pestañas -> [(data_num, date)]; las que no se entienden se avisan y se saltan."""
    dias = []
    for rotulo in page.locator(".rotulo_dia").all()[:max_dias]:
        texto = rotulo.inner_text()
        data_num = rotulo.get_attribute("data-num")
        try:
            if not data_num:
                raise ValueError(f"Pestaña sin data-num: {texto!r}")
            dias.append((data_num, parsear_rotulo(texto)))
        except ValueError:
            log.warning("%s: día descartado", cine, exc_info=True)
    return dias
