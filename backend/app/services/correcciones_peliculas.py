"""Correcciones manuales del emparejamiento título de la web -> película. Mandan sobre todo lo demás.

Clave: el título tal como sale en la web ("El odio (VOSE)") o ya limpio ("El odio"), que vale para
todas sus variantes (VOSE, 35mm, prefijos de ciclo...). Se comparan normalizados: da igual la
capitalización, las tildes o la puntuación. Primero se busca el título exacto y luego el limpio.

Valor:
- un tmdb_id (int): esa película de TMDB.
- SIN_TMDB: película propia con el título de la web, sin buscar en TMDB.
- IGNORAR: no es una película; sus pases se descartan.

Tras añadir una corrección, la siguiente ejecución del scraper registra los pases en la película
correcta y cerrar_ejecucion desactiva los que quedaron en la equivocada.
"""
SIN_TMDB = "sin_tmdb"
IGNORAR = "ignorar"

CORRECCIONES = {
    "Jujutsu Kaisen 0: La película": 810693,  # lo de tras ":" casaba con "La película" (1975)
    "IN THE COURT OF THE CRIMSON KING": 827484,  # en TMDB: "...: King Crimson at 50" (2022)
    "Euforia Bloque III: Erótica": SIN_TMDB,  # bloque de cortos; casaba con "Erótica" (1979)
    "Carmen's Pure Love": 215804,  # Doré, 1952; en TMDB "Carmen se enamora" / "Carmen's Innocent Love"
    "Torre Bela": 549342,  # Doré, 1975; en TMDB "Cooperativa Agrícola da Torre-Bela"
    "Fuefuki River": 219233,  # Doré, 1960; en TMDB "笛吹川" / "The River Fuefuki"
    "Hijas del bosque": 1599180,  # Cineteca, 2026; en TMDB solo "Daughters of the Forest"
    "Ozzy & Black Sabbath: Back to the Beginning": 1515139,  # en TMDB "Back to the Beginning: La despedida de Ozzy"
    "Hope: el primer impacto": 1058424,  # en TMDB solo "Hope" (2026)
}
