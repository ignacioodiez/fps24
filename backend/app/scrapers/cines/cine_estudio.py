import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_cine_estudio():
    nombre_cine = "Cine Estudio (CBA)"
    url_base = "https://www.circulobellasartes.com/ciclos-cine/"
    print(f"🎹 Entrando en {nombre_cine}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 1. CARGAR PORTADA
            page.goto(url_base, timeout=60000, wait_until="domcontentloaded")
            try: page.locator("button.cmplz-accept").click(timeout=3000)
            except: pass

            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # 2. RECOPILAR LINKS
            elementos = page.locator(".fl-post-grid-post").all()
            print(f"   🔎 Detectados {len(elementos)} eventos.")
            
            lista_para_visitar = []
            for el in elementos:
                try:
                    titulo_el = el.locator(".carousel-item-titulo a").first
                    if not titulo_el.count(): continue
                    
                    titulo = titulo_el.inner_text().strip()
                    link_ficha = titulo_el.get_attribute("href")
                    
                    # Imagen fallback (la de la web)
                    img_el = el.locator(".fl-post-image img").first
                    poster_web = img_el.get_attribute("src") if img_el.count() else None
                    
                    if link_ficha:
                        lista_para_visitar.append({
                            "titulo": titulo,
                            "link": link_ficha,
                            "poster_web": poster_web
                        })
                except: continue

            # 3. NAVEGACIÓN PROFUNDA
            nuevos_pases = 0
            
            with Session(engine) as session:
                for item in lista_para_visitar:
                    try:
                        titulo = item['titulo']
                        
                        # --- INTELIGENCIA TMDB ---
                        # Buscamos datos (Poster HD, Nota, Año)
                        datos_tmdb = buscar_datos_tmdb(titulo)
                        
                        poster_final = datos_tmdb.get("poster")
                        if not poster_final: # Si TMDB falla, usamos el de la web
                            poster_final = item['poster_web']
                            
                        nota_tmdb = datos_tmdb.get("nota")
                        try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                        except: anio_tmdb = None
                        
                        # Calculamos si es especial (CBA suele serlo siempre, pero añadimos lógica de año)
                        es_especial = es_programacion_especial(nombre_cine, titulo, anio_tmdb)


                        # Entramos a la ficha
                        page.goto(item['link'], timeout=45000, wait_until="domcontentloaded")
                        
                        # Link compra
                        link_compra = item['link']
                        boton_compra = page.locator("a.fl-button[href*='reservaentradas'], a.fl-button[href*='tickets']").first
                        if boton_compra.count():
                            link_compra = boton_compra.get_attribute("href")

                        # Tabla horarios
                        filas = page.locator("table.cba_tabla_sesiones tr").all()
                        if not filas: continue

                        for fila in filas:
                            celda_fecha = fila.locator("td").first
                            if not celda_fecha.count(): continue
                            
                            texto_fecha = celda_fecha.inner_text().strip()
                            match = re.search(r"(\d{1,2})/(\d{1,2}).*?(\d{1,2}):(\d{2})", texto_fecha)
                            
                            if match:
                                dia, mes, hora, minuto = map(int, match.groups())
                                now = datetime.now()
                                anio = now.year
                                if mes < now.month and now.month == 12: anio += 1
                                
                                fecha_final = datetime(anio, mes, dia, hora, minuto)
                                if fecha_final < now.replace(hour=0, minute=0, second=0): continue

                                # GUARDAR
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == nombre_cine,
                                    Pase.pelicula == titulo,
                                    Pase.fecha_hora == fecha_final
                                )).first()

                                if not existe:
                                    nuevo = Pase(
                                        cine=nombre_cine,
                                        pelicula=titulo,
                                        fecha_hora=fecha_final,
                                        sala="Sala Cine Estudio",
                                        precio="5.50€",
                                        link_compra=link_compra,
                                        poster_url=poster_final,
                                        idioma="VOSE",
                                        es_evento_especial=es_especial,
                                        nota_tmdb=nota_tmdb,
                                        anio=anio_tmdb
                                    )
                                    session.add(nuevo)
                                    nuevos_pases += 1

                    except Exception as e:
                        # print(f"⚠️ Error en ficha: {e}")
                        continue
            
                session.commit()
            print(f"🏁 FIN CINE ESTUDIO. {nuevos_pases} pases guardados.")

        except Exception as e:
            print(f"❌ Error general en Cine Estudio: {e}")
        
        browser.close()

if __name__ == "__main__":
    scrapear_cine_estudio()