from datetime import date, datetime
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


def ahora_madrid() -> datetime:
    # fecha_hora se guarda en hora local de Madrid sin tzinfo.
    return datetime.now(MADRID).replace(tzinfo=None)


def hoy_madrid() -> date:
    return ahora_madrid().date()


def resolver_anio(mes: int, dia: int, hoy: date | None = None) -> int:
    """Año de una fecha de cartelera que no lo trae: el único que la deja entre
    30 días antes y 335 días después de hoy (Madrid). Así noviembre -> enero es el año
    siguiente y "31 de diciembre" leído el 2 de enero es el anterior."""
    hoy = hoy or hoy_madrid()
    for anio in (hoy.year - 1, hoy.year, hoy.year + 1):
        try:
            fecha = date(anio, mes, dia)
        except ValueError:  # 29 de febrero en año no bisiesto
            continue
        if -30 <= (fecha - hoy).days < 335:
            return anio
    raise ValueError(f"La fecha {dia}/{mes} no cae en la ventana de cartelera desde {hoy}")
