import os
import requests
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

def buscar_datos_tmdb(titulo: str):
    """
    1. Busca la película por título.
    2. Si la encuentra, pide los DETALLES (para sacar duración y backdrop).
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

    try:
        res = requests.get(search_url, params=params, timeout=5)
        res.raise_for_status()
        results = res.json().get("results", [])

        if not results:
            return None

        # Lógica de mejor coincidencia (Priorizar recientes)
        mejor_opcion = results[0]
        for peli in results:
            fecha = peli.get("release_date", "")
            if fecha and ("2024" in fecha or "2025" in fecha or "2026" in fecha):
                mejor_opcion = peli
                break
        
        movie_id = mejor_opcion.get("id")

        # PASO 2: PEDIR DETALLES COMPLETOS (Runtime + Backdrop) 📝
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        details_params = {"api_key": TMDB_API_KEY, "language": "es-ES"}
        
        detalles = requests.get(details_url, params=details_params, timeout=5).json()

        # Procesar imágenes
        poster_path = detalles.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
        
        backdrop_path = detalles.get("backdrop_path")
        # Pedimos calidad original o w1280 para que se vea bien de fondo
        backdrop_url = f"https://image.tmdb.org/t/p/w1280{backdrop_path}" if backdrop_path else None
        
        fecha_str = detalles.get("release_date", "")
        anio = int(fecha_str.split("-")[0]) if fecha_str else None

        # Géneros (Ahora vienen como lista de objetos)
        generos = ", ".join([g["name"] for g in detalles.get("genres", [])])

        return {
            "tmdb_id": movie_id,
            "titulo_tmdb": detalles.get("title"),
            "titulo_original": detalles.get("original_title"),
            "poster": poster_url,
            "backdrop": backdrop_url,    # <--- NUEVO
            "sinopsis": detalles.get("overview"),
            "nota": detalles.get("vote_average"),
            "duracion": detalles.get("runtime"), # <--- NUEVO
            "anio": anio,
            "generos": generos
        }

    except Exception as e:
        print(f"      ⚠️ Error TMDB: {e}")
        return None