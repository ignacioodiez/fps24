import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase
from app.utils import es_programacion_especial
from app.services.tmdb import buscar_datos_tmdb

# Diccionario para traducir meses de Cineteca a números
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def parsear_fecha_cineteca(texto_fecha):
    """
    Convierte: 'Enero: Mié-28 (20:00)' -> datetime object
    """
    try:
        texto = texto_fecha.strip().lower()
        match = re.search(r"([a-z]+):\s*[a-záéíóú\.]+-(\d+)\s*\((\d{2}:\d{2})\)", texto)
        
        if not match: return None
            
        nombre_mes = match.group(1)
        dia = int(match.group(2))
        hora_str = match.group(3)
        
        if nombre_mes not in MESES: return None
        mes = MESES[nombre_mes]
        
        hoy = datetime.now()
        anio = hoy.year
        
        if hoy.month == 12 and mes == 1: anio += 1
        elif hoy.month == 1 and mes == 12: anio -= 1
            
        h, m = map(int, hora_str.split(":"))
        return datetime(anio, mes, dia, h, m)
        
    except Exception as e:
        # print(f"      ⚠️ Error parseando fecha '{texto_fecha}': {e}")
        return None

def scrapear_cineteca():
    with sync_playwright() as p:
        print("🍿 Entrando en Cineteca Madrid...")
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        base_url = "https://www.cinetecamadrid.com"
        pagina_actual = 0
        nuevos_pases = 0
        
        with Session(engine) as session:
            while True:
                url = f"{base_url}/programacion?page={pagina_actual}"
                print(f"   📄 Leyendo página {pagina_actual}...")
                
                try: page.goto(url, timeout=60000)
                except: break

                tarjetas = page.locator(".node--type-activity").all()
                if not tarjetas: break
                
                print(f"      🔎 Encontradas {len(tarjetas)} fichas.")

                for tarjeta in tarjetas:
                    try:
                        # 1. TÍTULO
                        titulo_elem = tarjeta.locator("h2.title a").first
                        if not titulo_elem.count(): continue
                        titulo = titulo_elem.inner_text().strip()
                        
                        # 2. INTELIGENCIA TMDB
                        datos_tmdb = buscar_datos_tmdb(titulo)
                        
                        poster_final = datos_tmdb.get("poster")
                        nota_tmdb = datos_tmdb.get("nota")
                        try: anio_tmdb = int(datos_tmdb.get("anio")) if datos_tmdb.get("anio") else None
                        except: anio_tmdb = None

                        # Fallback de póster (Web Cineteca)
                        if not poster_final:
                            img_elem = tarjeta.locator(".image-holder img").first
                            if img_elem.count():
                                src = img_elem.get_attribute("src")
                                if src:
                                    poster_final = f"{base_url}{src}" if src.startswith("/") else src

                        # 3. LINK COMPRA
                        link_relativo = titulo_elem.get_attribute("href")
                        link_compra = f"{base_url}{link_relativo}"
                        
                        # 4. ESPECIAL? (Cineteca casi siempre lo es, pero el año confirma clásicos)
                        es_especial = es_programacion_especial("Cineteca", titulo, anio_tmdb)

                        # 5. FECHAS
                        bloque_fechas = tarjeta.locator(".field--name-field-dias-de-proyeccion").first
                        if not bloque_fechas.count(): continue
                        
                        texto_fechas_completo = bloque_fechas.inner_text()
                        lineas = texto_fechas_completo.split('\n')
                        
                        for linea in lineas:
                            if not linea.strip(): continue
                            
                            fecha_final = parsear_fecha_cineteca(linea)
                            if not fecha_final: continue
                            
                            # GUARDAR
                            existe = session.exec(select(Pase).where(
                                Pase.cine == "Cineteca",
                                Pase.pelicula == titulo,
                                Pase.fecha_hora == fecha_final
                            )).first()
                            
                            if not existe:
                                nuevo = Pase(
                                    cine="Cineteca",
                                    pelicula=titulo,
                                    fecha_hora=fecha_final,
                                    sala="Cineteca",
                                    precio="3.50€",
                                    link_compra=link_compra,
                                    poster_url=poster_final,
                                    idioma="VOSE", # Cineteca suele ser VOSE por defecto
                                    es_evento_especial=es_especial,
                                    nota_tmdb=nota_tmdb,
                                    anio=anio_tmdb
                                )
                                session.add(nuevo)
                                nuevos_pases += 1

                    except Exception as e:
                        continue

                pagina_actual += 1
                session.commit()
                time.sleep(0.5)

            print(f"🏁 FIN CINETECA. {nuevos_pases} pases nuevos.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_cineteca()