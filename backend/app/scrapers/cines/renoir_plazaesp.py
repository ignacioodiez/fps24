import re
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase

def scrapear_renoir_plazaesp():
    # URL base del Princesa (podríamos cambiarlo por el Plaza de España fácilmente)
    BASE_URL = "https://www.cinesrenoir.com/cine/renoir-plaza-de-espana/cartelera/"
    
    # Cuántos días queremos mirar
    DIAS_A_ESCANEAR = 7

    with sync_playwright() as p:
        print("🤴 Entrando en Cines Renoir Plaza de España...")
        browser = p.chromium.launch(headless=True) # Modo fantasma activado
        page = browser.new_page()
        
        fecha_actual = datetime.now()
        nuevos_pases = 0

        with Session(engine) as session:
            for i in range(DIAS_A_ESCANEAR):
                # 1. CONSTRUIR URL DEL DÍA
                fecha_target = fecha_actual + timedelta(days=i)
                fecha_str_url = fecha_target.strftime("%Y-%m-%d") # Formato 2026-01-17
                url_dia = f"{BASE_URL}?fecha={fecha_str_url}"
                
                print(f"   📅 Analizando: {fecha_target.strftime('%d/%m/%Y')}")
                
                try:
                    page.goto(url_dia, timeout=60000)
                    # Esperamos a que cargue la lista principal
                    page.wait_for_selector(".shop_list_area", timeout=10000)
                except:
                    print(f"      ⚠️ Error cargando la fecha {fecha_str_url}")
                    continue

                # 2. SELECCIONAR SOLO LA VISTA DE ESCRITORIO (Para evitar duplicados)
                # Buscamos el contenedor que tiene la clase 'd-lg-block'
                contenedor_desktop = page.locator(".my-account-content.d-none.d-lg-block")
                
                # Cada fila dentro de ese contenedor es una peli
                filas_peli = contenedor_desktop.locator("> .row").all()
                
                if not filas_peli:
                    print("      (Sin sesiones o web cambiada)")
                    continue

                for fila in filas_peli:
                    try:
                        # --- TÍTULO ---
                        # Está en el col-4 dentro de un enlace
                        titulo_elem = fila.locator(".col-4 a").first
                        if not titulo_elem.count(): continue
                        titulo = titulo_elem.inner_text().strip().upper()

                        # --- POSTER ---
                        # Está en el col-1
                        poster_elem = fila.locator(".col-1 img").first
                        poster_url = poster_elem.get_attribute("src") if poster_elem.count() else None

                        # --- IDIOMA ---
                        # Buscamos en los <small> del col-4
                        textos_small = fila.locator(".col-4 small").all_inner_texts()
                        idioma = "Desconocido"
                        for texto in textos_small:
                            texto_low = texto.lower()
                            if "subtitulada" in texto_low:
                                idioma = "VOSE"
                                break
                            elif "castellano" in texto_low or "español" in texto_low:
                                idioma = "Español"
                                break

                        # --- SESIONES (HORAS) ---
                        # Están en el col-7. Cada hora es un .text-center
                        bloques_hora = fila.locator(".col-7 .text-center").all()
                        
                        for bloque in bloques_hora:
                            # La hora es el texto del botón
                            boton = bloque.locator("a.btn-primary").first
                            if not boton.count(): continue
                            
                            hora_txt = boton.inner_text().strip()
                            link_compra = boton.get_attribute("href")
                            
                            # Extraer hora
                            match_h = re.search(r"(\d{2}:\d{2})", hora_txt)
                            if not match_h: continue
                            h, m = map(int, match_h.group(1).split(":"))
                            
                            # Crear fecha completa
                            fecha_final = fecha_target.replace(hour=h, minute=m, second=0, microsecond=0)
                            
                            # Sala (a veces está en un span encima del botón)
                            sala = "Renoir Plaza de España"
                            sala_elem = bloque.locator("span").first
                            if sala_elem.count() and "sala" in sala_elem.inner_text().lower():
                                num_sala = sala_elem.inner_text().lower().replace("sala", "").strip()
                                sala = f"Renoir Plaza de España (Sala {num_sala})"
                            # GUARDAR EN BBDD
                            existe = session.exec(select(Pase).where(
                                Pase.cine == "Renoir Plaza de España",
                                Pase.pelicula == titulo,
                                Pase.fecha_hora == fecha_final,
                                Pase.idioma == idioma # Importante chequear idioma ahora
                            )).first()
                            
                            if not existe:
                                nuevo = Pase(
                                    cine="Renoir Plaza de España",
                                    pelicula=titulo,
                                    fecha_hora=fecha_final,
                                    sala=sala,
                                    precio="Consultar", # Renoir varía precio
                                    link_compra=link_compra,
                                    poster_url=poster_url,
                                    idioma=idioma
                                )
                                session.add(nuevo)
                                nuevos_pases += 1
                                print(f"      ✅ [{idioma}] {titulo[:20]}... -> {hora_txt}")

                    except Exception as e:
                        # print(f"Error en una peli: {e}")
                        pass
                
                session.commit()
                # Pausa de cortesía entre días
                time.sleep(1)

            print(f"🏁 FIN. {nuevos_pases} pases recuperados de Renoir Plaza de España.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_renoir_plazaesp()