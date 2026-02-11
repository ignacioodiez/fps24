import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial # <--- EL CEREBRO

def scrapear_golem():
    nombre_cine = "Golem Madrid"
    base_url = "https://www.golem.es/golem/golem-madrid"
    print(f"🎹 Entrando en {nombre_cine} (Modo Relacional)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        nuevos_pases = 0
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Iteramos HOY + los próximos 6 días
        for i in range(7):
            fecha_iter = hoy + timedelta(days=i)
            
            # Construimos la URL
            if i == 0:
                url_dia = base_url
            else:
                str_fecha_url = fecha_iter.strftime("%Y%m%d")
                url_dia = f"{base_url}/{str_fecha_url}"

            print(f"   📅 Procesando día: {fecha_iter.strftime('%d/%m')} ({url_dia})")

            try:
                page.goto(url_dia, timeout=60000, wait_until="domcontentloaded")
                
                # Truco: Cada peli está en una tabla con background="#AEAEAE"
                bloques = page.locator('table[background="#AEAEAE"]').all()
                
                if not bloques: continue

                with Session(engine) as session:
                    for bloque in bloques:
                        try:
                            # 1. TÍTULO E IDIOMA
                            titulo_elem = bloque.locator(".txtNegXXL").first
                            if not titulo_elem.count(): continue
                            
                            raw_titulo = titulo_elem.inner_text().strip()
                            titulo_limpio = raw_titulo
                            idioma = "Español"

                            # Detectar idioma y limpiar título para el gestor
                            if "(V.O.S.E.)" in raw_titulo:
                                idioma = "VOSE"
                                titulo_limpio = raw_titulo.replace("(V.O.S.E.)", "").strip()
                            elif "(VOSE)" in raw_titulo:
                                idioma = "VOSE"
                                titulo_limpio = raw_titulo.replace("(VOSE)", "").strip()

                            # 2. INTELIGENCIA 1:N
                            pelicula_id, anio_peli = obtener_id_pelicula(titulo_limpio, session)

                            # 3. ESPECIAL? (Por año)
                            es_especial = determinar_si_es_especial(titulo_limpio, anio_peli)

                            # 4. HORARIOS
                            celdas_hora = bloque.locator(".CajaVentasSup").all()
                            
                            for celda in celdas_hora:
                                try:
                                    hora_txt = celda.inner_text().strip()
                                    if ":" not in hora_txt: continue
                                    
                                    # Link de compra
                                    link_elem = celda.locator("a").first
                                    link_compra = base_url # Fallback
                                    
                                    if link_elem.count():
                                        href = link_elem.get_attribute("href")
                                        if href:
                                            link_compra = f"https://www.golem.es{href}"

                                    # Fecha final
                                    h, m = map(int, hora_txt.split(":"))
                                    fecha_final = fecha_iter.replace(hour=h, minute=m, second=0, microsecond=0)
                                    
                                    # GUARDAR PASE
                                    existe = session.exec(select(Pase).where(
                                        Pase.cine == nombre_cine,
                                        Pase.pelicula_id == pelicula_id,
                                        Pase.fecha_hora == fecha_final
                                    )).first()

                                    if not existe:
                                        nuevo = Pase(
                                            cine=nombre_cine,
                                            pelicula_id=pelicula_id,
                                            fecha_hora=fecha_final,
                                            sala=nombre_cine,
                                            precio="Consultar",
                                            link_compra=link_compra,
                                            idioma=idioma,
                                            es_evento_especial=es_especial
                                        )
                                        session.add(nuevo)
                                        nuevos_pases += 1

                                except: continue
                        except: continue
                    
                    session.commit()

            except Exception as e:
                # print(f"   ❌ Error cargando URL del día: {e}")
                continue

        print(f"🏁 FIN GOLEM. {nuevos_pases} pases guardados.")
        browser.close()

if __name__ == "__main__":
    scrapear_golem()