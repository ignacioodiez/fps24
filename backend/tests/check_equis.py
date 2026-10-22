"""Self-check del parser de enlaces de Sala Equis. No toca la red ni la BD.
Uso: docker compose exec api python tests/check_equis.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers.cines.equis import parsear_link

postback = ('javascript:WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions("ctl43", "", false, "", '
            '"numEntradas.aspx?idPelicula=2964&cine=EQUIS&fecha=22/10/2026&hora=19:30&sala=1", false, true))')
assert parsear_link(postback) == ("https://kinetike.com:83/views/numEntradas.aspx"
                                  "?idPelicula=2964&cine=EQUIS&fecha=22/10/2026&hora=19:30&sala=1")
assert parsear_link("numEntradas.aspx?x=1") == "https://kinetike.com:83/views/numEntradas.aspx?x=1"
assert parsear_link("https://otra.es/x") == "https://otra.es/x"
assert parsear_link(None) == ""
print("check_equis OK")
