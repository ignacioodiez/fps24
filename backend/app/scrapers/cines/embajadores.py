import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_embajadores():
    url = "https://cinesembajadores.es/madrid/"
    print(f"🎹 Entrando en Cines Embajadores...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            try:
                page.locator("#cookies-eu-accept").click(timeout=3000)
            except: pass
            
            # Scroll para cargar imágenes
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error cargando web: {e}")
            browser.close()
            return

        nuevos_pases = 0
        peliculas = page.locator("ul.cartelera li.movie").all()
        print(f"   🔎 Encontradas {len(peliculas)} películas.")

        with Session(engine) as session:
            for peli_card in peliculas:
                try:
                    # 1. TÍTULO E IDIOMA
                    titulo_elem = peli_card.locator(".info h2 a").first
                    if not titulo_elem.count(): continue
                    raw_titulo = titulo_elem.inner_text().strip()
                    titulo = raw_titulo
                    idioma = "Español"

                    if "(VOSE)" in raw_titulo.upper():
                        idioma = "VOSE"
                        titulo = raw_titulo.replace("(VOSE)", "").replace("(DOBLADA AL ESPAÑOL)", "").strip()
                    elif "(DOBLADA" in raw_titulo.upper():
                        titulo = raw_titulo.split("(")[0].strip()

                    # 2. DATOS TMDB (Póster, Nota, Año)
                    datos_tmdb = buscar_datos_tmdb(titulo)
                    
                    poster_final = datos_tmdb.get("poster")
                    nota_tmdb = datos_tmdb.get("nota")
                    try:
                        anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                    except: anio_tmdb = None

                    # Fallback de póster si TMDB falla
                    if not poster_final:
                        img_elem = peli_card.locator(".poster img").first
                        if img_elem.count():
                            src = img_elem.get_attribute("srcset")
                            if src: poster_final = src.split(",")[-1].strip().split(" ")[0]
                            else: poster_final = img_elem.get_attribute("src")

                    # 3. CALCULAR SI ES ESPECIAL (Usando el Año)
                    es_especial = es_programacion_especial("Cine Embajadores", titulo, anio_tmdb)

                    # 4. HORARIOS
                    items_horarios = peli_card.locator(".showtimelist p[data-dia]").all()
                    
                    for item in items_horarios:
                        try:
                            dia_txt = item.get_attribute("data-dia")
                            hora_txt = item.get_attribute("data-hora")
                            recinto = item.get_attribute("data-recinto")
                            
                            link_elem = item.locator("a.compraTicket").first
                            link_compra = link_elem.get_attribute("href") if link_elem.count() else url

                            anio_actual = datetime.now().year
                            fecha_final = datetime.strptime(f"{dia_txt}/{anio_actual} {hora_txt}", "%d/%m/%Y %H:%M")
                            
                            if fecha_final.month < datetime.now().month and datetime.now().month == 12:
                                fecha_final = fecha_final.replace(year=anio_actual + 1)

                            nombre_cine_db = "Cine Embajadores Río" if "Río" in recinto or "Rio" in recinto else "Cine Embajadores"

                            # 5. GUARDAR (Sin chequear duplicados porque hemos borrado la DB)
                            nuevo = Pase(
                                cine=nombre_cine_db,
                                pelicula=titulo,
                                fecha_hora=fecha_final,
                                sala=nombre_cine_db,
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

                        except: continue

                except Exception as e:
                    print(f"   ⚠️ Error peli: {e}")
                    continue
            
            session.commit()
            print(f"🏁 FIN EMBAJADORES. {nuevos_pases} pases guardados.")
        browser.close()

if __name__ == "__main__":
    scrapear_embajadores()