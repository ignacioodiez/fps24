import re
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, expect
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula # <--- EL CEREBRO

# --- CONFIGURACIÓN ---
DIAS_A_ESCANEAR = 7 
# ---------------------

def scrapear_equis():
    with sync_playwright() as p:
        print(f"👻 Sala Equis: Escaneando {DIAS_A_ESCANEAR} días (Modo Relacional)...")
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        # 1. INFILTRACIÓN (Rutina estándar para saltar al iframe de venta)
        try:
            page.goto("https://salaequis.es/taquilla/", timeout=60000)
            link_entrada = page.locator(".buy.bigFont a").first
            if not link_entrada.count(): raise Exception("Sin links de entrada")
            page.goto(link_entrada.get_attribute("href"))
            
            link_k = page.locator("a[href*='kinetike.com']").first
            if not link_k.count(): raise Exception("Sin enlace a Kinetike")
            page.goto(link_k.get_attribute("href"))
            
            # Maniobra "Volver" para ver la cartelera completa
            page.on("dialog", lambda dialog: dialog.accept())
            if page.locator('input[name="ctl07"]').is_visible():
                page.locator('input[name="ctl07"]').click()
            
            page.wait_for_selector("#UpdatePanelFechas", timeout=15000)
            
        except Exception as e:
            print(f"❌ Error al entrar en Sala Equis: {e}")
            browser.close(); return

        # 2. BUCLE DÍA A DÍA
        pases_totales = 0
        
        lbl_fecha = page.locator("#lblContFecha")
        btn_siguiente = page.locator("#imgSiguiente")

        with Session(engine) as session:
            
            # Fecha inicial
            fecha_texto_inicial = lbl_fecha.inner_text().strip()
            try:
                fecha_actual = datetime.strptime(fecha_texto_inicial, "%d/%m/%Y")
            except:
                print(f"❌ Error fecha inicial: {fecha_texto_inicial}")
                browser.close(); return

            print(f"   📅 Inicio: {fecha_actual.strftime('%d/%m/%Y')}")

            for i in range(DIAS_A_ESCANEAR):
                fecha_str = fecha_actual.strftime("%d/%m/%Y")

                # --- A. SCRAPEO DEL DÍA ---
                time.sleep(0.5) 
                
                tarjetas = page.locator(".panel_peli").all()
                
                if tarjetas:
                    for tarjeta in tarjetas:
                        try:
                            # TÍTULO
                            titulo_raw = tarjeta.locator(".info_negrita").first.inner_text().strip()
                            
                            # INTELIGENCIA 1:N
                            # Equis suele poner títulos muy limpios, pero el gestor se encarga
                            pelicula_id, anio_peli = obtener_id_pelicula(titulo_raw, session)

                            # ESPECIAL? (Por año)
                            es_especial = False
                            if anio_peli and anio_peli < 2023:
                                es_especial = True

                            # SESIONES
                            links = tarjeta.locator("a").all()
                            for link in links:
                                hora_txt = link.inner_text().strip()
                                raw_link = link.get_attribute("href")
                                
                                match_h = re.search(r"(\d{2}:\d{2})", hora_txt)
                                if not match_h: continue
                                h, m = map(int, match_h.group(1).split(":"))
                                
                                fecha_final = fecha_actual.replace(hour=h, minute=m, second=0, microsecond=0)
                                
                                # Limpiar link de Kinetike
                                final_link = raw_link
                                if "javascript" in raw_link and "numEntradas.aspx" in raw_link:
                                    match_url = re.search(r'"(numEntradas\.aspx.*?)"', raw_link)
                                    if match_url: final_link = f"https://kinetike.com:83/views/{match_url.group(1)}"
                                elif final_link and not final_link.startswith("http"):
                                    final_link = f"https://kinetike.com:83/views/{final_link}"

                                # GUARDAR PASE
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == "Sala Equis",
                                    Pase.pelicula_id == pelicula_id,
                                    Pase.fecha_hora == fecha_final
                                )).first()
                                
                                if not existe:
                                    nuevo = Pase(
                                        cine="Sala Equis",
                                        pelicula_id=pelicula_id,
                                        fecha_hora=fecha_final,
                                        sala="Sala Equis",
                                        precio="6.90€",
                                        link_compra=final_link,
                                        idioma="VOSE", # Sala Equis casi siempre es VOSE
                                        es_evento_especial=es_especial
                                    )
                                    session.add(nuevo)
                                    pases_totales += 1
                        except: pass
                    
                    session.commit()

                # --- B. AVANZAR AL DÍA SIGUIENTE ---
                fecha_siguiente = fecha_actual + timedelta(days=1)
                fecha_siguiente_str = fecha_siguiente.strftime("%d/%m/%Y")
                
                if not btn_siguiente.is_visible():
                    break

                btn_siguiente.click()

                try:
                    expect(lbl_fecha).to_have_text(fecha_siguiente_str, timeout=5000)
                    fecha_actual = fecha_siguiente
                except:
                    # print(f"⚠️ Calendario atascado en {fecha_str}")
                    break

            print(f"🏁 FIN SALA EQUIS. {pases_totales} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_equis()