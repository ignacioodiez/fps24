import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}

def parsear_fecha_texto(texto_completo):
    """
    Busca patrones tipo: "17 de Enero a las 19:00" dentro de un texto largo.
    """
    try:
        # 1. Limpiamos el texto (quitamos saltos de línea y espacios raros)
        texto = " ".join(texto_completo.split())
        
        # 2. Usamos Regex para buscar: Digitos + 'de' + Texto + 'a las' + Hora
        # Ejemplo: "17 de Enero a las 19:00"
        patron = r"(\d{1,2})\s+de\s+([A-Za-z]+).*?(\d{2}:\d{2})"
        match = re.search(patron, texto, re.IGNORECASE)
        
        if not match:
            return None

        dia, mes_txt, hora_txt = match.groups()
        
        # 3. Convertir a números
        mes = MESES.get(mes_txt.lower())
        if not mes: return None
        
        # Calcular año (si estamos en dic y peli es en enero -> año siguiente)
        hoy = datetime.now()
        anio = hoy.year
        if hoy.month == 12 and mes == 1:
            anio += 1
            
        horas, minutos = map(int, hora_txt.split(":"))
        
        return datetime(anio, mes, int(dia), horas, minutos)

    except Exception as e:
        print(f"⚠️ Error fecha: {e}")
        return None

def scrapear_dore():
    with sync_playwright() as p:
        # headless=True para que no moleste la ventana
        browser = p.chromium.launch(headless=True) 
        page = browser.new_page()
        
        url = "https://entradasfilmoteca.sacatuentrada.es/"
        print(f"🍿 Entrando al Doré ({url})...")
        page.goto(url)
        
        # Esperamos a que carguen los títulos (clase .titulo)
        try:
            page.wait_for_selector(".titulo", timeout=10000)
        except:
            print("❌ No se han cargado las películas. ¿Web caída?")
            browser.close()
            return

        # Estrategia: Buscamos todas las cajas de información (.info)
        # y desde ahí sacamos el resto de datos
        bloques_info = page.query_selector_all("div.info")
        print(f"🔎 Analizando {len(bloques_info)} posibles pases...")

        nuevos_pases = 0

        with Session(engine) as session:
            for info in bloques_info:
                try:
                    # 1. TÍTULO
                    titulo_elem = info.query_selector("h2.titulo")
                    if not titulo_elem: continue
                    titulo = titulo_elem.inner_text().strip()

                    # 2. FECHA
                    # Está dentro de div.descripcion mezclado con texto
                    desc_elem = info.query_selector("div.descripcion")
                    texto_fecha = desc_elem.inner_text()
                    fecha_hora = parsear_fecha_texto(texto_fecha)
                    
                    if not fecha_hora:
                        # Si no hay fecha, es un pase raro o abono, lo saltamos
                        continue

                    # 3. LINK e IMAGEN
                    # Truco ninja: Tenemos el div.info, pero el link y la foto están 
                    # en sus hermanos (div.enlaces y div.imagen).
                    # Subimos al padre para buscar desde allí.
                    padre = info.evaluate_handle("el => el.parentElement")
                    
                    # Link
                    link_elem = padre.query_selector(".enlaces a")
                    link_relativo = link_elem.get_attribute("href") if link_elem else ""
                    link_completo = link_relativo # A veces ya viene absoluto, si no, concatenamos
                    if link_relativo and not link_relativo.startswith("http"):
                         link_completo = f"https://entradasfilmoteca.sacatuentrada.es{link_relativo}"

                    # Foto (Opcional)
                    img_elem = padre.query_selector(".imagen img")
                    poster = img_elem.get_attribute("src") if img_elem else None

                    # 4. GUARDAR EN BBDD
                    # Chequeo anti-duplicados
                    existe = session.exec(select(Pase).where(
                        Pase.cine == "Cine Doré",
                        Pase.pelicula == titulo,
                        Pase.fecha_hora == fecha_hora
                    )).first()
                    
                    if existe:
                        continue # Ya lo tenemos

                    nuevo_pase = Pase(
                        cine="Cine Doré",
                        pelicula=titulo,
                        fecha_hora=fecha_hora,
                        sala="Sala 1", # Por defecto
                        link_compra=link_completo,
                        poster_url=poster,
                        precio="3.00€"
                    )
                    session.add(nuevo_pase)
                    nuevos_pases += 1
                    print(f"✅ {titulo[:20]}... -> {fecha_hora.strftime('%d/%m %H:%M')}")

                except Exception as e:
                    print(f"⚠️ Error leyendo tarjeta: {e}")
                    continue
            
            session.commit()
            print(f"🏁 TERMINADO. {nuevos_pases} pases nuevos en la base de datos.")
        
        browser.close()

if __name__ == "__main__":
    scrapear_dore()