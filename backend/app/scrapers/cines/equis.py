import re
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, expect
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase

# --- CONFIGURACIÓN ---
DIAS_A_ESCANEAR = 5  # Días a leer hacia el futuro
# ---------------------

def scrapear_equis():
    with sync_playwright() as p:
        print(f"👻 Modo fantasma. Escaneando {DIAS_A_ESCANEAR} días con lógica AJAX.")
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        # 1. INFILTRACIÓN (Rutina estándar)
        try:
            page.goto("https://salaequis.es/taquilla/", timeout=60000)
            link_entrada = page.locator(".buy.bigFont a").first
            if not link_entrada.count(): raise Exception("Sin links")
            page.goto(link_entrada.get_attribute("href"))
            
            link_k = page.locator("a[href*='kinetike.com']").first
            if not link_k.count(): raise Exception("Sin Kinetike")
            page.goto(link_k.get_attribute("href"))
            
            # Maniobra Volver
            page.on("dialog", lambda dialog: dialog.accept())
            page.locator('input[name="ctl07"]').click()
            
            # Esperamos a que aparezca el panel de fechas que me has pasado
            page.wait_for_selector("#UpdatePanelFechas", timeout=15000)
            print("✅ Hackeo completado. Panel de fechas localizado.")
            
        except Exception as e:
            print(f"❌ Error al entrar: {e}")
            browser.close(); return

        # 2. BUCLE DÍA A DÍA
        pases_totales = 0
        
        # Localizadores fijos basados en tu HTML
        lbl_fecha = page.locator("#lblContFecha")
        btn_siguiente = page.locator("#imgSiguiente")

        with Session(engine) as session:
            
            # Obtenemos la fecha inicial que marca la web
            fecha_texto_inicial = lbl_fecha.inner_text().strip()
            try:
                fecha_actual = datetime.strptime(fecha_texto_inicial, "%d/%m/%Y")
            except:
                print(f"❌ No entiendo la fecha inicial: {fecha_texto_inicial}")
                browser.close(); return

            print(f"📅 Fecha de inicio detectada: {fecha_actual.strftime('%d/%m/%Y')}")

            for i in range(DIAS_A_ESCANEAR):
                fecha_str = fecha_actual.strftime("%d/%m/%Y")
                print(f"\n👉 Procesando día: {fecha_str}")

                # --- A. SCRAPEO DEL DÍA ---
                # Esperamos un poco a que carguen los paneles de pelis
                # (Aunque el texto de la fecha cambie rápido, las pelis tardan un poco más)
                time.sleep(1) 
                
                tarjetas = page.locator(".panel_peli").all()
                if not tarjetas:
                    print("      (Sin sesiones hoy)")
                else:
                    for tarjeta in tarjetas:
                        try:
                            # TÍTULO
                            titulo = tarjeta.locator(".info_negrita").first.inner_text().strip()
                            
                            # SESIONES
                            links = tarjeta.locator("a").all()
                            for link in links:
                                hora_txt = link.inner_text().strip()
                                raw_link = link.get_attribute("href")
                                
                                match_h = re.search(r"(\d{2}:\d{2})", hora_txt)
                                if not match_h: continue
                                h, m = map(int, match_h.group(1).split(":"))
                                
                                # Componemos la fecha final
                                fecha_final = fecha_actual.replace(hour=h, minute=m, second=0, microsecond=0)
                                
                                # Limpiar link
                                final_link = raw_link
                                if "javascript" in raw_link and "numEntradas.aspx" in raw_link:
                                    match_url = re.search(r'"(numEntradas\.aspx.*?)"', raw_link)
                                    if match_url: final_link = f"https://kinetike.com:83/views/{match_url.group(1)}"
                                elif final_link and not final_link.startswith("http"):
                                    final_link = f"https://kinetike.com:83/views/{final_link}"

                                # Guardar
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == "Sala Equis",
                                    Pase.pelicula == titulo,
                                    Pase.fecha_hora == fecha_final
                                )).first()
                                
                                if not existe:
                                    nuevo = Pase(
                                        cine="Sala Equis",
                                        pelicula=titulo,
                                        fecha_hora=fecha_final,
                                        sala="Sala Equis",
                                        precio="6.90€",
                                        link_compra=final_link,
                                        poster_url="https://salaequis.es/wp-content/themes/salax/images/logo.svg"
                                    )
                                    session.add(nuevo)
                                    pases_totales += 1
                                    print(f"      ✅ {titulo[:20]}... -> {fecha_final.strftime('%H:%M')}")
                        except: pass
                    session.commit()

                # --- B. AVANZAR AL DÍA SIGUIENTE ---
                # Calculamos cuál DEBERÍA ser la siguiente fecha
                fecha_siguiente = fecha_actual + timedelta(days=1)
                fecha_siguiente_str = fecha_siguiente.strftime("%d/%m/%Y")
                
                if not btn_siguiente.is_visible():
                    print("⛔ Se acabó el calendario (no hay flecha).")
                    break

                # Click a la flecha
                # print(f"   ➡️ Avanzando a {fecha_siguiente_str}...")
                btn_siguiente.click()

                # --- LA CLAVE DEL ÉXITO ---
                # Esperamos hasta que el TEXTO del label cambie a la fecha que esperamos.
                try:
                    # Le damos 5 segundos para que el AJAX cambie el texto
                    expect(lbl_fecha).to_have_text(fecha_siguiente_str, timeout=5000)
                    # Si pasa aquí, es que ya ha cambiado -> actualizamos variable y seguimos
                    fecha_actual = fecha_siguiente
                except:
                    print(f"⚠️ El calendario no avanzó a {fecha_siguiente_str}. ¿Fin de mes o error?")
                    break

            print(f"🏁 FIN TOTAL. {pases_totales} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_equis()