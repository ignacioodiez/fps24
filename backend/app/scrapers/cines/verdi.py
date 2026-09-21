import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial

def scrapear_verdi():
    # Target official Verdi website instead of FilmAffinity
    url = "https://madrid.cines-verdi.com/cartelera"
    print(f"🎹 Entering Verdi (Official Web Mode)...")

    with sync_playwright() as p:
        # Launch browser with bot evasion
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # Wait for the main collection of movies to load
            try:
                page.wait_for_selector(".collection article", timeout=15000)
            except Exception as e:
                print(f"  ⚠️ Cannot find movies. Saving debug screenshot to 'debug_verdi.png'...")
                page.screenshot(path="debug_verdi.png") 
                print(f"  ❌ Playwright Error: {e}")
                browser.close()
                return
            
            # Scroll down to ensure lazy-loaded items appear
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error loading web: {e}")
            browser.close()
            return

        # --- EXTRACTION ---
        # Select all movie blocks
        articles = page.locator(".collection article").all()
        print(f"  🔎 Found {len(articles)} movies.")
        
        nuevos_pases = 0

        with Session(engine) as session:
            for idx, article in enumerate(articles):
                try:
                    # Find movie title (it can be inside .syn header or figcaption)
                    titulo_elem = article.locator(".syn header h2").first
                    if not titulo_elem.count():
                        titulo_elem = article.locator("figcaption h2").first
                    
                    if not titulo_elem.count(): 
                        continue
                    
                    raw_titulo = titulo_elem.inner_text().strip() 
                    
                    # 1. Detect if it's a special event
                    es_especial = determinar_si_es_especial(raw_titulo, None)

                    # 2. Call the manager to get TMDB ID
                    pelicula_id, anio_peli = obtener_id_pelicula(raw_titulo, session)

                    if not pelicula_id: 
                        print(f"  ⚠️ Could not resolve TMDB ID for: {raw_titulo}")
                        continue

                    # Mark as special if older than 2023
                    if anio_peli and anio_peli < 2023:
                        es_especial = True

                    # 3. Find all available dates for this specific movie in its hidden select
                    opciones = article.locator("select.dates-select option").all()
                    fechas_disponibles = []
                    for op in opciones:
                        val = op.get_attribute("value")
                        if val and val not in fechas_disponibles:
                            fechas_disponibles.append(val)

                    if not fechas_disponibles:
                        print(f"  ⚠️ No showtimes/dates found for: {raw_titulo}")
                        continue

                    # 4. Loop through each date to update the DOM and read showtimes
                    for fecha_str in fechas_disponibles:
                        # Select the date to trigger Alpine.js visibility update
                        article.locator("select.dates-select").select_option(value=fecha_str, force=True)
                        page.wait_for_timeout(200) # Give Alpine.js time to update the UI
                        
                        # Grab all showtime buttons
                        pases_nodos = article.locator(".info-performances .button-buy").all()
                        
                        for pase in pases_nodos:
                            # Skip if this showtime is for a different date (hidden by Alpine)
                            if not pase.is_visible():
                                continue
                            
                            hora_txt = pase.locator("time").inner_text().strip()
                            link_compra = pase.get_attribute("href")
                            
                            # Skip sold out tickets or unclickable links
                            if not link_compra or link_compra == "#":
                                continue

                            # Detect language from the data-attr string
                            version_attr = pase.get_attribute("data-attr") or ""
                            idioma = "VOSE" if "V.O." in version_attr.upper() or "SUB" in version_attr.upper() else "Español"

                            try:
                                # Parse full datetime (fecha_str is formatted as YYYY-MM-DD)
                                fecha_completa_str = f"{fecha_str} {hora_txt}"
                                fecha_final = datetime.strptime(fecha_completa_str, "%Y-%m-%d %H:%M")
                                
                                # Check if showing already exists in DB
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == "Cines Verdi",
                                    Pase.pelicula_id == pelicula_id,
                                    Pase.fecha_hora == fecha_final,
                                    Pase.idioma == idioma
                                )).first()
                                
                                if not existe:
                                    nuevo = Pase(
                                        cine="Cines Verdi",
                                        pelicula_id=pelicula_id,
                                        fecha_hora=fecha_final,
                                        sala="Cines Verdi",
                                        precio="Consultar",
                                        link_compra=link_compra,
                                        idioma=idioma,
                                        es_evento_especial=es_especial 
                                    )
                                    session.add(nuevo)
                                    nuevos_pases += 1

                            except ValueError as ve:
                                print(f"  ⚠️ Date parsing error for {fecha_completa_str}: {ve}")
                                continue

                except Exception as e:
                    titulo_error = raw_titulo if 'raw_titulo' in locals() else f"Index {idx}"
                    print(f"  ❌ Error processing movie '{titulo_error}': {e}")
                    continue

            session.commit()
            print(f"🏁 FINISH VERDI. {nuevos_pases} showings saved.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_verdi()