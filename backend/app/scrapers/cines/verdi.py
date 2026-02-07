import time
import re  # <--- IMPORTANTE: Necesitamos RE para quitar los minutos
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula

def scrapear_verdi():
    url = "https://www.filmaffinity.com/es/theater-showtimes.php?id=313"
    print(f"🎹 Entrando en Verdi (Modo Corrección Minutos)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # Cookies
            try:
                boton_cookie = page.get_by_role("button", name="ACEPTAR").or_(page.get_by_text("AGREE"))
                if boton_cookie.is_visible(timeout=3000):
                    boton_cookie.click()
            except: pass
            
            # Esperar contenido
            try:
                page.wait_for_selector(".fa-content-card.movie", timeout=10000)
            except:
                print("   ⚠️ No encuentro películas. Revisa el navegador.")
                browser.close()
                return
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error cargando web: {e}")
            browser.close()
            return

        # --- EXTRACCIÓN ---
        peliculas = page.locator(".fa-content-card.movie").all()
        print(f"   🔎 Encontradas {len(peliculas)} películas.")
        
        nuevos_pases = 0

        with Session(engine) as session:
            for peli_card in peliculas:
                try:
                    titulo_elem = peli_card.locator(".mv-title").first
                    if not titulo_elem.count(): continue
                    
                    raw_titulo = titulo_elem.inner_text().strip() # Ej: "TRES ADIOSES 120 MINUTOS"
                    
                    # --- ✂️ CORRECCIÓN: QUITAR MINUTOS ---
                    # Buscamos cualquier número seguido de "MINUTOS" al final y lo borramos
                    titulo_limpio = re.sub(r'\s\d+\s*MINUTOS$', '', raw_titulo, flags=re.IGNORECASE).strip()
                    
                    # Idioma
                    idioma = "Español"
                    if "(VOSE)" in titulo_limpio.upper() or "V.O.S.E." in titulo_limpio.upper():
                        idioma = "VOSE"
                    
                    # Llamamos al gestor con el título YA LIMPIO de minutos
                    pelicula_id, anio_peli = obtener_id_pelicula(titulo_limpio, session)

                    # Especial?
                    es_especial = False
                    if anio_peli and anio_peli < 2023:
                        es_especial = True

                    # Horarios
                    filas_dias = peli_card.locator(".sessions .row[data-sess-date]").all()
                    
                    for fila in filas_dias:
                        fecha_str = fila.get_attribute("data-sess-date")
                        if not fecha_str: continue
                        
                        botones = fila.locator(".times-wrap a.btn").all()
                        for boton in botones:
                            hora_txt = boton.inner_text().strip()
                            link_compra = boton.get_attribute("href")
                            
                            try:
                                fecha_completa_str = f"{fecha_str} {hora_txt}"
                                fecha_final = datetime.strptime(fecha_completa_str, "%Y-%m-%d %H:%M")
                                
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

                            except ValueError: continue

                except Exception as e:
                    continue

            session.commit()
            print(f"🏁 FIN VERDI. {nuevos_pases} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_verdi()