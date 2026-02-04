import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_yelmo_ideal():
    nombre_cine = "Yelmo Cines Ideal"
    url = "https://www.yelmocines.es/cartelera/madrid"
    print(f"🎹 Entrando en {nombre_cine}...")

    with sync_playwright() as p:
        # ⚠️ Mantenemos headless=False y channel="chrome" para evitar bloqueos
        browser = p.chromium.launch(headless=False, channel="chrome")
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            
            # --- COOKIES ---
            try:
                page.locator("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll").click(timeout=5000)
            except: pass
            
            # --- EL CENTINELA ---
            print("   ⏳ Esperando a que Yelmo rellene las fechas...")
            page.wait_for_function(
                "document.querySelectorAll('#ddlDate option').length > 1", 
                timeout=20000
            )
            
            valores_fechas = page.evaluate("""
                () => {
                    const options = document.querySelectorAll('#ddlDate option');
                    return Array.from(options).map(o => o.value).filter(v => v != '0');
                }
            """)
            valores_fechas = valores_fechas[:7]
            print(f"   📅 Fechas detectadas: {len(valores_fechas)}")

        except Exception as e:
            print(f"   ❌ Error inicializando Yelmo: {e}")
            browser.close()
            return

        nuevos_pases = 0

        with Session(engine) as session:
            for valor_fecha in valores_fechas:
                print(f"   👉 Procesando: {valor_fecha}")
                
                try:
                    # 1. CAMBIAR LA FECHA
                    page.select_option("#ddlDate", value=valor_fecha, force=True)
                    try:
                        page.wait_for_selector("#preloadCartelera", state="visible", timeout=1000)
                        page.wait_for_selector("#preloadCartelera", state="hidden", timeout=10000)
                    except:
                        time.sleep(1.5)

                    # 2. SELECCIONAR EL CINE IDEAL
                    contenedor_ideal = page.locator('div[data-cinema="ideal"]')
                    if contenedor_ideal.count():
                        page.evaluate("document.querySelector('div[data-cinema=\"ideal\"]').style.display = 'block'")
                    else:
                        continue

                    # 3. EXTRAER PELÍCULAS
                    peliculas = contenedor_ideal.locator("article.now__movie").all()
                    
                    for peli in peliculas:
                        try:
                            # TÍTULO
                            titulo_elem = peli.locator("header h3 a").first
                            if not titulo_elem.count(): continue
                            raw_titulo = titulo_elem.inner_text().strip()
                            titulo = raw_titulo
                            
                            # --- INTELIGENCIA TMDB ---
                            datos_tmdb = buscar_datos_tmdb(titulo)
                            
                            poster_final = datos_tmdb.get("poster")
                            nota_tmdb = datos_tmdb.get("nota")
                            try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                            except: anio_tmdb = None

                            # Fallback Poster (Si TMDB falla, usamos el de Yelmo)
                            if not poster_final:
                                img_elem = peli.locator("figure img").first
                                if img_elem.count():
                                    poster_final = img_elem.get_attribute("src")

                            # ESPECIAL?
                            es_especial = es_programacion_especial(nombre_cine, titulo, anio_tmdb)

                            # 4. HORARIOS
                            bloques_formato = peli.locator(".horarioExp").all()
                            
                            for bloque in bloques_formato:
                                texto_formato = bloque.locator(".col3").inner_text().upper()
                                idioma = "Español"
                                titulo_db = titulo
                                
                                if "VOSE" in texto_formato or "SUBTITULADO" in texto_formato:
                                    idioma = "VOSE"
                                    titulo_db = titulo.replace("(VOSE)", "").strip()

                                botones = bloque.locator("time.btn a").all()
                                
                                for btn in botones:
                                    hora_txt = btn.inner_text().strip()
                                    link_compra = btn.get_attribute("href")
                                    if ":" not in hora_txt: continue
                                    
                                    # PARSEO FECHA
                                    anio_actual = datetime.now().year
                                    meses = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
                                    
                                    dia_str, mes_nombre = valor_fecha.split("-")
                                    mes = meses.get(mes_nombre.lower(), datetime.now().month)
                                    anio_pase = anio_actual
                                    
                                    # Ajuste si estamos en diciembre y el pase es en enero
                                    if mes < datetime.now().month and datetime.now().month == 12:
                                        anio_pase += 1
                                    
                                    h, m = map(int, hora_txt.split(":"))
                                    fecha_final = datetime(anio_pase, mes, int(dia_str), h, m)

                                    # GUARDAR
                                    existe = session.exec(select(Pase).where(
                                        Pase.cine == nombre_cine,
                                        Pase.pelicula == titulo_db,
                                        Pase.fecha_hora == fecha_final,
                                        Pase.idioma == idioma
                                    )).first()

                                    if not existe:
                                        nuevo = Pase(
                                            cine=nombre_cine,
                                            pelicula=titulo_db,
                                            fecha_hora=fecha_final,
                                            sala="Yelmo Ideal",
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
                    print(f"   ⚠️ Error procesando día {valor_fecha}: {e}")
                    continue
            
            session.commit()
            print(f"🏁 FIN YELMO IDEAL. {nuevos_pases} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_yelmo_ideal()