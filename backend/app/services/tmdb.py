import requests
import re
from functools import lru_cache # <--- ESTO ES LA MAGIA DE LA MEMORIA

# PEGA AQUÍ TU API KEY (Mantenla secreta si subes esto a GitHub)
TMDB_API_KEY = "095a097e556670b8c3822dd355f7b876"

def limpiar_titulo(titulo: str) -> str:
    """
    Limpia el título del cine para que TMDB lo entienda.
    Ej: "Matrix (VOSE)" -> "Matrix"
    Ej: "Avatar: El sentido del agua - 3D" -> "Avatar: El sentido del agua"
    """
    # 1. Quitar todo lo que esté entre paréntesis (VOSE), (2024), etc.
    titulo = re.sub(r"\(.*?\)", "", titulo)
    
    # 2. Quitar guiones raros del final si los hay (típico de algunos cines)
    if " - " in titulo:
         titulo = titulo.split(" - ")[0]
         
    return titulo.strip()

# --- LA FUNCIÓN CON MEMORIA ---
# maxsize=None significa que guardará TODAS las pelis que busque en esta ejecución.
@lru_cache(maxsize=None) 
def buscar_datos_tmdb(titulo_cine: str) -> dict:
    """
    Busca una película en TMDB y devuelve Poster, Nota, Sinopsis y Año.
    ¡Tiene memoria! Si le pides la misma peli dos veces, la segunda no gasta API.
    """
    print(f"      📡 Llamando a TMDB para: {titulo_cine}...") # Para que veas cuándo llama de verdad
    
    titulo_limpio = limpiar_titulo(titulo_cine)
    url = "https://api.themoviedb.org/3/search/movie"
    
    params = {
        "api_key": TMDB_API_KEY,
        "query": titulo_limpio,
        "language": "es-ES", # Queremos sinopsis y cartel en español
        "page": 1
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                # Cogemos el primer resultado, suele ser el correcto
                peli = data["results"][0]
                
                # Construimos la URL de la imagen (w500 es el tamaño, calidad media-alta)
                poster_path = peli.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None
                
                return {
                    "poster": poster_url,
                    "nota": peli.get("vote_average", 0),  # La nota (ej: 7.4)
                    "sinopsis": peli.get("overview", "Sin sinopsis disponible."),
                    "anio": peli.get("release_date", "")[:4] # Solo el año "2024"
                }
    except Exception as e:
        print(f"      ⚠️ Fallo conectando con TMDB: {e}")

    # Si falla o no encuentra nada, devolvemos un diccionario vacío o con None
    return {"poster": None, "nota": None, "sinopsis": None, "anio": None}