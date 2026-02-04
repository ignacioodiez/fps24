import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_verdi():
    # URL de Cines Verdi Madrid en FilmAffinity
    url = "https://www.filmaffinity.com/es/theater-showtimes.php?id=313"
    print(f"🎹 Entrando en Verdi (Vía FilmAffinity)...")

    with sync_playwright() as p:
        # headless=False ayuda a veces con Cloudflare en FilmAffinity
        # Si te da problemas en el servidor, prueba a ponerlo en True
        browser = p.chromium.launch(headless=True, channel="chrome") 
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # --- COOKIES ---
            try:
                boton_cookie = page.get_by_text("ACEPTAR", exact=True).or_(page.get_by_text("AGREE"))
                if boton_cookie.is_visible(timeout=4000):
                    boton_cookie.click()
            except: pass
            
            # --- ESPERAR CONTENIDO ---
            print("   ⏳ Esperando lista de películas...")
            try:
                page.wait_for_selector(".fa-content-card.movie", timeout=15000)
            except:
                print("   ⚠️ Timeout o bloqueo de Cloudflare.")
                # print(f"   📄 Título: {page.title()}")
            
            # Scroll para cargar imágenes (Lazy load)
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(2)

        except Exception as e:
            print(f"❌ Error cargando FilmAffinity: {e}")
            browser.close()
            return

        # --- EXTRACCIÓN ---
        peliculas = page.locator(".fa-content-card.movie").all()
        print(f"   🔎 Encontradas {len(peliculas)} películas.")
        
        nuevos_pases = 0

        with Session(engine) as session:
            for peli_card in peliculas:
                try:
                    # 1. TÍTULO
                    titulo_elem = peli_card.locator(".mv-title span.fs-5").first
                    if not titulo_elem.count(): continue
                    
                    raw_titulo = titulo_elem.inner_text().strip()
                    idioma = "Español"
                    titulo = raw_titulo

                    # Limpieza de título
                    if "(VOSE)" in raw_titulo.upper():
                        idioma = "VOSE"
                        titulo = raw_titulo.replace("(VOSE)", "").replace("(V.O. SUB. CASTELLANO)", "").strip()
                    elif "(CASTELLANO)" in raw_titulo.upper():
                        titulo = raw_titulo.replace("(CASTELLANO)", "").strip()
                    
                    # Quitar paréntesis residuales
                    titulo = titulo.split("(")[0].strip()

                    # 2. INTELIGENCIA TMDB
                    datos_tmdb = buscar_datos_tmdb(titulo)
                    
                    poster_final = datos_tmdb.get("poster")
                    nota_tmdb = datos_tmdb.get("nota")
                    try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                    except: anio_tmdb = None

                    # Fallback Poster (FilmAffinity)
                    if not poster_final:
                        img_elem = peli_card.locator(".mc-poster img").first
                        if img_elem.count():
                            srcset = img_elem.get_attribute("data-srcset") or img_elem.get_attribute("srcset")
                            if srcset:
                                poster_final = srcset.split(",")[-1].strip().split(" ")[0]
                            else:
                                poster_final = img_elem.get_attribute("src")

                    # 3. ESPECIAL?
                    es_especial = es_programacion_especial("Cines Verdi", titulo, anio_tmdb)

                    # 4. HORARIOS
                    filas_dias = peli_card.locator(".sessions .row[data-sess-date]").all()
                    
                    for fila in filas_dias:
                        fecha_str = fila.get_attribute("data-sess-date") # "2026-02-04"
                        if not fecha_str: continue
                        
                        botones = fila.locator(".times-wrap a.btn").all()
                        
                        for boton in botones:
                            hora_txt = boton.inner_text().strip()
                            link_compra = boton.get_attribute("href")
                            
                            try:
                                fecha_completa_str = f"{fecha_str} {hora_txt}"
                                fecha_final = datetime.strptime(fecha_completa_str, "%Y-%m-%d %H:%M")
                                
                                # GUARDAR
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == "Cines Verdi",
                                    Pase.pelicula == titulo,
                                    Pase.fecha_hora == fecha_final,
                                    Pase.idioma == idioma
                                )).first()
                                
                                if not existe:
                                    nuevo = Pase(
                                        cine="Cines Verdi",
                                        pelicula=titulo,
                                        fecha_hora=fecha_final,
                                        sala="Cines Verdi",
                                        precio="Consultar",
                                        link_compra=link_compra,
                                        poster_url=poster_final,
                                        idioma=idioma,
                                        es_evento_especial=es_especial,
                                        nota_tmdb=nota_tmdb,
                                        anio=anio_tmdb
                                    )
                                    session.add(nuevo)
                                    nuevos_pases += 1

                            except ValueError: continue

                except Exception as e:
                    continue

            session.commit()
            print(f"🏁 FIN VERDI. {nuevos_pases} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_verdi()