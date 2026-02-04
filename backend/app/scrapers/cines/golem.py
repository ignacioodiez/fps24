import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

def scrapear_golem():
    nombre_cine = "Golem Madrid"
    base_url = "https://www.golem.es/golem/golem-madrid"
    print(f"🎹 Entrando en {nombre_cine}...")

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
                
                if not bloques:
                    # print(f"      ⚠️ No encontré películas para este día.")
                    continue

                with Session(engine) as session:
                    for bloque in bloques:
                        try:
                            # 1. TÍTULO
                            titulo_elem = bloque.locator(".txtNegXXL").first
                            if not titulo_elem.count(): continue
                            
                            raw_titulo = titulo_elem.inner_text().strip()
                            titulo = raw_titulo
                            idioma = "Español"

                            # Detectar idioma
                            if "(V.O.S.E.)" in raw_titulo:
                                idioma = "VOSE"
                                titulo = raw_titulo.replace("(V.O.S.E.)", "").strip()
                            elif "(VOSE)" in raw_titulo:
                                idioma = "VOSE"
                                titulo = raw_titulo.replace("(VOSE)", "").strip()

                            # 2. INTELIGENCIA TMDB
                            datos_tmdb = buscar_datos_tmdb(titulo)
                            
                            poster_final = datos_tmdb.get("poster")
                            nota_tmdb = datos_tmdb.get("nota")
                            try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                            except: anio_tmdb = None

                            # Fallback de póster (Web Golem)
                            if not poster_final:
                                img_elem = bloque.locator("img.bordeCartel").first
                                if img_elem.count():
                                    src = img_elem.get_attribute("src")
                                    if src:
                                        poster_final = f"https://www.golem.es{src}"

                            # 3. ESPECIAL?
                            es_especial = es_programacion_especial(nombre_cine, titulo, anio_tmdb)

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

            except Exception as e:
                print(f"   ❌ Error cargando URL del día: {e}")
                continue

        print(f"🏁 FIN GOLEM. {nuevos_pases} pases guardados.")
        browser.close()

if __name__ == "__main__":
    scrapear_golem()