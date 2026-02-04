import time
import re
from datetime import datetime, timedelta  # <--- AQUÍ FALTABA EL TIMEDELTA
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_cine_paz():
    nombre_cine = "Cine Paz"
    BASE_URL = "https://www.cinepazmadrid.es/es/cartelera"
    # Limitamos a 7 días para no llenar la base de datos con eventos de dentro de 3 meses
    MAX_DIAS_A_ESCANEAR = 7 

    print(f"🎹 Entrando en {nombre_cine}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 1. CARGA ÚNICA
            page.goto(BASE_URL, timeout=60000)
            
            nuevos_pases = 0
            fecha_actual = datetime.now()
            anio_actual = fecha_actual.year

            # 2. LOCALIZAR DÍAS DISPONIBLES
            # En el HTML: <div class="rotulo_dia ... data-num="0">Hoy</div>
            rotulos = page.locator(".rotulo_dia").all()
            
            # Limitamos la búsqueda a los primeros X días que aparezcan en la web
            rotulos_a_procesar = rotulos[:MAX_DIAS_A_ESCANEAR]

            with Session(engine) as session:
                for rotulo in rotulos_a_procesar:
                    # --- A. CALCULAR FECHA ---
                    texto_dia = rotulo.inner_text().strip().lower() # Ej: "hoy", "mañana", "sábado 07/02"
                    data_num = rotulo.get_attribute("data-num") # El ID para buscar su contenedor (ej: "0", "1")
                    
                    if not data_num: continue

                    fecha_target = None

                    if "hoy" in texto_dia:
                        fecha_target = fecha_actual
                    elif "mañana" in texto_dia:
                        fecha_target = fecha_actual + timedelta(days=1)
                    else:
                        # Parsear fechas tipo "Viernes 06/02"
                        match_fecha = re.search(r"(\d{1,2})/(\d{1,2})", texto_dia)
                        if match_fecha:
                            d, m = map(int, match_fecha.groups())
                            
                            # Lógica cambio de año (Si estamos en dic y la peli es en enero)
                            anio_peli = anio_actual
                            if m < fecha_actual.month and fecha_actual.month == 12:
                                anio_peli += 1
                            
                            fecha_target = datetime(anio_peli, m, d)
                    
                    if not fecha_target:
                        continue # Si no pudimos sacar la fecha, saltamos

                    print(f"   📅 Procesando ID {data_num} -> {fecha_target.strftime('%d/%m')}")

                    # --- B. BUSCAR EL CONTENEDOR DE PELIS ASOCIADO ---
                    # En el HTML: <div class="contenedor_cines clearfix cines-0">
                    contenedor = page.locator(f".contenedor_cines.cines-{data_num}")
                    
                    # Extraer pelis de ese contenedor
                    peliculas_html = contenedor.locator(".horarios").all()

                    for peli_div in peliculas_html:
                        try:
                            # 1. TÍTULO
                            titulo_elem = peli_div.locator(".peli .text-header-span a").first
                            if not titulo_elem.count(): continue
                            
                            raw_titulo = titulo_elem.inner_text().strip()
                            titulo = raw_titulo.upper() # Estandarizamos a mayúsculas

                            # 2. DETECCIÓN DE IDIOMA Y LIMPIEZA
                            idioma = "Español"
                            
                            # Miramos si tiene la etiqueta visual "VOSE" en el póster
                            etiqueta_vose = peli_div.locator(".etiqueta-vose").count() > 0
                            
                            # O si lo pone en el título
                            if etiqueta_vose or "VOSE" in titulo or "V.O.S.E" in titulo:
                                idioma = "VOSE"
                                titulo = titulo.replace("(VOSE)", "").replace("(V.O.S.E)", "").strip()

                            # 3. PÓSTER (Ojo: URL relativa en el HTML)
                            img_elem = peli_div.locator(".peli img").first
                            poster_local = None
                            if img_elem.count():
                                src_relativo = img_elem.get_attribute("src")
                                if src_relativo:
                                    # La web usa base href, pero por si acaso construimos la absoluta
                                    poster_local = f"https://www.cinepazmadrid.es/{src_relativo}"

                            # 4. INTELIGENCIA TMDB (Prioritaria)
                            datos_tmdb = buscar_datos_tmdb(titulo)
                            poster_final = datos_tmdb.get("poster", poster_local)
                            nota_tmdb = datos_tmdb.get("nota")
                            try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                            except: anio_tmdb = None

                            # 5. ESPECIAL?
                            es_especial = es_programacion_especial(nombre_cine, titulo, anio_tmdb)

                            # 6. SESIONES
                            botones = peli_div.locator(".horas .btn.metrica").all()
                            
                            for btn in botones:
                                hora_txt = btn.inner_text().strip() # Puede contener "VOSE22:00" pegado
                                link_compra = btn.get_attribute("href")
                                
                                # Extraer solo la hora con Regex
                                match_hora = re.search(r"(\d{2}:\d{2})", hora_txt)
                                if not match_hora: continue
                                h, m = map(int, match_hora.group(1).split(":"))
                                
                                # Fecha final completa
                                fecha_final = fecha_target.replace(hour=h, minute=m, second=0, microsecond=0)

                                # GUARDAR
                                existe = session.exec(select(Pase).where(
                                    Pase.cine == nombre_cine,
                                    Pase.pelicula == titulo,
                                    Pase.fecha_hora == fecha_final
                                )).first()

                                if not existe:
                                    nuevo = Pase(
                                        cine=nombre_cine,
                                        pelicula=titulo,
                                        fecha_hora=fecha_final,
                                        sala="Cine Paz",
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

                        except Exception as e:
                            continue
                    
                    # Guardamos tras procesar cada día
                    session.commit()

            print(f"🏁 FIN {nombre_cine}. {nuevos_pases} pases guardados.")
        
        except Exception as e:
            print(f"❌ Error crítico en Cine Paz: {e}")
        
        browser.close()

if __name__ == "__main__":
    scrapear_cine_paz()