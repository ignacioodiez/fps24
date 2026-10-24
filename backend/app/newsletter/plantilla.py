"""HTML y texto plano de los correos. Sin Jinja2 (no está instalado): funciones con html.escape en todo lo variable.
HTML de correo: 600 px, solo tablas y estilos en línea; el <style> solo añade lo que no se puede en línea (móvil y
modo oscuro), así que si un cliente lo ignora el correo sigue viéndose bien."""
from datetime import date
from html import escape

SITIO = "https://fps24.es"
MORADO = "#7c3aed"  # --primary de la web
FUENTE = "Arial,Helvetica,sans-serif"
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
ANCHO_POSTER = 264  # (600 - 2·12) / 2 columnas - 2·12 de margen

ESTILOS = f"""
body{{margin:0;padding:0;width:100%!important;-webkit-text-size-adjust:100%}}
img{{border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic}}
@media only screen and (max-width:599px){{
  .contenedor{{width:100%!important}}
  .col{{display:block!important;width:100%!important;box-sizing:border-box}}
  .poster{{width:100%!important;max-width:342px!important;height:auto!important}}
  .pad{{padding-left:16px!important;padding-right:16px!important}}
}}
@media (prefers-color-scheme:dark){{
  .fondo{{background-color:#0f0d16!important}}
  .caja{{background-color:#1b1726!important}}
  .texto{{color:#ece9f4!important}}
  .suave{{color:#a7a1b8!important}}
  .linea{{border-color:#2f2a3d!important}}
  .marca{{color:#a78bfa!important}}
}}
[data-ogsc] .texto{{color:#ece9f4!important}}
[data-ogsc] .suave{{color:#a7a1b8!important}}
[data-ogsc] .marca{{color:#a78bfa!important}}
"""


def dia_corto(fecha_hora) -> str:
    """«vie 31 oct · 20:30»"""
    return f"{DIAS[fecha_hora.weekday()]} {fecha_hora.day} {MESES[fecha_hora.month - 1][:3]} · {fecha_hora:%H:%M}"


def rango(desde: date, hasta: date) -> str:
    """«del 27 de octubre al 2 de noviembre»"""
    return f"del {desde.day} de {MESES[desde.month - 1]} al {hasta.day} de {MESES[hasta.month - 1]}"


def url_pelicula(id_) -> str:
    return f"{SITIO}/pelicula/{id_}"


def _sesion(f) -> str:
    return " · ".join([f["cine"], dia_corto(f["fecha_hora"])] + (["VOSE"] if f["vose"] else []))


def _meta(f) -> str:
    return " · ".join(filter(None, [str(f["anio"]) if f["anio"] else None,
                                    f"en {f['cines']} cine{'s' if f['cines'] != 1 else ''}"]))


def _boton(url, texto) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-top:12px">'
            f'<tr><td bgcolor="{MORADO}" style="background-color:{MORADO}">'
            f'<a href="{escape(url)}" style="display:inline-block;padding:11px 18px;font-family:{FUENTE};font-size:14px;'
            f'font-weight:bold;line-height:1;color:#ffffff;text-decoration:none">{escape(texto)}</a></td></tr></table>')


def _poster(f, ancho) -> str:
    alto = ancho * 3 // 2
    if not f["poster"]:  # hueco del mismo tamaño para que la cuadrícula no baile
        return (f'<div role="img" aria-label="{escape(f["titulo"])}" style="width:{ancho}px;height:{alto}px;'
                f'background-color:#e9e3f7"></div>')
    return (f'<a href="{escape(url_pelicula(f["id"]))}"><img class="{"poster" if ancho == ANCHO_POSTER else ""}" '
            f'src="{escape(f["poster"])}" width="{ancho}" height="{alto}" alt="Póster de {escape(f["titulo"])}" '
            f'style="display:block;width:{ancho}px;height:{alto}px;background-color:#e9e3f7;color:#18151f;'
            f'font-family:{FUENTE};font-size:13px"></a>')


def _tarjeta(f) -> str:
    return (f'<td class="col" width="50%" valign="top" style="padding:12px">{_poster(f, ANCHO_POSTER)}'
            f'<p class="texto" style="margin:12px 0 4px;font-family:{FUENTE};font-size:17px;line-height:1.3;'
            f'font-weight:bold;color:#18151f">{escape(f["titulo"])}</p>'
            f'<p class="suave" style="margin:0 0 6px;font-family:{FUENTE};font-size:13px;color:#5f5873">{escape(_meta(f))}</p>'
            f'<p class="texto" style="margin:0;font-family:{FUENTE};font-size:14px;line-height:1.4;color:#18151f">'
            f'Mejor sesión: {escape(_sesion(f))}</p>{_boton(url_pelicula(f["id"]), "Ver sesiones")}</td>')


def _fila_especial(f) -> str:
    return (f'<tr><td class="linea" style="padding:12px 0;border-top:1px solid #e6e1ef">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
            f'<td width="96" valign="top" style="width:96px">{_poster(f, 96)}</td>'
            f'<td valign="top" style="padding-left:16px">'
            f'<p class="texto" style="margin:0 0 4px;font-family:{FUENTE};font-size:16px;line-height:1.3;font-weight:bold;'
            f'color:#18151f">{escape(f["titulo"])}</p>'
            f'<p class="suave" style="margin:0 0 6px;font-family:{FUENTE};font-size:13px;color:#5f5873">{escape(_meta(f))}</p>'
            f'<p class="texto" style="margin:0;font-family:{FUENTE};font-size:14px;line-height:1.4;color:#18151f">'
            f'{escape(_sesion(f))}</p>{_boton(url_pelicula(f["id"]), "Ver sesiones")}</td></tr></table></td></tr>')


def _titulo_seccion(texto) -> str:
    return (f'<h2 class="texto" style="margin:0;font-family:{FUENTE};font-size:13px;letter-spacing:2px;'
            f'text-transform:uppercase;color:#18151f">{escape(texto)}</h2>')


def _vacio(texto) -> str:
    return f'<p class="suave" style="margin:12px 0 0;font-family:{FUENTE};font-size:14px;color:#5f5873">{escape(texto)}</p>'


def _documento(titulo, preheader, cuerpo, pie) -> str:
    """Esqueleto común: fondo de color de respaldo, cabecera FPS24, cuerpo y pie, todo en una tabla de 600 px."""
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="x-apple-disable-message-reformatting"><meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark"><title>{escape(titulo)}</title><style>{ESTILOS}</style></head>
<body class="fondo" style="margin:0;padding:0;background-color:#f4f1fb">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all">{escape(preheader)}</div>
<table role="presentation" class="fondo" width="100%" bgcolor="#f4f1fb" cellpadding="0" cellspacing="0" border="0" style="background-color:#f4f1fb">
<tr><td align="center" style="padding:24px 0">
<table role="presentation" class="contenedor" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px">
<tr><td class="caja pad" bgcolor="#ffffff" style="background-color:#ffffff;border-top:6px solid {MORADO};padding:28px 24px 8px">
<p class="marca" style="margin:0;font-family:{FUENTE};font-size:40px;line-height:1;font-weight:900;letter-spacing:-1px;color:{MORADO}">FPS24</p>
<h1 class="texto" style="margin:10px 0 0;font-family:{FUENTE};font-size:26px;line-height:1.2;color:#18151f">{escape(titulo)}</h1>
</td></tr>
{cuerpo}
<tr><td class="pad" style="padding:24px;font-family:{FUENTE};font-size:12px;line-height:1.6;color:#5f5873" align="center">
<p class="suave" style="margin:0 0 8px;color:#5f5873">{pie}</p>
<p class="suave" style="margin:0 0 8px;color:#5f5873">This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
</td></tr></table></td></tr></table></body></html>"""


def _enlace(url, texto) -> str:
    return f'<a href="{escape(url)}" style="color:{MORADO};text-decoration:underline">{escape(texto)}</a>'


def semanal(datos: dict, url_baja: str, contacto: str) -> tuple:
    """-> (asunto, html, texto) de la newsletter de la semana."""
    fechas = rango(datos["desde"], datos["hasta"])
    asunto = f"Esta semana en Madrid: estrenos y especiales {fechas}"
    titulos = [f["titulo"] for f in datos["estrenos"] + datos["especiales"]][:3]
    preheader = ("Con " + ", ".join(titulos) + " y más.") if titulos else "La cartelera de los cines de Madrid."

    estrenos = datos["estrenos"]
    filas = "".join("<tr>" + "".join(_tarjeta(f) for f in estrenos[i:i + 2])
                    + ('<td class="col" width="50%"></td>' if len(estrenos[i:i + 2]) == 1 else "") + "</tr>"
                    for i in range(0, len(estrenos), 2))
    cuerpo = (
        f'<tr><td class="caja pad" bgcolor="#ffffff" style="background-color:#ffffff;padding:0 24px 8px">'
        f'<p class="suave" style="margin:0;font-family:{FUENTE};font-size:15px;color:#5f5873">Lo que se estrena y las '
        f'sesiones especiales {escape(fechas)}.</p></td></tr>'
        f'<tr><td class="caja pad" bgcolor="#ffffff" style="background-color:#ffffff;padding:24px 24px 0">'
        f'{_titulo_seccion("Estrenos del viernes")}'
        + ("" if estrenos else _vacio("Esta semana no hay estrenos en nuestros cines."))
        + '</td></tr>'
        f'<tr><td class="caja" bgcolor="#ffffff" style="background-color:#ffffff;padding:0 12px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{filas}</table></td></tr>'
        f'<tr><td class="caja pad" bgcolor="#ffffff" style="background-color:#ffffff;padding:24px 24px 12px">'
        f'{_titulo_seccion("Sesiones especiales")}'
        + (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:12px">'
           f'{"".join(_fila_especial(f) for f in datos["especiales"])}</table>' if datos["especiales"]
           else _vacio("Esta semana no hay sesiones especiales destacadas."))
        + f'</td></tr><tr><td class="caja pad" bgcolor="#ffffff" align="center" style="background-color:#ffffff;padding:12px 24px 32px">'
        f'{_boton(SITIO, "Toda la cartelera en fps24.es")}</td></tr>'
    )
    pie = (f"Recibes este correo porque te suscribiste en fps24.es.<br>{_enlace(url_baja, 'Darte de baja')} · "
           f"{_enlace(SITIO + '/privacidad', 'Privacidad')} · Contacto: {_enlace('mailto:' + contacto, contacto)}")
    html = _documento("Esta semana en Madrid", preheader, cuerpo, pie)

    def bloque(f):
        return f"- {f['titulo']} ({_meta(f)})\n  Mejor sesión: {_sesion(f)}\n  {url_pelicula(f['id'])}"
    texto = "\n".join([
        "FPS24 · Esta semana en Madrid", f"Estrenos y sesiones especiales {fechas}.", "",
        "ESTRENOS DEL VIERNES", *(map(bloque, estrenos) if estrenos else ["Esta semana no hay estrenos en nuestros cines."]), "",
        "SESIONES ESPECIALES", *(map(bloque, datos["especiales"]) if datos["especiales"]
                                 else ["Esta semana no hay sesiones especiales destacadas."]), "",
        f"Toda la cartelera: {SITIO}", "", "--",
        "Recibes este correo porque te suscribiste en fps24.es.", f"Darte de baja: {url_baja}",
        f"Privacidad: {SITIO}/privacidad", f"Contacto: {contacto}",
        "This product uses the TMDB API but is not endorsed or certified by TMDB.",
    ])
    return asunto, html, texto


def confirmacion(url_confirmar: str, contacto: str) -> tuple:
    """-> (asunto, html, texto) del correo de doble opt-in."""
    asunto = "Confirma tu suscripción a FPS24 Esta semana en Madrid"
    cuerpo = (f'<tr><td class="caja pad" bgcolor="#ffffff" style="background-color:#ffffff;padding:8px 24px 32px">'
              f'<p class="texto" style="margin:0;font-family:{FUENTE};font-size:16px;line-height:1.5;color:#18151f">'
              f'Para recibir cada lunes los estrenos y las sesiones especiales de los cines de Madrid, confirma tu '
              f'email. Si no has sido tú, ignora este correo: no te escribiremos más.</p>'
              f'{_boton(url_confirmar, "Confirmar suscripción")}</td></tr>')
    pie = f"{_enlace(SITIO + '/privacidad', 'Privacidad')} · Contacto: {_enlace('mailto:' + contacto, contacto)}"
    html = _documento("Confirma tu suscripción", "Un clic y listo: la cartelera de Madrid cada lunes.", cuerpo, pie)
    texto = (f"FPS24 · Esta semana en Madrid\n\nPara recibir cada lunes los estrenos y las sesiones especiales de los "
             f"cines de Madrid, confirma tu email:\n{url_confirmar}\n\nSi no has sido tú, ignora este correo: no te "
             f"escribiremos más.\n\nPrivacidad: {SITIO}/privacidad\nContacto: {contacto}")
    return asunto, html, texto
