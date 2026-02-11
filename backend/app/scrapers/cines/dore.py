import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select

from app.database.engine import engine
from app.database.models import Pase
from app.services.gestor_peliculas import obtener_id_pelicula, determinar_si_es_especial # <--- EL CEREBRO

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def parsear_fecha_texto(texto_completo):
    """
    Busca patrones tipo: "17 de Enero a las 19:00"
    """
    try:
        texto = " ".join(texto_completo.split())
        patron = r"(\d{1,2})\s+de\s+([A-Za-z]+).*?(\d{2}:\d{2})"
        match = re.search(patron, texto, re.IGNORECASE)
        
        if not match: return None

        dia, mes_txt, hora_txt = match.groups()
        mes = MESES.get(mes_txt.lower())
        if not mes: return None
        
        hoy = datetime.now()
        anio = hoy.year
        if hoy.month == 12 and mes == 1: anio += 1
            
        horas, minutos = map(int, hora_txt.split(":"))
        return datetime(anio, mes, int(dia), horas, minutos)

    except Exception as e:
        return None

def scrapear_dore():
    with sync_playwright() as p:
        # headless=True para que no moleste
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        url = "https://entradasfilmoteca.sacatuentrada.es/"
        print(f"🍿 Entrando al Doré (Modo Relacional)...")
        
        try:
            page.goto(url, timeout=60000)
            page.wait_for_selector(".titulo", timeout=10000)
        except:
            print("❌ Error cargando Doré.")
            browser.close()
            return

        bloques_info = page.query_selector_all("div.info")
        print(f"   🔎 Analizando {len(bloques_info)} pases...")

        nuevos_pases = 0

        with Session(engine) as session:
            for info in bloques_info:
                try:
                    # 1. TÍTULO
                    titulo_elem = info.query_selector("h2.titulo")
                    if not titulo_elem: continue
                    titulo_raw = titulo_elem.inner_text().strip()

                    # 2. INTELIGENCIA 1:N
                    pelicula_id, anio_peli = obtener_id_pelicula(titulo_raw, session)

                    # 3. LÓGICA DE EVENTO ESPECIAL
                    # El Doré es casi todo ciclo/clásico. 
                    # Si tiene año y es antiguo (<2023), es especial.
                    es_especial= determinar_si_es_especial(titulo_raw, anio_peli)

                    # 4. FECHA
                    desc_elem = info.query_selector("div.descripcion")
                    texto_fecha = desc_elem.inner_text()
                    fecha_hora = parsear_fecha_texto(texto_fecha)
                    if not fecha_hora: continue

                    # 5. LINK
                    padre = info.evaluate_handle("el => el.parentElement")
                    link_elem = padre.query_selector(".enlaces a")
                    link_relativo = link_elem.get_attribute("href") if link_elem else ""
                    link_compra = link_relativo
                    if link_relativo and not link_relativo.startswith("http"):
                         link_compra = f"https://entradasfilmoteca.sacatuentrada.es{link_relativo}"

                    # 6. GUARDAR PASE
                    existe = session.exec(select(Pase).where(
                        Pase.cine == "Cine Doré",
                        Pase.pelicula_id == pelicula_id,
                        Pase.fecha_hora == fecha_hora
                    )).first()
                    
                    if not existe:
                        nuevo_pase = Pase(
                            cine="Cine Doré",
                            pelicula_id=pelicula_id,
                            fecha_hora=fecha_hora,
                            sala="Sala 1", # Default habitual
                            link_compra=link_compra,
                            precio="3.00€",
                            es_evento_especial=es_especial,
                            idioma="VOSE" # Filmoteca es VOSE por definición
                        )
                        session.add(nuevo_pase)
                        nuevos_pases += 1

                except Exception as e:
                    # print(f"⚠️ Error leyendo tarjeta: {e}")
                    continue
            
            session.commit()
            print(f"🏁 FIN DORÉ. {nuevos_pases} pases guardados.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_dore()