import re
from sqlmodel import Session, select
from thefuzz import process, fuzz 
from app.database.models import Pelicula
from app.services.tmdb import buscar_datos_tmdb

# --- LISTA NEGRA (Eventos Especiales) ---
# Si un título tiene algo de esto, se considera Evento Especial
BASURA_TITULOS = [
    "MIERCOLES DE IMPRESCINDIBLES", "MIÉRCOLES DE IMPRESCINDIBLES",
    "CINE DE SIEMPRE", "LOS JUEVES DEL", "SESIÓN ESPECIAL",
    "PROYECCIÓN Y COLOQUIO", "PRESENTACIÓN Y COLOQUIO", "COLOQUIO",
    "REESTRENO 4K", "REESTRENO", "CLÁSICOS", "CICLO", "CUTRECON 15",
    "NUEVAS MIRADAS DE CINE ASIÁTICO", "FILMOTECA", "MARATÓN",
    "EVENTO", "PREESTRENO", "PRESENTACIÓN", "FILMOTECA", "JUEVES DE IMPRESCINDIBLES:",
    "ANIME DAY: ", "MIERCOLES CULTURAL", "[WILDER CINEMA]", "DOMINGO DE CLÁSICOS:", "UNIVERSO RAFAEL AZCONA:", "BERTOLUCCI:",

]

UMBRAL_FUZZY = 85 

# 👇 ESTA ES LA NUEVA FUNCIÓN MAESTRA 👇
def determinar_si_es_especial(titulo_raw: str, anio: int = None) -> bool:
    """
    Decide si un pase es especial basándose en:
    1. Palabras clave en el título (Ciclos, maratones...)
    2. Antigüedad de la película (Clásicos)
    """
    # 1. Chequeo por Título
    if titulo_raw:
        titulo_upper = titulo_raw.upper()
        for palabra in BASURA_TITULOS:
            if palabra in titulo_upper:
                return True

    # 2. Chequeo por Año (Si es anterior a 2023, lo consideramos 'Clásico' o 'Reposición')
    # Puedes ajustar este año a lo que tú consideres "viejo"
    if anio and anio < 2023:
        return True

    return False

def limpiar_titulo_avanzado(titulo_sucio: str) -> str:
    if not titulo_sucio: return ""
    titulo = titulo_sucio.upper()
    titulo = re.sub(r'\(.*?\)', '', titulo) # Quitar paréntesis
    for basura in BASURA_TITULOS:
        titulo = titulo.replace(basura, "") # Quitar basura
    titulo = titulo.replace(":", "").replace("-", "").strip()
    return " ".join(titulo.split())

def obtener_id_pelicula(titulo_raw: str, session: Session, anio_filtro: int = None):
    try:
        # Usamos la nueva función, pero aquí solo nos importa el título para saber si limpiamos o no
        # (El año lo usamos después en el scraper para marcar el pase)
        es_especial_por_titulo = determinar_si_es_especial(titulo_raw, anio=None)
        
        titulo_limpio = limpiar_titulo_avanzado(titulo_raw)
        if not titulo_limpio or len(titulo_limpio) < 2:
            titulo_limpio = titulo_raw.strip().upper()

        etiqueta = " [ESPECIAL]" if es_especial_por_titulo else ""
        print(f"   🔎 Procesando: '{titulo_raw}'{etiqueta} -> Buscando: '{titulo_limpio}'")
        
        # 1. BÚSQUEDA EXACTA
        peli_exacta = session.exec(select(Pelicula).where(Pelicula.titulo == titulo_limpio)).first()
        if peli_exacta: return peli_exacta.id, peli_exacta.anio
        
        peli_raw = session.exec(select(Pelicula).where(Pelicula.titulo == titulo_raw.strip())).first()
        if peli_raw: return peli_raw.id, peli_raw.anio

        # 2. FUZZY MATCH
        todas = session.exec(select(Pelicula)).all()
        if todas:
            mapa = {p.titulo: p for p in todas}
            match, score = process.extractOne(titulo_limpio, list(mapa.keys()), scorer=fuzz.token_sort_ratio) or (None, 0)
            if score >= UMBRAL_FUZZY:
                return mapa[match].id, mapa[match].anio

        # 3. TMDB
        print(f"      ✨ Nueva película (TMDB)...")
        # Pasamos el flag para que TMDB priorice clásicos si el título es especial
        datos_tmdb = buscar_datos_tmdb(titulo_limpio, anio=anio_filtro, es_evento_especial=es_especial_por_titulo)

        if not datos_tmdb:
            print(f"      ⚠️ Fallo TMDB. Guardando raw: '{titulo_raw}'")
            nueva = Pelicula(titulo=titulo_raw.strip(), sinopsis="No encontrada en TMDB")
            session.add(nueva)
            session.commit()
            session.refresh(nueva)
            return nueva.id, None

        duplicada = session.exec(select(Pelicula).where(Pelicula.tmdb_id == datos_tmdb.get("tmdb_id"))).first()
        if duplicada: return duplicada.id, duplicada.anio

        # 4. GUARDAR
        # Si es especial por título, guardamos el nombre RAW ("CICLO: ...")
        # Si no, guardamos el nombre limpio de TMDB
        titulo_final = titulo_raw.strip() if es_especial_por_titulo else datos_tmdb.get("titulo_tmdb")
        
        nueva_peli = Pelicula(
            titulo=titulo_final, 
            titulo_original=datos_tmdb.get("titulo_original"),
            tmdb_id=datos_tmdb.get("tmdb_id"),
            poster_url=datos_tmdb.get("poster"),
            sinopsis=datos_tmdb.get("sinopsis"),
            nota_tmdb=datos_tmdb.get("nota"),
            anio=datos_tmdb.get("anio"),
            generos=datos_tmdb.get("generos"),
            backdrop_url=datos_tmdb.get("backdrop"),
            duracion=datos_tmdb.get("duracion"),
            youtube_id=datos_tmdb.get("youtube_id"),
            imagenes_galeria=datos_tmdb.get("imagenes_galeria")
        )
        session.add(nueva_peli)
        session.commit()
        session.refresh(nueva_peli)
        
        return nueva_peli.id, nueva_peli.anio

    except Exception as e:
        print(f"      ❌ ERROR GESTOR: {e}")
        return None, None