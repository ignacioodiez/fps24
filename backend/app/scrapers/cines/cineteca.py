import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula # <--- EL CEREBRO

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
        return None

def scrapear_cineteca():
    with sync_playwright() as p:
        print("🍿 Entrando en Cineteca Madrid (Modo Relacional)...")
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
                        titulo_raw = titulo_elem.inner_text().strip()
                        
                        # 2. INTELIGENCIA 1:N
                        pelicula_id, anio_peli = obtener_id_pelicula(titulo_raw, session)

                        # 3. Lógica Evento Especial
                        es_especial = False
                        if anio_peli and anio_peli < 2023:
                            es_especial = True
                        # Cineteca es especial per se, pero filtramos por antiguos o si no tiene año

                        # 4. LINK COMPRA
                        link_relativo = titulo_elem.get_attribute("href")
                        link_compra = f"{base_url}{link_relativo}"
                        
                        # 5. FECHAS
                        bloque_fechas = tarjeta.locator(".field--name-field-dias-de-proyeccion").first
                        if not bloque_fechas.count(): continue
                        
                        texto_fechas_completo = bloque_fechas.inner_text()
                        lineas = texto_fechas_completo.split('\n')
                        
                        for linea in lineas:
                            if not linea.strip(): continue
                            
                            fecha_final = parsear_fecha_cineteca(linea)
                            if not fecha_final: continue
                            
                            # GUARDAR PASE
                            existe = session.exec(select(Pase).where(
                                Pase.cine == "Cineteca",
                                Pase.pelicula_id == pelicula_id,
                                Pase.fecha_hora == fecha_final
                            )).first()
                            
                            if not existe:
                                nuevo = Pase(
                                    cine="Cineteca",
                                    pelicula_id=pelicula_id,
                                    fecha_hora=fecha_final,
                                    sala="Cineteca",
                                    precio="3.50€",
                                    link_compra=link_compra,
                                    idioma="VOSE", # Cineteca suele ser VOSE
                                    es_evento_especial=es_especial
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