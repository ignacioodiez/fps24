import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase

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
        # 1. Limpieza básica
        texto = texto_fecha.strip().lower()
        
        # 2. Regex para sacar las partes
        # Busca: (texto mes): (texto dia)-(numero dia) ((hora):(minuto))
        match = re.search(r"([a-z]+):\s*[a-záéíóú\.]+-(\d+)\s*\((\d{2}:\d{2})\)", texto)
        
        if not match:
            return None
            
        nombre_mes = match.group(1)
        dia = int(match.group(2))
        hora_str = match.group(3)
        
        # 3. Convertir mes a número
        if nombre_mes not in MESES:
            return None
        mes = MESES[nombre_mes]
        
        # 4. Calcular año
        hoy = datetime.now()
        anio = hoy.year
        
        # Si estamos en Diciembre y leemos Enero, es el año que viene
        if hoy.month == 12 and mes == 1:
            anio += 1
        # Si estamos en Enero y leemos Diciembre (raro, pero por si acaso), es año pasado
        elif hoy.month == 1 and mes == 12:
            anio -= 1
            
        # 5. Juntar todo
        h, m = map(int, hora_str.split(":"))
        return datetime(anio, mes, dia, h, m)
        
    except Exception as e:
        print(f"      ⚠️ Error parseando fecha '{texto_fecha}': {e}")
        return None

def scrapear_cineteca():
    with sync_playwright() as p:
        print("🍿 Entrando en Cineteca Madrid...")
        # headless=True porque esta web es estática y fácil, no necesitamos verla
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        base_url = "https://www.cinetecamadrid.com"
        pagina_actual = 0
        nuevos_pases = 0
        
        with Session(engine) as session:
            while True:
                url = f"{base_url}/programacion?page={pagina_actual}"
                print(f"   📄 Leyendo página {pagina_actual}...")
                
                try:
                    page.goto(url, timeout=60000)
                except:
                    print("      ❌ Timeout cargando página. Paramos.")
                    break

                # Buscamos todas las tarjetas de películas
                # Según tu HTML: .node--type-activity
                tarjetas = page.locator(".node--type-activity").all()
                
                # Si no hay tarjetas, hemos llegado al final de la paginación
                if not tarjetas:
                    print("      ⛔ No hay más películas. Fin del recorrido.")
                    break
                
                print(f"      🔎 Encontradas {len(tarjetas)} fichas en esta página.")

                for tarjeta in tarjetas:
                    try:
                        # --- 1. TÍTULO ---
                        # h2.title > a
                        titulo_elem = tarjeta.locator("h2.title a").first
                        if not titulo_elem.count(): continue
                        titulo = titulo_elem.inner_text().strip()
                        
                        # --- 2. LINK DETALLE (Usaremos esto como link de compra por ahora) ---
                        link_relativo = titulo_elem.get_attribute("href")
                        link_compra = f"{base_url}{link_relativo}"
                        
                        # --- 3. IMAGEN ---
                        # .image-holder img
                        img_elem = tarjeta.locator(".image-holder img").first
                        poster_url = None
                        if img_elem.count():
                            src = img_elem.get_attribute("src")
                            if src:
                                if src.startswith("/"):
                                    poster_url = f"{base_url}{src}"
                                else:
                                    poster_url = src

                        # --- 4. FECHAS (Puede haber varias por tarjeta) ---
                        # .field--name-field-dias-de-proyeccion > div
                        # Tu HTML muestra que dentro de ese campo hay divs con el texto
                        bloque_fechas = tarjeta.locator(".field--name-field-dias-de-proyeccion").first
                        if not bloque_fechas.count():
                            continue # Peli sin fechas (quizás evento pasado)
                            
                        # A veces hay varios divs dentro con distintas fechas
                        # O a veces está todo el texto junto. Vamos a sacar el texto completo y buscar todas las coincidencias.
                        texto_fechas_completo = bloque_fechas.inner_text()
                        
                        # Truco: Dividimos por líneas o buscamos patrones
                        # En tu ejemplo: "Enero: Mié-28 (20:00)"
                        # Vamos a buscar todas las líneas que parezcan fechas
                        lineas = texto_fechas_completo.split('\n')
                        
                        for linea in lineas:
                            if not linea.strip(): continue
                            
                            fecha_final = parsear_fecha_cineteca(linea)
                            if not fecha_final: continue
                            
                            # GUARDAR EN BBDD
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
                                    sala="Cineteca", # Sala única o genérica por ahora
                                    precio="3.50€",  # Precio estándar Cineteca (o scrapearlo si está)
                                    link_compra=link_compra,
                                    poster_url=poster_url
                                )
                                session.add(nuevo)
                                nuevos_pases += 1
                                print(f"         ✅ {titulo[:20]}... -> {fecha_final.strftime('%d/%m %H:%M')}")

                    except Exception as e:
                        print(f"      ⚠️ Error procesando una tarjeta: {e}")

                # Pasamos a la siguiente página
                pagina_actual += 1
                session.commit() # Guardamos lo de esta página
                
                # Pequeña pausa para no saturar
                time.sleep(0.5)

            print(f"🏁 FIN. {nuevos_pases} pases nuevos de Cineteca.")
            
        browser.close()

if __name__ == "__main__":
    scrapear_cineteca()