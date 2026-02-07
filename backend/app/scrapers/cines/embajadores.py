import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula # <--- EL CEREBRO

def scrapear_embajadores():
    url = "https://cinesembajadores.es/madrid/"
    print(f"🎹 Entrando en Cines Embajadores (Modo Relacional)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            try:
                page.locator("#cookies-eu-accept").click(timeout=3000)
            except: pass
            
            # Scroll para cargar todo
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
                    titulo_limpio = raw_titulo
                    idioma = "Español" # Por defecto

                    # Detectar idioma en el título antes de limpiar
                    if "(VOSE)" in raw_titulo.upper():
                        idioma = "VOSE"
                        titulo_limpio = raw_titulo.replace("(VOSE)", "").replace("(DOBLADA AL ESPAÑOL)", "").strip()
                    elif "(DOBLADA" in raw_titulo.upper():
                        titulo_limpio = raw_titulo.split("(")[0].strip()

                    # 2. INTELIGENCIA 1:N
                    # Usamos el título limpio para buscar el ID
                    pelicula_id, anio_peli = obtener_id_pelicula(titulo_limpio, session)

                    # 3. LÓGICA ESPECIAL (Por año)
                    es_especial = False
                    if anio_peli and anio_peli < 2023:
                        es_especial = True

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
                            
                            # Ajuste cambio de año
                            if fecha_final.month < datetime.now().month and datetime.now().month == 12:
                                fecha_final = fecha_final.replace(year=anio_actual + 1)

                            # Distinguir entre las dos sedes
                            nombre_cine_db = "Cine Embajadores Río" if "Río" in recinto or "Rio" in recinto else "Cine Embajadores"

                            # 5. GUARDAR PASE
                            existe = session.exec(select(Pase).where(
                                Pase.cine == nombre_cine_db,
                                Pase.pelicula_id == pelicula_id,
                                Pase.fecha_hora == fecha_final
                            )).first()

                            if not existe:
                                nuevo = Pase(
                                    cine=nombre_cine_db,
                                    pelicula_id=pelicula_id,
                                    fecha_hora=fecha_final,
                                    sala=nombre_cine_db, # Usamos el nombre del cine como sala genérica
                                    precio="Consultar",
                                    link_compra=link_compra,
                                    idioma=idioma,
                                    es_evento_especial=es_especial
                                )
                                session.add(nuevo)
                                nuevos_pases += 1

                        except: continue

                except Exception as e:
                    continue
            
            session.commit()
            print(f"🏁 FIN EMBAJADORES. {nuevos_pases} pases guardados.")
        browser.close()

if __name__ == "__main__":
    scrapear_embajadores()