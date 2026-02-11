import time
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

# Importamos la base de datos
from app.database.engine import engine
from app.database.models import Pase, Pelicula
# 👇 IMPORTANTE: Usamos tu gestor centralizado
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial

class CinesaFilmAffinityScraper:
    def __init__(self):
        self.cines = [
            {"id": "cinesa-proyecciones", "fa_id": "271", "nombre": "Cinesa Proyecciones"},
            {"id": "cinesa-principe-pio", "fa_id": "270", "nombre": "Cinesa Príncipe Pío"}
        ]
        self.base_url = "https://www.filmaffinity.com/es/theater-showtimes.php?id={}"

    def get_sessions(self):
        """
        Devuelve una lista de diccionarios (NO objetos Pase todavía) con los datos crudos.
        Ej: [{'titulo': 'Avatar', 'cine': 'Cinesa...', 'fecha': datetime...}, ...]
        """
        datos_crudos = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            for cine in self.cines:
                url = self.base_url.format(cine["fa_id"])
                print(f"🎬 Scrapeando {cine['nombre']} con Playwright...")
                
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")

                    try:
                        boton_cookie = page.get_by_role("button", name="ACEPTAR").or_(page.get_by_text("AGREE"))
                        if boton_cookie.is_visible(timeout=3000):
                            boton_cookie.click()
                    except: pass

                    try:
                        page.wait_for_selector(".fa-content-card.movie", timeout=10000)
                    except:
                        print(f"⚠️ No se encontraron películas en {cine['nombre']}")
                        continue

                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1)

                    content = page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    movie_cards = soup.select("div.fa-content-card.movie")
                    
                    print(f"   ℹ️ Encontradas {len(movie_cards)} películas.")

                    for card in movie_cards:
                        title_tag = card.select_one("div.mc-title a")
                        if not title_tag: continue
                        
                        titulo_raw = title_tag.text.strip()
                        
                        showtimes_block = card.select_one("div.movie-showtimes-n")
                        if not showtimes_block: continue
                            
                        title_showtime_tag = showtimes_block.select_one("div.mv-title span.fs-5")
                        titulo_sesion = title_showtime_tag.text.strip() if title_showtime_tag else titulo_raw
                        
                        es_vose = "(VOSE)" in titulo_sesion
                        titulo_limpio = titulo_sesion.replace("(VOSE)", "").strip()

                        # NOTA: Ya no sacamos el poster aquí, porque lo hace el gestor_peliculas con TMDB

                        day_rows = showtimes_block.select("div.row[data-sess-date]")
                        
                        for row in day_rows:
                            fecha_str = row.get("data-sess-date")
                            if not fecha_str: continue

                            time_buttons = row.select("div.sess-times a.btn")
                            
                            for btn in time_buttons:
                                hora_str = btn.text.strip()
                                link_compra = btn.get("href")
                                sala_info = btn.get("title", "").replace("Sala", "").strip()
                                
                                try:
                                    fecha_hora_dt = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")
                                    
                                    # Guardamos los datos crudos para procesarlos luego
                                    datos_crudos.append({
                                        "titulo": titulo_limpio,
                                        "cine": cine["nombre"],
                                        "sala": sala_info if sala_info else None,
                                        "fecha_hora": fecha_hora_dt,
                                        "link": link_compra,
                                        "idioma": "VOSE" if es_vose else "ESPAÑOL"
                                    })
                                    
                                except ValueError:
                                    continue

                except Exception as e:
                    print(f"❌ Error en {cine['nombre']}: {e}")
                
                finally:
                    context.close()

            browser.close()

        return datos_crudos

# 👇 AHORA SÍ: LA FUNCIÓN MAESTRA QUE USA TU GESTOR 👇
def scrapear_cinesa():
    print("🍿 Ejecutando Scraper Cinesa (Integrado con Gestor TMDB)...")
    scraper = CinesaFilmAffinityScraper()
    datos_pases = scraper.get_sessions() # Devuelve lista de diccionarios
    
    if not datos_pases:
        print("📭 No se han encontrado pases.")
        return

    print(f"💾 Procesando {len(datos_pases)} pases...")
    
    with Session(engine) as session:
        nuevos_pases = 0
        
        for dato in datos_pases:
            try:
                # 1. USAMOS TU GESTOR PARA OBTENER EL ID (O CREARLA CON TMDB)
                # Esto rellena poster, sinopsis, trailer, etc. automáticamente
                pelicula_id, _ = obtener_id_pelicula(dato["titulo"], session)
                
                if not pelicula_id:
                    print(f"⚠️ Saltando pase, no se pudo identificar peli: {dato['titulo']}")
                    continue

                # 2. Comprobar si el pase ya existe
                existe = session.exec(select(Pase).where(
                    Pase.cine == dato["cine"],
                    Pase.pelicula_id == pelicula_id,
                    Pase.fecha_hora == dato["fecha_hora"],
                    Pase.sala == dato["sala"]
                )).first()

                if not existe:
                    # 3. Detectar evento especial (lógica simple)
                    tit_lower = dato["titulo"].lower()
                    es_especial = determinar_si_es_especial(dato["titulo"], None) # No hay año en datos_crudos

                    # 4. Crear el Pase
                    nuevo_pase = Pase(
                        pelicula_id=pelicula_id,
                        cine=dato["cine"],
                        sala=dato["sala"],
                        fecha_hora=dato["fecha_hora"],
                        precio="Consultar",
                        link_compra=dato["link"],
                        idioma=dato["idioma"],
                        es_evento_especial=es_especial
                    )
                    session.add(nuevo_pase)
                    nuevos_pases += 1

            except Exception as e:
                print(f"⚠️ Error procesando pase de '{dato['titulo']}': {e}")
                continue
        
        session.commit()
        print(f"🏁 FIN CINESA. {nuevos_pases} pases guardados correctamente en la BD.")

if __name__ == "__main__":
    scrapear_cinesa()