import os
import requests
import random  # <--- 1. IMPORTANTE: Importamos el módulo de aleatoriedad
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

def buscar_datos_tmdb(titulo: str, anio: int = None, es_evento_especial: bool = False):
    """
    1. Busca la película por título.
    2. Pide DETALLES + VÍDEOS + IMÁGENES.
    3. Selecciona 4 imágenes ALEATORIAS para la galería.
    """
    if not TMDB_API_KEY:
        return None

    # PASO 1: BUSCAR ID 🔎
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": titulo,
        "language": "es-ES",
        "region": "ES"
    }

    if anio:
        params["year"] = anio

    try:
        res = requests.get(search_url, params=params, timeout=5)
        res.raise_for_status()
        results = res.json().get("results", [])

        if not results:
            return None

        # Priorizar recientes (2024-2026)
        mejor_opcion = results[0]
        if not anio and not es_evento_especial:
            for peli in results:
                fecha = peli.get("release_date", "")
                # Priorizamos estrenos recientes solo si es una búsqueda estándar
                if fecha and ("2024" in fecha or "2025" in fecha or "2026" in fecha):
                    mejor_opcion = peli
                    break
        
        movie_id = mejor_opcion.get("id")

        # PASO 2: PEDIR TODO DE GOLPE 🚀
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        details_params = {
            "api_key": TMDB_API_KEY, 
            "language": "es-ES",
            "append_to_response": "videos,images",
            "include_image_language": "es,null" # Priorizamos sin texto o español
        }
        
        detalles = requests.get(details_url, params=details_params, timeout=5).json()

        # --- A. PROCESAR IMÁGENES PRINCIPALES ---
        poster_path = detalles.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        
        backdrop_path = detalles.get("backdrop_path")
        backdrop_url = f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else None
        
        # --- B. PROCESAR GALERÍA (MODO ALEATORIO 🎲) ---
        backdrops_raw = detalles.get("images", {}).get("backdrops", [])
        galeria = []

        # Truco Pro: Quitamos la primera imagen (index 0) de la lista de candidatos
        # porque esa es la que acabamos de usar como 'backdrop_url' (fondo principal).
        # Así no sale repetida en la galería.
        candidatos = backdrops_raw[1:] if len(backdrops_raw) > 1 else []

        # Si hay candidatos, elegimos hasta 4 al azar
        if candidatos:
            num_a_seleccionar = min(4, len(candidatos)) # Cogemos 4, o los que haya si son menos
            seleccionados = random.sample(candidatos, num_a_seleccionar) # <--- MAGIA ALEATORIA
            
            for img in seleccionados:
                path = img.get("file_path")
                if path:
                    galeria.append(f"https://image.tmdb.org/t/p/w780{path}")
        
        # --- C. PROCESAR TRÁILER ---
        videos_raw = detalles.get("videos", {}).get("results", [])
        youtube_id = None
        for video in videos_raw:
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                youtube_id = video.get("key")
                break 

        # --- D. OTROS DATOS ---
        fecha_str = detalles.get("release_date", "")
        anio = int(fecha_str.split("-")[0]) if fecha_str else None
        generos = ", ".join([g["name"] for g in detalles.get("genres", [])])

        return {
            "tmdb_id": movie_id,
            "titulo_tmdb": detalles.get("title"),
            "titulo_original": detalles.get("original_title"),
            "poster": poster_url,
            "backdrop": backdrop_url,    
            "imagenes_galeria": galeria, # <--- Lista aleatoria
            "youtube_id": youtube_id,
            "sinopsis": detalles.get("overview"),
            "nota": detalles.get("vote_average"),
            "duracion": detalles.get("runtime"),
            "anio": anio,
            "generos": generos
        }

    except Exception as e:
        print(f"      ⚠️ Error TMDB: {e}")
        return None