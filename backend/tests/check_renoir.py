"""Self-check del idioma, la sala, los ciclos y la lectura de filas del scraper de Renoir. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_renoir.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from datetime import date

from app.scrapers.cines import renoir
from app.scrapers.cines.renoir import CINES, SLUGS, idioma_de, sala_de, separar_ciclo
from app.scrapers.comun import abrir_pagina

assert set(SLUGS) == set(CINES)
assert idioma_de(["de Jonatan Etzler", "Versión Original subtitulada a Castellano"]) == "VOSE"
assert idioma_de(["Versión Original Castellano"]) == "Español"
assert idioma_de([]) == "Español"

assert sala_de("sala 01", "Renoir Retiro") == "Renoir Retiro (Sala 01)"
assert sala_de("Sala 11 ", "Renoir Princesa") == "Renoir Princesa (Sala 11)"
assert sala_de("20:15", "Renoir Retiro") == "Renoir Retiro"
assert sala_de(None, "Renoir Retiro") == "Renoir Retiro"
assert separar_ciclo("LOS PARAGUAS DE CHERBURGO [WILDER CINEMA]") == ("LOS PARAGUAS DE CHERBURGO", "WILDER CINEMA")
assert separar_ciclo("RE-ANIMATOR [OBSCURA VISIÓN] ") == ("RE-ANIMATOR", "OBSCURA VISIÓN")
assert separar_ciclo("NOSFERATU CON MÚSICA EN DIRECTO") == ("NOSFERATU CON MÚSICA EN DIRECTO", None)
assert separar_ciclo("[SOLO CICLO]") == ("[SOLO CICLO]", None)
assert separar_ciclo("A [B] C") == ("A [B] C", None)  # solo la etiqueta final

# --- lectura de filas: HTML real (27/10/2026) con pase especial btn-evento, más "+info" sin clase y una fila sin botón ---
HTML = """<div class="my-account-content d-none d-lg-block">
<div class="row">
  <div class="col-4 pl-0 pr-0">
    <a href="/pelicula/los-paraguas-de-cherburgo-wilder-cinema/">LOS PARAGUAS DE CHERBURGO [WILDER CINEMA]</a>
    <br><small style="color:#748294"><b> de Jacques Demy </b></small>
    <br><small>Versión Original subtitulada a Castellano</small>
  </div>
  <div class="col-7">
    <div class="pase-cartelera text-center ">
      <span style="font-size:12px">sala 06</span>
      <span><a href="https://www.pillalas.com/pase/1090712/" class="btn btn-evento">
               20:30
            </a></span>
      <a href="/pelicula/los-paraguas-de-cherburgo-wilder-cinema/">+info</a>
      <div class="pase-cartelera-tag">PASE ESPECIAL</div>
    </div>
  </div>
</div>
<div class="row">
  <div class="col-4"><a href="/pelicula/sin-boton/">SIN BOTÓN</a></div>
  <div class="col-7"><div class="pase-cartelera text-center"><span>sala 02</span><a href="/x/">+info</a></div></div>
</div>
</div>"""

resueltos, registrados, avisos = [], [], []
renoir.resolver_pelicula = lambda session, titulo, cine: (resueltos.append(titulo), (7, False))[1]
renoir.registrar_pase = lambda session, **pase: (registrados.append(pase), "creado")[1]


class Avisos(logging.Handler):
    def emit(self, record):
        avisos.append(record.getMessage())


renoir.log.addHandler(Avisos(logging.WARNING))
contadores = {"creado": 0, "actualizado": 0, "descartado": 0}
with abrir_pagina() as page:
    page.set_content(HTML)
    for fila in page.locator(".my-account-content.d-none.d-lg-block > .row").all():
        renoir._leer_fila(None, fila, date(2026, 10, 27), "Renoir Princesa", contadores)

assert resueltos == ["LOS PARAGUAS DE CHERBURGO"], resueltos
assert len(registrados) == 1, registrados
pase = registrados[0]
assert pase["fecha_hora"].isoformat() == "2026-10-27T20:30:00"
assert pase["sala"] == "Renoir Princesa (Sala 06)"
assert pase["idioma"] == "VOSE"
assert pase["link_compra"] == "https://www.pillalas.com/pase/1090712/"
assert pase["es_evento_especial"] is True  # por el ciclo, aunque resolver_pelicula diga False
assert contadores == {"creado": 1, "actualizado": 0, "descartado": 1}, contadores
assert len(avisos) == 1 and "SIN BOTÓN" in avisos[0] and "2026-10-27" in avisos[0], avisos
print("check_renoir OK")
