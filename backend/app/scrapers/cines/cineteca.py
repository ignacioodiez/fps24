import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def scrapear_cineteca():
    with sync_playwright() as p:
        print("🍿 Entrando en Cineteca Madrid (Navegación Profunda + Fuerza Bruta)...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        base_url = "https://www.cinetecamadrid.com"
        url_listado = f"{base_url}/programacion"
        
        try:
            page.goto(url_listado, timeout=60000)
        except Exception as e:
            print(f"❌ Error cargando portada: {e}")
            browser.close()
            return

        enlaces_peliculas = []
        tarjetas = page.locator(".node--type-activity").all()
        print(f"   🔎 Encontradas {len(tarjetas)} tarjetas en portada.")
        
        for tarjeta in tarjetas:
            link_elem = tarjeta.locator("h2.title a").first
            if link_elem.count() > 0:
                href = link_elem.get_attribute("href")
                titulo = link_elem.inner_text().strip()
                full_url = f"{base_url}{href}"
                enlaces_peliculas.append({"titulo": titulo, "url": full_url})
        
        print(f"   📍 Recolectados {len(enlaces_peliculas)} enlaces.")

        nuevos_pases = 0
        
        with Session(engine) as session:
            for peli in enlaces_peliculas:
                try:
                    print(f"   👉 Analizando: {peli['titulo']}")
                    page.goto(peli['url'], timeout=60000)
                    
                    # Esperar carga mínima
                    try: page.wait_for_selector(".tit-ficha", timeout=5000)
                    except: pass
                    
                    titulo_raw = page.locator("h2.title").first.inner_text().strip()
                    
                    # --- EXTRACCIÓN DE AÑO (MEJORADA) ---
                    anio_peli = None
                    
                    # 1. Selector específico
                    anio_elem = page.locator(".field--name-field-ano-filmacion .field__item").first
                    if anio_elem.count() > 0:
                        try:
                            anio_peli = int(anio_elem.inner_text().strip())
                        except: pass
                    
                    # 2. Regex en la cabecera completa (si falla el 1)
                    if not anio_peli:
                        try:
                            texto_cabecera = page.locator(".tit-ficha").first.inner_text()
                            match = re.search(r'\b(19|20)\d{2}\b', texto_cabecera)
                            if match:
                                anio_peli = int(match.group(0))
                        except: pass

                    if anio_peli:
                        print(f"      🎬 Año: {anio_peli}")
                    else:
                        print("      ⚠️ Año no encontrado")

                    # Gestor Inteligente
                    pelicula_id, _ = obtener_id_pelicula(titulo_raw, session, anio_filtro=anio_peli)
                    
                    if not pelicula_id: continue

                    # Horarios
                    bloque_sesiones = page.locator(".sb-sessions__items").first
                    if not bloque_sesiones.count():
                        print("      ⚠️ Sin horarios.")
                        continue

                    elementos = bloque_sesiones.locator("> *").all()
                    
                    mes_actual = datetime.now().month
                    dia_actual = datetime.now().day
                    
                    for elem in elementos:
                        try:
                            # Usamos JS para sacar el tag name de forma segura
                            tag_name = elem.evaluate("el => el.tagName.toLowerCase()")
                            texto = elem.inner_text().strip()
                            
                            if tag_name == "h2": 
                                mes_txt = texto.lower()
                                if mes_txt in MESES:
                                    mes_actual = MESES[mes_txt]
                            
                            elif tag_name == "h4":
                                match_dia = re.search(r'\d+', texto)
                                if match_dia:
                                    dia_actual = int(match_dia.group())
                            
                            elif tag_name == "ul":
                                lis = elem.locator("li.sb-sessions__date-hours-hour").all()
                                sala = "Cineteca"
                                sala_elem = elem.locator("li.sb-sessions__date-hours-space").first
                                if sala_elem.count():
                                    sala = sala_elem.inner_text().strip()

                                for li_hora in lis:
                                    hora_txt = li_hora.inner_text().replace('h', '').strip()
                                    h, m = map(int, hora_txt.split(':'))
                                    
                                    anio_proyeccion = datetime.now().year
                                    hoy = datetime.now()
                                    if hoy.month == 12 and mes_actual == 1: anio_proyeccion += 1
                                    elif hoy.month == 1 and mes_actual == 12: anio_proyeccion -= 1

                                    fecha_final = datetime(anio_proyeccion, mes_actual, dia_actual, h, m)
                                    
                                    existe = session.exec(select(Pase).where(
                                        Pase.cine == "Cineteca",
                                        Pase.pelicula_id == pelicula_id,
                                        Pase.fecha_hora == fecha_final
                                    )).first()
                                    

                                    es_especial = determinar_si_es_especial(titulo_raw, anio_peli)
                                    if not existe:
                                        nuevo = Pase(
                                            cine="Cineteca",
                                            pelicula_id=pelicula_id,
                                            fecha_hora=fecha_final,
                                            sala=sala,
                                            precio="3.50€",
                                            link_compra=peli['url'],
                                            idioma="VOSE",
                                            es_evento_especial=es_especial
                                        )
                                        session.add(nuevo)
                                        nuevos_pases += 1
                        except: continue

                    session.commit()

                except Exception as e:
                    print(f"      ❌ Error ficha: {e}")
                    continue
            
            print(f"🏁 FIN CINETECA. {nuevos_pases} pases nuevos.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_cineteca()