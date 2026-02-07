import re
from sqlmodel import Session, select
from thefuzz import process, fuzz 
from app.database.models import Pelicula
from app.services.tmdb import buscar_datos_tmdb

# --- LISTA NEGRA ---
BASURA_TITULOS = [
    "MIERCOLES DE IMPRESCINDIBLES", "MIÉRCOLES DE IMPRESCINDIBLES",
    "CINE DE SIEMPRE", "LOS JUEVES DEL", "SESIÓN ESPECIAL",
    "PROYECCIÓN Y COLOQUIO", "PRESENTACIÓN Y COLOQUIO", "COLOQUIO",
    "REESTRENO 4K", "REESTRENO", "CLÁSICOS", "CICLO", "CUTRECON 15",
    "NUEVAS MIRADAS DE CINE ASIÁTICO", "FILMOTECA", "MARATÓN",
    "EVENTO", "PREESTRENO", "PRESENTACIÓN"
]

UMBRAL_FUZZY = 85 

def limpiar_titulo_avanzado(titulo_sucio: str) -> str:
    if not titulo_sucio: return ""
    titulo = titulo_sucio.upper()
    # 1. Regex: Quitar paréntesis y contenido (VOSE, años, etc)
    titulo = re.sub(r'\(.*?\)', '', titulo)
    # 2. Quitar basura
    for basura in BASURA_TITULOS:
        titulo = titulo.replace(basura, "")
    # 3. Limpieza final
    titulo = titulo.replace(":", "").replace("-", "").strip()
    titulo = " ".join(titulo.split())
    return titulo

def obtener_id_pelicula(titulo_raw: str, session: Session):
    """
    Devuelve SIEMPRE una tupla (id, anio). Nunca falla.
    """
    try:
        # --- 0. LIMPIEZA ---
        titulo_limpio = limpiar_titulo_avanzado(titulo_raw)
        if not titulo_limpio or len(titulo_limpio) < 2:
            titulo_limpio = titulo_raw.strip().upper()

        print(f"   🔎 Procesando: '{titulo_raw}' -> '{titulo_limpio}'")
        
        # --- 1. BÚSQUEDA EXACTA ---
        peli_exacta = session.exec(select(Pelicula).where(Pelicula.titulo == titulo_limpio)).first()
        if peli_exacta:
            return peli_exacta.id, peli_exacta.anio

        # --- 2. FUZZY MATCH ---
        todas_las_pelis = session.exec(select(Pelicula)).all()
        if todas_las_pelis:
            mapa_pelis = {p.titulo: p for p in todas_las_pelis}
            lista_titulos = list(mapa_pelis.keys())
            match, score = process.extractOne(titulo_limpio, lista_titulos, scorer=fuzz.token_sort_ratio)
            
            if score >= UMBRAL_FUZZY:
                print(f"      🧠 Fuzzy Match: '{titulo_limpio}' == '{match}' ({score}%)")
                peli_encontrada = mapa_pelis[match]
                return peli_encontrada.id, peli_encontrada.anio

        # --- 3. TMDB (Aquí fallaba antes) ---
        print(f"      ✨ Nueva película (llamando a TMDB)...")
        datos_tmdb = buscar_datos_tmdb(titulo_limpio)

        # Si TMDB devuelve None (por error o no encontrado), creamos placeholder
        if not datos_tmdb:
            print(f"      ⚠️ Fallo en TMDB. Creando placeholder local.")
            nueva_peli = Pelicula(titulo=titulo_limpio, sinopsis="No encontrada en TMDB")
            session.add(nueva_peli)
            session.commit()
            session.refresh(nueva_peli)
            return nueva_peli.id, None

        # Doble check de ID
        peli_doble_check = session.exec(
            select(Pelicula).where(Pelicula.tmdb_id == datos_tmdb.get("tmdb_id"))
        ).first()

        if peli_doble_check:
            print(f"      🔄 Ya existía con otro nombre: '{peli_doble_check.titulo}'")
            return peli_doble_check.id, peli_doble_check.anio

        # Guardar nueva
        nueva_peli = Pelicula(
            titulo=titulo_limpio,
            titulo_original=datos_tmdb.get("titulo_original"),
            tmdb_id=datos_tmdb.get("tmdb_id"),
            poster_url=datos_tmdb.get("poster"),
            sinopsis=datos_tmdb.get("sinopsis"),
            nota_tmdb=datos_tmdb.get("nota"),
            anio=datos_tmdb.get("anio"),
            generos=datos_tmdb.get("generos"),
            backdrop_url=datos_tmdb.get("backdrop"),
            duracion=datos_tmdb.get("duracion")
        )
        session.add(nueva_peli)
        session.commit()
        session.refresh(nueva_peli)
        
        return nueva_peli.id, nueva_peli.anio

    except Exception as e:
        print(f"      ❌ ERROR CRÍTICO EN GESTOR: {e}")
        # En caso de catástrofe nuclear, devolvemos un ID nulo para que el scraper no explote
        return None, None