import time
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_renoir_retiro():
    nombre_cine = "Renoir Retiro"
    BASE_URL = "https://www.cinesrenoir.com/cine/renoir-retiro/cartelera/"
    DIAS_A_ESCANEAR = 7

    print(f"🎹 Entrando en {nombre_cine}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        fecha_actual = datetime.now()
        nuevos_pases = 0

        with Session(engine) as session:
            for i in range(DIAS_A_ESCANEAR):
                # 1. CONSTRUIR URL DEL DÍA
                fecha_target = fecha_actual + timedelta(days=i)
                fecha_str_url = fecha_target.strftime("%Y-%m-%d")
                url_dia = f"{BASE_URL}?fecha={fecha_str_url}"
                
                print(f"   📅 Analizando: {fecha_target.strftime('%d/%m/%Y')}")
                
                try:
                    page.goto(url_dia, timeout=60000)
                    page.wait_for_selector(".shop_list_area", timeout=10000)
                except:
                    continue

                # 2. SELECCIONAR VISTA DE ESCRITORIO
                contenedor_desktop = page.locator(".my-account-content.d-none.d-lg-block")
                filas_peli = contenedor_desktop.locator("> .row").all()
                
                if not filas_peli:
                    continue

                for fila in filas_peli:
                    try:
                        # --- TÍTULO ---
                        titulo_elem = fila.locator(".col-4 a").first
                        if not titulo_elem.count(): continue
                        raw_titulo = titulo_elem.inner_text().strip()
                        titulo = raw_titulo 

                        # --- INTELIGENCIA TMDB ---
                        datos_tmdb = buscar_datos_tmdb(titulo)
                        
                        poster_final = datos_tmdb.get("poster")
                        nota_tmdb = datos_tmdb.get("nota")
                        try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                        except: anio_tmdb = None

                        # Fallback Poster (Web Renoir)
                        if not poster_final:
                            poster_elem = fila.locator(".col-1 img").first
                            if poster_elem.count():
                                poster_final = poster_elem.get_attribute("src")

                        # --- ESPECIAL? ---
                        es_especial = es_programacion_especial(nombre_cine, titulo, anio_tmdb)

                        # --- IDIOMA ---
                        textos_small = fila.locator(".col-4 small").all_inner_texts()
                        idioma = "Español" 
                        for texto in textos_small:
                            texto_low = texto.lower()
                            if "subtitulada" in texto_low:
                                idioma = "VOSE"
                                break
                            elif "castellano" in texto_low or "español" in texto_low:
                                idioma = "Español"

                        # --- SESIONES ---
                        bloques_hora = fila.locator(".col-7 .text-center").all()
                        
                        for bloque in bloques_hora:
                            boton = bloque.locator("a.btn-primary").first
                            if not boton.count(): continue
                            
                            hora_txt = boton.inner_text().strip()
                            link_compra = boton.get_attribute("href")
                            
                            match_h = re.search(r"(\d{2}:\d{2})", hora_txt)
                            if not match_h: continue
                            h, m = map(int, match_h.group(1).split(":"))
                            
                            fecha_final = fecha_target.replace(hour=h, minute=m, second=0, microsecond=0)
                            
                            # Sala
                            sala = nombre_cine
                            sala_elem = bloque.locator("span").first
                            if sala_elem.count() and "sala" in sala_elem.inner_text().lower():
                                num_sala = sala_elem.inner_text().lower().replace("sala", "").strip()
                                sala = f"{nombre_cine} (Sala {num_sala})"

                            # GUARDAR
                            existe = session.exec(select(Pase).where(
                                Pase.cine == nombre_cine,
                                Pase.pelicula == titulo,
                                Pase.fecha_hora == fecha_final,
                                Pase.idioma == idioma
                            )).first()
                            
                            if not existe:
                                nuevo = Pase(
                                    cine=nombre_cine,
                                    pelicula=titulo,
                                    fecha_hora=fecha_final,
                                    sala=sala,
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

                    except Exception as e:
                        continue
                
                session.commit()
                time.sleep(1)

        print(f"🏁 FIN {nombre_cine}. {nuevos_pases} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_renoir_retiro()