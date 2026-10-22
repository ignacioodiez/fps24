import os
import random
import unicodedata

import requests
from dotenv import load_dotenv

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
API = "https://api.themoviedb.org/3"


class TmdbNoDisponible(Exception):
    """TMDB no responde, responde con error o falta la API key. No es lo mismo que "sin resultados"."""


def _get(ruta: str, **params) -> dict:
    if not TMDB_API_KEY:
        raise TmdbNoDisponible("Falta TMDB_API_KEY")
    try:
        res = requests.get(f"{API}{ruta}", params={"api_key": TMDB_API_KEY, **params}, timeout=5)
        res.raise_for_status()
        return res.json()
    except (requests.RequestException, ValueError) as e:  # ValueError: JSON roto
        raise TmdbNoDisponible(f"{ruta}: {e}") from e


def buscar(consulta: str, idioma: str = "es-ES", anio: int = None) -> list:
    """Resultados de /search/movie en el orden de TMDB (relevancia). Lista vacía si no hay."""
    # Sin region: con region=ES, release_date es el estreno en España y no casa con el año de la web
    params = {"query": consulta, "language": idioma}
    if anio:
        params["year"] = anio
    return _get("/search/movie", **params).get("results", [])


def es_latino(texto: str) -> bool:
    """True si todas las letras son del alfabeto latino ("Cold War", "Ágora"; no "笛吹川")."""
    letras = [c for c in texto or "" if c.isalpha()]
    return bool(letras) and all(unicodedata.name(c, "").startswith("LATIN") for c in letras)


def _traduccion(detalles: dict, idioma: str, pais: str):
    """Título en ese idioma (primero el de ese país), o None si TMDB no tiene traducción a ese idioma.
    Si es el idioma original, o la traducción existe con el título vacío ("Cars"), es el original."""
    original = detalles.get("original_title")
    if detalles.get("original_language") == idioma:
        return original
    titulos = {(t.get("iso_639_1"), t.get("iso_3166_1")): t.get("data", {}).get("title")
               for t in detalles.get("translations", {}).get("translations", [])
               if t.get("iso_639_1") == idioma}
    if not titulos:
        return None
    return titulos.get((idioma, pais)) or next((v for v in titulos.values() if v), None) or original


def datos_por_id(tmdb_id: int) -> dict:
    """Detalles + vídeos + imágenes + traducciones de una película, en una sola petición."""
    detalles = _get(f"/movie/{tmdb_id}", language="es-ES",
                    append_to_response="videos,images,translations",
                    include_image_language="es,null")  # sin texto o en español

    poster_path = detalles.get("poster_path")
    backdrop_path = detalles.get("backdrop_path")

    # La primera imagen ya es el backdrop principal: no se repite en la galería
    candidatos = detalles.get("images", {}).get("backdrops", [])[1:]
    galeria = [f"https://image.tmdb.org/t/p/w780{img['file_path']}"
               for img in random.sample(candidatos, min(4, len(candidatos))) if img.get("file_path")]

    youtube_id = next((v.get("key") for v in detalles.get("videos", {}).get("results", [])
                       if v.get("site") == "YouTube" and v.get("type") == "Trailer"), None)

    fecha = detalles.get("release_date") or ""
    return {
        "tmdb_id": detalles.get("id"),
        # De las traducciones y no de "title": sin traducción, "title" es el original ("Panny z Wilka")
        "titulo_es": _traduccion(detalles, "es", "ES"),
        "titulo_en": _traduccion(detalles, "en", "US"),
        "titulo_original": detalles.get("original_title"),
        "poster": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None,
        "backdrop": f"https://image.tmdb.org/t/p/original{backdrop_path}" if backdrop_path else None,
        "imagenes_galeria": galeria,
        "youtube_id": youtube_id,
        "sinopsis": detalles.get("overview"),
        "nota": detalles.get("vote_average"),
        "duracion": detalles.get("runtime"),
        "anio": int(fecha[:4]) if fecha[:4].isdigit() else None,
        "generos": ", ".join(g["name"] for g in detalles.get("genres", [])),
    }
