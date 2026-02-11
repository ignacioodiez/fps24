import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial

def scrapear_cine_estudio():
    nombre_cine = "Cine Estudio (CBA)"
    url_base = "https://www.circulobellasartes.com/ciclos-cine/"
    print(f"🎹 Entrando en {nombre_cine} (Modo Relacional)...")

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
            print(f"   🔎 Detectados {len(elementos)} eventos preliminares.")
            
            lista_para_visitar = []
            for el in elementos:
                try:
                    titulo_el = el.locator(".carousel-item-titulo a").first
                    if not titulo_el.count(): continue
                    
                    titulo = titulo_el.inner_text().strip()
                    link_ficha = titulo_el.get_attribute("href")
                    
                    if link_ficha:
                        lista_para_visitar.append({
                            "titulo": titulo,
                            "link": link_ficha
                        })
                except: continue

            # 3. NAVEGACIÓN PROFUNDA
            nuevos_pases = 0
            
            with Session(engine) as session:
                for item in lista_para_visitar:
                    try:
                        titulo_raw = item['titulo']
                        
                        # --- INTELIGENCIA 1:N ---
                        # Obtenemos ID y AÑO del gestor central
                        pelicula_id, anio_peli = obtener_id_pelicula(titulo_raw, session)
                        
                        # Lógica Evento Especial (Cine Estudio suele ser clásico, así que < 2023)
                        es_especial = determinar_si_es_especial(item["titulo"], anio_peli)

                        # Entramos a la ficha para ver horarios
                        page.goto(item['link'], timeout=45000, wait_until="domcontentloaded")
                        
                        # Link compra fallback
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

                                # GUARDAR PASE
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == nombre_cine,
                                    Pase.pelicula_id == pelicula_id, # Buscamos por ID
                                    Pase.fecha_hora == fecha_final
                                )).first()

                                if not existe:
                                    nuevo = Pase(
                                        cine=nombre_cine,
                                        pelicula_id=pelicula_id, # Enlace al padre
                                        fecha_hora=fecha_final,
                                        sala="Sala Cine Estudio",
                                        precio="5.50€",
                                        link_compra=link_compra,
                                        idioma="VOSE",
                                        es_evento_especial=es_especial
                                    )
                                    session.add(nuevo)
                                    nuevos_pases += 1

                    except Exception as e:
                        print(f"⚠️ Error procesando ficha '{item.get('titulo')}': {e}")
                        continue
            
                session.commit()
            print(f"🏁 FIN CINE ESTUDIO. {nuevos_pases} pases guardados.")

        except Exception as e:
            print(f"❌ Error general en Cine Estudio: {e}")
        
        browser.close()

if __name__ == "__main__":
    scrapear_cine_estudio()