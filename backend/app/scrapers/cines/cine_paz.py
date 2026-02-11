import time
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial

def scrapear_cine_paz():
    nombre_cine = "Cine  MK2 Paz"
    BASE_URL = "https://www.cinepazmadrid.es/es/cartelera"
    MAX_DIAS_A_ESCANEAR = 7 

    print(f"🎹 Entrando en {nombre_cine} (Modo Relacional)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(BASE_URL, timeout=60000)
            
            nuevos_pases = 0
            fecha_actual = datetime.now()
            anio_actual = fecha_actual.year

            rotulos = page.locator(".rotulo_dia").all()
            rotulos_a_procesar = rotulos[:MAX_DIAS_A_ESCANEAR]

            with Session(engine) as session:
                for rotulo in rotulos_a_procesar:
                    # --- A. FECHAS (Igual que antes) ---
                    texto_dia = rotulo.inner_text().strip().lower()
                    data_num = rotulo.get_attribute("data-num")
                    if not data_num: continue

                    fecha_target = None
                    if "hoy" in texto_dia: fecha_target = fecha_actual
                    elif "mañana" in texto_dia: fecha_target = fecha_actual + timedelta(days=1)
                    else:
                        match_fecha = re.search(r"(\d{1,2})/(\d{1,2})", texto_dia)
                        if match_fecha:
                            d, m = map(int, match_fecha.groups())
                            anio_peli_fecha = anio_actual
                            if m < fecha_actual.month and fecha_actual.month == 12: anio_peli_fecha += 1
                            fecha_target = datetime(anio_peli_fecha, m, d)
                    
                    if not fecha_target: continue
                    print(f"   📅 Procesando ID {data_num} -> {fecha_target.strftime('%d/%m')}")

                    # --- B. PELÍCULAS ---
                    contenedor = page.locator(f".contenedor_cines.cines-{data_num}")
                    peliculas_html = contenedor.locator(".horarios").all()

                    for peli_div in peliculas_html:
                        try:
                            # 1. TÍTULO
                            titulo_elem = peli_div.locator(".peli .text-header-span a").first
                            if not titulo_elem.count(): continue
                            raw_titulo = titulo_elem.inner_text().strip().upper()

                            # 2. IDIOMA
                            idioma = "Español"
                            etiqueta_vose = peli_div.locator(".etiqueta-vose").count() > 0
                            if etiqueta_vose or "VOSE" in raw_titulo or "V.O.S.E" in raw_titulo:
                                idioma = "VOSE"
                                raw_titulo = raw_titulo.replace("(VOSE)", "").replace("(V.O.S.E)", "").strip()

                            # 3. OBTENER ID Y AÑO (¡NUEVO!) ✨
                            pelicula_id, anio_peli = obtener_id_pelicula(raw_titulo, session)

                            # 4. LÓGICA DE EVENTO ESPECIAL
                            # Si es anterior a 2023, asumimos que es reposición/clásico/especial
                            es_especial = determinar_si_es_especial(raw_titulo, anio_peli)
                            
                            # También si el propio cine lo marca (a veces ponen etiquetas)
                            if "EVENTO" in raw_titulo or "OPERA" in raw_titulo:
                                es_especial = True

                            # 5. GUARDAR SESIONES
                            botones = peli_div.locator(".horas .btn.metrica").all()
                            
                            for btn in botones:
                                hora_txt = btn.inner_text().strip()
                                link_compra = btn.get_attribute("href")
                                match_hora = re.search(r"(\d{2}:\d{2})", hora_txt)
                                if not match_hora: continue
                                h, m = map(int, match_hora.group(1).split(":"))
                                fecha_final = fecha_target.replace(hour=h, minute=m, second=0)

                                existe = session.exec(select(Pase).where(
                                    Pase.cine == nombre_cine,
                                    Pase.pelicula_id == pelicula_id,
                                    Pase.fecha_hora == fecha_final
                                )).first()

                                if not existe:
                                    nuevo_pase = Pase(
                                        cine=nombre_cine,
                                        pelicula_id=pelicula_id,
                                        fecha_hora=fecha_final,
                                        sala="Cine Paz",
                                        precio="Consultar",
                                        link_compra=link_compra,
                                        idioma=idioma,
                                        es_evento_especial=es_especial # <--- GUARDAMOS EL VALOR
                                    )
                                    session.add(nuevo_pase)
                                    nuevos_pases += 1

                        except Exception as e:
                            print(f"⚠️ Error procesando peli: {e}")
                            continue
                    
                    session.commit()

            print(f"🏁 FIN {nombre_cine}. {nuevos_pases} pases guardados.")
        
        except Exception as e:
            print(f"❌ Error crítico en Cine Paz: {e}")
        
        browser.close()

if __name__ == "__main__":
    scrapear_cine_paz()