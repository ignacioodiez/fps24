import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase

def scrapear_verdi():
    url = "https://www.ecartelera.com/cines/51,0,1.html"
    print(f"🎹 Entrando en Verdi (Vía eCartelera)...")

    with sync_playwright() as p:
        # Headless=False para ver cómo destruye cookies
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # --- 🍪 PROTOCOLO ANTI-COOKIES 🍪 ---
            try:
                # Buscamos el botón verde específico de tu HTML
                boton_cookie = page.locator("a.cmpboxbtnyes").first
                if boton_cookie.is_visible(timeout=4000):
                    print("   🍪 Destruyendo banner de cookies...")
                    boton_cookie.click(force=True)
                    time.sleep(1.5)
            except: pass
            # ------------------------------------

            print("   ⏳ Esperando listado de películas...")
            # Esperamos a que cargue cualquiera de los dos formatos
            try:
                page.wait_for_selector(".titem, article.article-cartelera", timeout=15000)
            except:
                print("❌ Timeout esperando elementos. ¿Bloqueo?")
                browser.close()
                return

            # Scroll para asegurar carga de imágenes
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error cargando la página: {e}")
            browser.close()
            return

        # --- SELECCIÓN HÍBRIDA ---
        # Pillamos TODO lo que parezca una peli (formato antiguo y nuevo)
        elementos = page.locator(".titem, article.article-cartelera").all()
        print(f"   🔎 Encontrados {len(elementos)} bloques de película.")
        
        nuevos_pases = 0

        with Session(engine) as session:
            for bloque in elementos:
                try:
                    # 1. TÍTULO
                    # Buscamos en ambos sitios posibles
                    titulo_elem = bloque.locator(".tinfo .tit a, h2 a").first
                    if not titulo_elem.count(): continue
                    
                    raw_titulo = titulo_elem.inner_text().strip()
                    titulo = raw_titulo.replace("(VOSE)", "").replace("VOSE", "").strip()

                    # 2. POSTER
                    img_elem = bloque.locator("img").first
                    poster_url = None
                    if img_elem.count():
                        src = img_elem.get_attribute("src")
                        data_src = img_elem.get_attribute("data-src")
                        poster_url = src if src and "placeholder" not in src else data_src
                        if poster_url and not poster_url.startswith("http"):
                            poster_url = f"https://www.ecartelera.com{poster_url}"

                    # 3. HORARIOS (LÓGICA UNIFICADA)
                    # Recopilamos todos los botones de hora, estén en pestañas o en lista simple
                    
                    # A. Caso Pestañas (Formato Article)
                    paneles = bloque.locator(".tab-content .tab-pane").all()
                    
                    # B. Caso Lista Simple (Formato Titem)
                    lista_simple = bloque.locator(".sessions li a, .sessions span[data-session-time]").all()
                    
                    # Recorremos todo lo que encontremos
                    items_a_procesar = []

                    if paneles:
                        # Si hay pestañas, entramos dentro para sacar el idioma correcto de cada fila
                        for panel in paneles:
                            filas = panel.locator(".row.pelicula").all()
                            for fila in filas:
                                # Idioma de la fila
                                txt_idioma = ""
                                span = fila.locator("span").first
                                if span.count(): txt_idioma = span.inner_text().upper()
                                idioma_fila = "VOSE" if "SUB" in txt_idioma or "VOSE" in txt_idioma else "Español"
                                
                                # Botones de esta fila
                                botones = fila.locator("a").all()
                                for btn in botones:
                                    items_a_procesar.append((btn, idioma_fila))
                    
                    elif lista_simple:
                        # Si es lista simple, asumimos idioma general o VOSE por defecto en Verdi
                        idioma_defecto = "VOSE"
                        # Buscamos pistas en el texto global
                        texto_info = bloque.locator(".tinfo").inner_text().upper()
                        if "ESPAÑOL" in texto_info or "ANIMACIÓN" in texto_info:
                            idioma_defecto = "Español"
                        
                        for btn in lista_simple:
                            items_a_procesar.append((btn, idioma_defecto))

                    # --- PROCESAR CADA PASE ENCONTRADO ---
                    for boton, idioma in items_a_procesar:
                        try:
                            # Sacamos datos
                            # A veces es un atributo 'title', a veces el texto interior
                            data_fecha = boton.get_attribute("title") # Formato ideal: "20260117 18:00"
                            link_compra = boton.get_attribute("href")
                            if not link_compra: link_compra = "https://madrid.cines-verdi.com/cartelera"

                            fecha_final = None
                            
                            # Intento 1: Por atributo title (YYYYMMDD HH:MM)
                            if data_fecha and data_fecha[0].isdigit():
                                fecha_final = datetime.strptime(data_fecha, "%Y%m%d %H:%M")
                            
                            # Intento 2: Si falla, asumimos que es HOY y cogemos la hora del texto
                            if not fecha_final:
                                hora_txt = boton.inner_text().strip()
                                match = re.search(r"(\d{2}:\d{2})", hora_txt)
                                if match:
                                    h, m = map(int, match.group(1).split(":"))
                                    fecha_final = datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)

                            if not fecha_final: continue

                            # --- INSERTAR EN BBDD ---
                            existe = session.exec(select(Pase).where(
                                Pase.cine == "Cines Verdi",
                                Pase.pelicula == titulo,
                                Pase.fecha_hora == fecha_final
                            )).first()
                            
                            if not existe:
                                nuevo = Pase(
                                    cine="Cines Verdi",
                                    pelicula=titulo,
                                    fecha_hora=fecha_final,
                                    sala="Cines Verdi",
                                    precio="8.00€",
                                    link_compra=link_compra,
                                    poster_url=poster_url,
                                    idioma=idioma
                                )
                                session.add(nuevo)
                                nuevos_pases += 1 # ¡AHORA SÍ SUMA!
                                print(f"      ✅ [{idioma}] {titulo[:15]}... -> {fecha_final.strftime('%d/%m %H:%M')}")
                        
                        except Exception as e:
                            # print(f"Error procesando botón: {e}")
                            pass

                except Exception as e:
                    print(f"   ⚠️ Error leyendo bloque: {e}")
                    pass

            session.commit()
            print(f"🏁 FIN VERDI. {nuevos_pases} pases guardados correctamente.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_verdi()