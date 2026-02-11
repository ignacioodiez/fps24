import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
# 👇 IMPORTAMOS LAS HERRAMIENTAS MAESTRAS
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial

# Mapeo de meses de SensaCine
MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12
}

class PalacioPrensaScraper:
    def __init__(self):
        self.cine_nombre = "Palacio de la Prensa"
        self.url = "https://www.sensacine.com/cines/cine/E0559/"

    def parse_fecha(self, dia_txt, mes_txt):
        try:
            dia = int(dia_txt)
            mes = MESES.get(mes_txt.lower(), 1)
            anio = datetime.now().year
            
            # Si estamos en diciembre y leemos "enero", es año siguiente
            if datetime.now().month == 12 and mes == 1:
                anio += 1
            
            return datetime(anio, mes, dia)
        except:
            return None

    def get_sessions(self):
        """
        Devuelve lista de diccionarios con datos crudos.
        """
        datos_crudos = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            print(f"🎬 Entrando en SensaCine ({self.cine_nombre})...")
            
            try:
                page.goto(self.url, timeout=60000, wait_until="domcontentloaded")

                # Cookies
                try:
                    boton_cookie = page.locator("#didomi-notice-agree-button")
                    if boton_cookie.is_visible(timeout=3000):
                        boton_cookie.click()
                        time.sleep(1)
                except: pass

                # Días del calendario
                dias_disponibles = page.locator(".calendar-date-link:not(.disabled)").all()
                print(f"   📅 Días detectados: {len(dias_disponibles)}")

                # Limitamos a 7 días
                for i, dia_btn in enumerate(dias_disponibles[:7]):
                    try:
                        dia_num = dia_btn.locator(".num").inner_text()
                        mes_txt = dia_btn.locator(".month").inner_text()
                        fecha_base = self.parse_fecha(dia_num, mes_txt)
                        
                        if not fecha_base: continue

                        # Clicar si no es el activo
                        if "current" not in dia_btn.get_attribute("class"):
                            dia_btn.click(force=True)
                            time.sleep(1.5)

                        # Leer películas
                        movie_cards = page.locator(".movie-card-theater").all()
                        
                        for card in movie_cards:
                            titulo_raw = card.locator(".meta-title-link").inner_text().strip()
                            
                            versiones = card.locator(".showtimes-version").all()
                            for version in versiones:
                                tipo_texto = version.locator(".text").inner_text().upper()
                                es_vose = "V.O.S.E." in tipo_texto
                                idioma = "VOSE" if es_vose else "Español"
                                
                                botones_hora = version.locator(".showtimes-hour-item-value").all()
                                for btn_hora in botones_hora:
                                    hora_str = btn_hora.inner_text().strip()
                                    h, m = map(int, hora_str.split(":"))
                                    fecha_fin = fecha_base.replace(hour=h, minute=m)
                                    
                                    # Link compra (padre del botón)
                                    padre = btn_hora.locator("xpath=..")
                                    href = padre.get_attribute("href")
                                    link_compra = f"https://www.sensacine.com{href}" if href else self.url

                                    datos_crudos.append({
                                        "titulo": titulo_raw,
                                        "fecha_hora": fecha_fin,
                                        "link": link_compra,
                                        "idioma": idioma,
                                        "cine": self.cine_nombre
                                    })

                    except Exception as e:
                        # print(f"Error día {i}: {e}")
                        continue

            except Exception as e:
                print(f"❌ Error general SensaCine: {e}")
            
            browser.close()

        return datos_crudos

# --- FUNCIÓN PRINCIPAL ACTUALIZADA ---
def scrapear_palacio_prensa():
    print("🍿 Ejecutando Scraper Palacio de la Prensa (Modo Gestor Inteligente)...")
    scraper = PalacioPrensaScraper()
    datos_pases = scraper.get_sessions()
    
    if not datos_pases:
        print("📭 No se han encontrado pases.")
        return

    print(f"💾 Procesando {len(datos_pases)} pases...")
    
    with Session(engine) as session:
        nuevos_pases = 0
        
        for dato in datos_pases:
            try:
                # 1. Obtener ID y Año con el Gestor (TMDB)
                pelicula_id, anio_peli = obtener_id_pelicula(dato["titulo"], session)
                
                if not pelicula_id:
                    print(f"   ⚠️ Saltando: {dato['titulo']}")
                    continue

                # 2. Detectar si es Especial (Centralizado)
                es_especial = determinar_si_es_especial(dato["titulo"], anio_peli)

                # 3. Comprobar duplicados
                existe = session.exec(select(Pase).where(
                    Pase.cine == dato["cine"],
                    Pase.pelicula_id == pelicula_id,
                    Pase.fecha_hora == dato["fecha_hora"]
                )).first()

                if not existe:
                    nuevo = Pase(
                        cine=dato["cine"],
                        pelicula_id=pelicula_id,
                        fecha_hora=dato["fecha_hora"],
                        sala="Palacio de la Prensa",
                        precio="Consultar",
                        link_compra=dato["link"],
                        idioma=dato["idioma"],
                        es_evento_especial=es_especial # ✅ Lógica centralizada
                    )
                    session.add(nuevo)
                    nuevos_pases += 1
            
            except Exception as e:
                print(f"   ❌ Error procesando pase: {e}")
                continue
        
        session.commit()
        print(f"🏁 FIN PALACIO PRENSA. {nuevos_pases} pases nuevos.")

if __name__ == "__main__":
    scrapear_palacio_prensa()