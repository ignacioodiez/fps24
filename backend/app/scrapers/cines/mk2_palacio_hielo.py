import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_mk2_palacio_hielo():
    nombre_cine = "Mk2 Palacio de Hielo"
    url = "https://www.mk2palaciodehielo.es/es/cartelera"
    print(f"🎹 Entrando en {nombre_cine}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # --- COOKIES ---
            try:
                page.get_by_text("ACEPTAR", exact=True).click(timeout=3000)
            except: pass

            # Scroll para cargar imágenes
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error cargando {nombre_cine}: {e}")
            browser.close()
            return

        nuevos_pases = 0
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        with Session(engine) as session:
            # Iteramos los próximos 7 días
            for i in range(7):
                dia_target = hoy + timedelta(days=i)
                selector_dia = f".cines-{i}"
                
                # Si no existe el contenedor de ese día, saltamos
                if not page.locator(selector_dia).is_visible(): continue

                print(f"   📅 {nombre_cine}: Procesando día {dia_target.strftime('%d/%m')}")

                bloques_peli = page.locator(f"{selector_dia} .horarios").all()

                for bloque in bloques_peli:
                    try:
                        # 1. TÍTULO
                        titulo_elem = bloque.locator("p.gibsonT b").first
                        if not titulo_elem.count(): continue
                        
                        raw_titulo = titulo_elem.inner_text().strip()
                        titulo = raw_titulo
                        idioma = "Español"

                        # Detección VOSE
                        if "(VOSE)" in raw_titulo.upper():
                            idioma = "VOSE"
                            titulo = raw_titulo.replace("(VOSE)", "").replace("(vose)", "").strip()
                        if bloque.locator(".etiqueta-vose").count() > 0:
                            idioma = "VOSE"

                        # --- INTELIGENCIA TMDB ---
                        datos_tmdb = buscar_datos_tmdb(titulo)
                        
                        poster_final = datos_tmdb.get("poster")
                        nota_tmdb = datos_tmdb.get("nota")
                        try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                        except: anio_tmdb = None

                        # 2. PÓSTER FALLBACK (Si TMDB falla, usamos el de la web)
                        if not poster_final:
                            img_elem = bloque.locator("img.img-responsive").first
                            if img_elem.count():
                                src = img_elem.get_attribute("src")
                                if src:
                                    if not src.startswith("http"):
                                        poster_final = f"https://www.mk2palaciodehielo.es/{src.lstrip('/')}"
                                    else:
                                        poster_final = src

                        # 3. ESPECIAL?
                        es_especial = es_programacion_especial(nombre_cine, titulo, anio_tmdb)

                        # 4. HORARIOS
                        botones = bloque.locator(".horas a.btn").all()
                        
                        for btn in botones:
                            hora_txt = btn.inner_text().replace("VOSE", "").strip()
                            link_compra = btn.get_attribute("href")
                            
                            if ":" not in hora_txt: continue
                            
                            try:
                                h, m = map(int, hora_txt.split(":"))
                                fecha_final = dia_target.replace(hour=h, minute=m)
                                
                                # Guardar
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == nombre_cine,
                                    Pase.pelicula == titulo,
                                    Pase.fecha_hora == fecha_final,
                                    Pase.idioma == idioma
                                )).first()

                                if not existe:
                                    nuevo = Pase(
                                        cine=nombre_cine,
                                        pelicula=titulo,
                                        fecha_hora=fecha_final,
                                        sala=nombre_cine,
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

                    except: continue

            session.commit()
            print(f"🏁 FIN {nombre_cine}. {nuevos_pases} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_mk2_palacio_hielo()