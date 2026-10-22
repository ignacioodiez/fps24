# Contrato de scrapers

Reglas para cualquier scraper nuevo o migrado. Los scrapers que aún no se han migrado (`app/scrapers/cines/`) no las cumplen; no los toméis como modelo.
La plantilla completa está en `app/scrapers/_plantilla.py`: no se registra ni se lanza, solo se copia.

## Reglas

1. **Un archivo por fuente** en `app/scrapers/cines/<nombre>.py`, con una función pública `scrapear_<nombre>()` sin argumentos.
2. **Cabecera de 3 líneas** (docstring del módulo): qué web lee, cómo extrae los datos y qué suele romperse.
3. **`CINES`**: constante con los nombres canónicos (los de `CINES_CONOCIDOS` en `app/services/cines.py`) que cubre la fuente. El nombre del cine sale siempre de esta constante, nunca del texto de la web. Si la web distingue sedes, el scraper elige entre los valores de `CINES`.
4. **Persistencia solo con `registrar_pase`** (`app/services/pases.py`). No hay `select(Pase)` ni `Pase(...)` en el scraper.
5. **Película y "especial" solo con `resolver_pelicula(session, titulo_raw, cine, anio_web=None)`** (`app/services/gestor_peliculas.py`). Pásale el título **tal como aparece en la web**: el scraper no limpia el título ni decide si el pase es especial. Si la web da el año de la película, pásalo en `anio_web`. Si devuelve `None` como id, salta la película (el aviso ya queda en el log). Si TMDB no la encuentra o no responde, la película se guarda sin TMDB y `reintentar_sin_tmdb` vuelve a buscarla al final de `lanzar_todo` (a los 7 días o en la siguiente ejecución); el scraper no hace nada especial.
6. **`sala`**: un valor estable entre ejecuciones (`"2"`, `"Sala 2"`, `"Sala Berlanga"`) o `None`. Nunca un texto que cambie (aforo, "últimas entradas"…), porque forma parte de la identidad del pase.
7. **`idioma`**: `"Español"` o `"VOSE"`. `registrar_pase` normaliza las variantes ("ESPAÑOL", "V.O.S.E."…) y deja un WARNING si recibe otro valor.
8. **Errores**:
   - Si la fuente no carga o no devuelve nada, **se lanza una excepción** (la de Playwright o `FuenteNoDisponible`). Nada de `print` + `return`.
   - Un item malo (un pase o una película que no se puede leer) se registra con `log.warning(...)` y se sigue con el siguiente.
   - Captura solo el error que esperas del item (normalmente `ValueError` al parsear). Prohibido `except: pass`, `except: continue` y `except Exception` silenciosos.
9. **Fechas** con los helpers de `app/scrapers/comun.py`:
   - `numero_mes("Enero")`, `numero_mes("sept.")`: no hay diccionarios de meses propios.
   - `resolver_anio(mes, dia)` cuando la web no da el año.
   - `hoy_madrid()` / `ahora_madrid()` cuando haga falta "hoy". Nunca `datetime.now()` suelto: el contenedor está en UTC.
   - `fecha_hora` es hora de Madrid **sin zona** y sin segundos ni microsegundos sueltos.
10. **Logging, no `print`**: `log = obtener_logger(__name__)` a nivel de módulo. Escribe en stdout con el formato `fecha NIVEL [modulo] mensaje`. Al final, una línea `log.info` con los contadores.
11. **Una sesión por ejecución y `session.commit()` al final**. `resolver_pelicula` solo hace flush (nunca commit): si el scraper falla antes del commit, no se guarda nada, ni pases ni películas nuevas. Sus errores de base de datos no se capturan: deja que suban.
12. **Playwright con `abrir_pagina()`**: headless, user agent de escritorio, viewport 1920×1080, `es-ES` y zona `Europe/Madrid`. Ajusta por scraper `timeout_ms` (esperas y clics, 15 s por defecto) y `navegacion_ms` (`goto`, 60 s por defecto). Cualquier otra opción de `browser.new_context` se pasa como argumento con nombre y pisa el valor por defecto.
13. **Sin archivos de depuración**: el scraper no escribe capturas, volcados de HTML ni otros archivos en el directorio de trabajo. Solo se permite si la variable de entorno `SCRAPERS_DEBUG=1` está activada de forma explícita, y en ese caso se escriben en `tempfile.gettempdir()`, nunca dentro del repo.
14. **Cómo se ejecuta**: siempre a través del registro de scrapers y `ejecutar_scraper`. Para registrar uno nuevo, añade su módulo a la tupla de `REGISTRO` en `app/run_scrapers.py`, en el orden en que debe ejecutarse: el nombre corto es el del módulo, y la función y los cines salen de `scrapear_<nombre>` y `CINES`. `tests/check_run_scrapers.py` falla si un módulo de `app/scrapers/cines/` no está registrado o si un cine no está en `CINES_CONOCIDOS`. Para lanzar solo algunos: `docker compose exec api python -m app.run_scrapers --solo dore,equis`.
15. **Esperas explícitas**: después de un scroll o una carga diferida, espera explícitamente a un elemento (`locator.wait_for()`, `page.wait_for_selector()`); una espera fija no basta.
16. **Fuentes HTTP/JSON** (sin navegador): pide con `obtener_json(url)` de `app/scrapers/comun.py` (User-Agent de navegador, timeout, 1 reintento; 403/429/5xx, error de red o JSON inválido lanzan `FuenteNoDisponible`). Sé educado: pausa entre peticiones (≥ 0,3 s), un tope de peticiones por ejecución que lance `FuenteNoDisponible` si se supera, y nada de peticiones en paralelo. Si el JSON no tiene la forma esperada (faltan claves), lanza `FuenteNoDisponible`; si falla solo un item, `log.warning` y sigue. La lectura del JSON va en una función sin BD que se pueda probar offline con una respuesta de ejemplo (ver `plataforma_sensacine.py` y `tests/check_sensacine.py`).

## Cómo probar un scraper

Siempre en Docker local (`docker compose up`), nunca contra producción.

1. **Dos ejecuciones seguidas.** La segunda no debe crear pases: en su línea final de log, `creado` tiene que ser 0 y todo debe salir como `actualizado`. Si crea pases, algo de la identidad del pase cambia entre ejecuciones (sala, idioma, segundos de la hora…).
   ```sh
   docker compose exec api python -c "from app.scrapers.cines.<nombre> import scrapear_<nombre>; scrapear_<nombre>()"
   docker compose exec api python -c "from app.scrapers.cines.<nombre> import scrapear_<nombre>; scrapear_<nombre>()"
   ```
2. **Todos los pases tienen `cine_id`.** Debe dar 0 para los cines del scraper:
   ```sh
   docker compose exec db psql -U fps24 -d fps24 -c "select cine, count(*) from pase where cine_id is null group by cine;"
   ```
   (Los scrapers sin migrar todavía crean pases sin `cine_id`; solo cuentan las filas de tus cines.)
3. **Sus `CINES` están en `CINES_CONOCIDOS`.** No debe imprimir nada:
   ```sh
   docker compose exec api python -c "from app.scrapers.cines.<nombre> import CINES; from app.services.cines import CINES_CONOCIDOS; print([c for c in CINES if c not in CINES_CONOCIDOS] or '')"
   ```
   Además, en el log no debe aparecer `Cine desconocido`.
4. **Tres ejecuciones seguidas.** Ejecútalo 3 veces seguidas: el total de pases vistos debe ser estable. Si varía de una ejecución a otra sin que la web haya cambiado, hay una condición de carrera.

## Ejemplo mínimo

```python
"""Lee: https://ejemplo.com/cartelera.
Extrae: tarjetas .pelicula con enlaces .pase ("17 de enero 19:30").
Se rompe si: cambian las clases o el formato de la fecha."""
from datetime import datetime

from sqlmodel import Session

from app.database.engine import engine
from app.scrapers.comun import FuenteNoDisponible, abrir_pagina, numero_mes, obtener_logger, resolver_anio
from app.services.gestor_peliculas import resolver_pelicula
from app.services.pases import registrar_pase

URL = "https://ejemplo.com/cartelera"
CINES = ["Cine Doré"]
log = obtener_logger(__name__)


def scrapear_ejemplo():
    cine = CINES[0]
    with abrir_pagina(navegacion_ms=90_000) as page, Session(engine) as session:
        page.goto(URL)
        tarjetas = page.locator(".pelicula").all()
        if not tarjetas:
            raise FuenteNoDisponible(URL)
        for tarjeta in tarjetas:
            titulo = tarjeta.locator("h2").inner_text()
            pelicula_id, especial = resolver_pelicula(session, titulo, cine)
            if pelicula_id is None:
                continue
            for pase in tarjeta.locator("a.pase").all():
                try:
                    dia, _, mes, hora = pase.inner_text().split()  # "17 de enero 19:30"
                    dia, mes = int(dia), numero_mes(mes)
                    h, m = map(int, hora.split(":"))
                    registrar_pase(session, cine=cine, pelicula_id=pelicula_id,
                                   fecha_hora=datetime(resolver_anio(mes, dia), mes, dia, h, m),
                                   sala=None, idioma="VOSE", precio="Consultar",
                                   link_compra=pase.get_attribute("href"), es_evento_especial=especial)
                except ValueError:
                    log.warning("Pase descartado: %r", pase.inner_text())
        session.commit()
```
