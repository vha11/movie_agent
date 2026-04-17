"""
imdb_scraper.py
---------------
Obtiene información de una película usando la API de OMDb (Open Movie Database).
OMDb devuelve datos oficiales de IMDb en formato JSON, sin scraping frágil.

Requiere: OMDB_API_KEY en el archivo .env de la raíz del proyecto.
"""

import os
import requests
from dotenv import load_dotenv

# Carga las variables del archivo .env (OMDB_API_KEY)
load_dotenv()

OMDB_API_URL = "https://www.omdbapi.com/"
TIMEOUT = 10


# ── Función principal ───────────────────────────────────────────────────────

def get_movie_info(title: str) -> dict:
    """
    Recibe el nombre de una película y devuelve un diccionario con:
        titulo, nota, votos, sinopsis, director, duracion, anio, url
    En caso de error devuelve un dict con clave 'error'.
    """
    api_key = os.getenv("OMDB_API_KEY")
    if not api_key:
        return {"error": "No se encontró OMDB_API_KEY en el archivo .env"}

    try:
        data = _fetch_omdb(title, api_key)
        if data.get("Response") == "False":
            return {"error": f"Película no encontrada: {data.get('Error', 'Error desconocido')}"}

        return _parse_response(data)

    except requests.exceptions.Timeout:
        return {"error": "Tiempo de espera agotado. Intenta de nuevo."}
    except requests.exceptions.ConnectionError:
        return {"error": "Sin conexión a Internet."}
    except Exception as exc:
        return {"error": f"Error inesperado: {exc}"}


# ── Petición a la API ───────────────────────────────────────────────────────

def _fetch_omdb(title: str, api_key: str) -> dict:
    """Llama a la API de OMDb y devuelve el JSON en bruto."""
    params = {
        "t": title,       # busca por título
        "apikey": api_key,
        "plot": "full",   # sinopsis completa
        "r": "json",
    }
    resp = requests.get(OMDB_API_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ── Parseo de la respuesta ─────────────────────────────────────────────────

def _parse_response(data: dict) -> dict:
    """Extrae y limpia los campos que nos interesan del JSON de OMDb."""
    imdb_id = data.get("imdbID", "")
    url = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else "N/A"

    return {
        "titulo":   data.get("Title",    "N/A"),
        "anio":     data.get("Year",     "N/A"),
        "nota":     data.get("imdbRating", "N/A"),
        "votos":    data.get("imdbVotes", "N/A"),
        "sinopsis": data.get("Plot",     "N/A"),
        "director": data.get("Director", "N/A"),
        "duracion": data.get("Runtime",  "N/A"),
        "genero":   data.get("Genre",    "N/A"),
        "url":      url,
    }


# ── Ejecución directa para pruebas rápidas ────────────────────────────────

if __name__ == "__main__":
    import sys
    import json

    pelicula = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Inception"
    print(f"\nBuscando: {pelicula}\n{'─' * 40}")
    resultado = get_movie_info(pelicula)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))