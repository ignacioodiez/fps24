import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula # <--- EL CEREBRO

def scrapear_mk2_palacio_hielo():
    nombre_cine = "Mk2 Palacio de Hielo"
    url = "https://www.mk2palaciodehielo.es/es/cartelera"
    print(f"🎹 Entrando en {nombre_cine} (Modo Relacional)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # --- COOKIES ---
            try:
                page.get_by_text("ACEPTAR", exact=True).click(timeout=3000)
            except: pass

            # Scroll para cargar (aunque ya no necesitamos imágenes, ayuda a cargar horarios)
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
                        titulo_limpio = raw_titulo
                        idioma = "Español"

                        # Detección VOSE y limpieza básica para el gestor
                        if "(VOSE)" in raw_titulo.upper():
                            idioma = "VOSE"
                            titulo_limpio = raw_titulo.replace("(VOSE)", "").replace("(vose)", "").strip()
                        
                        # Doble chequeo de etiqueta visual
                        if bloque.locator(".etiqueta-vose").count() > 0:
                            idioma = "VOSE"

                        # 2. INTELIGENCIA 1:N
                        pelicula_id, anio_peli = obtener_id_pelicula(titulo_limpio, session)

                        # 3. ESPECIAL? (Por año)
                        es_especial = False
                        if anio_peli and anio_peli < 2023:
                            es_especial = True

                        # 4. HORARIOS
                        botones = bloque.locator(".horas a.btn").all()
                        
                        for btn in botones:
                            hora_txt = btn.inner_text().replace("VOSE", "").strip()
                            link_compra = btn.get_attribute("href")
                            
                            if ":" not in hora_txt: continue
                            
                            try:
                                h, m = map(int, hora_txt.split(":"))
                                fecha_final = dia_target.replace(hour=h, minute=m)
                                
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
            print(f"🏁 FIN {nombre_cine}. {nuevos_pases} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_mk2_palacio_hielo()