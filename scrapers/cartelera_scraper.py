"""
cartelera_scraper.py
--------------------
Obtiene la cartelera de Madrid desde eCartelera y enriquece los datos
con información de OMDb (nota IMDb, sinopsis, director, etc.).

Estructura real de eCartelera (verificada):
  - Los hrefs son URLs completas: https://www.ecartelera.com/peliculas/slug/
  - Cada película aparece como: Título / Sinopsis / Fotos (3 enlaces al mismo slug)
  - El bloque de texto tiene: "166 min. EE.UU. Género Dir.: Nombre Horarios Nota"
"""

import sys
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Número de hilos para peticiones paralelas a OMDb.
# 5 es un valor seguro: no sobrecarga la API gratuita y reduce
# el tiempo de ~13s en serie a ~3s en paralelo.
MAX_WORKERS = 5

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from bs4 import BeautifulSoup
from scrapers.imdb_scraper import get_movie_info

# ── Configuración ─────────────────────────────────────────────────────────

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}

TIMEOUT = 10

CINES_MADRID = {
    "callao":      "https://www.ecartelera.com/cines/8,0,1.html",
    "capitol":     "https://www.ecartelera.com/cines/9,0,1.html",
    "paz":         "https://www.ecartelera.com/cines/40,0,1.html",
    "palafox":     "https://www.ecartelera.com/cines/39,0,1.html",
    "verdi":       "https://www.ecartelera.com/cines/51,0,1.html",
    "yelmo_ideal": "https://www.ecartelera.com/cines/54,0,1.html",
    "renoir":      "https://www.ecartelera.com/cines/44,0,1.html",
    "princesa":    "https://www.ecartelera.com/cines/20,0,1.html",
}

CINE_DEFAULT = "callao"

# Textos que NO son títulos reales (son enlaces de navegación o sub-enlaces)
TEXTOS_EXCLUIDOS = {"sinopsis", "fotos", "películas", "peliculas", "ver tráiler",
                    "ver trailer", "tráiler", "trailer", ""}

# Regex para identificar slugs de película (URL completa de eCartelera)
RE_PELICULA = re.compile(
    r"https://www\.ecartelera\.com/peliculas/[^/]+/$"
)


# ── Función principal ──────────────────────────────────────────────────────

def get_cartelera(cine: str = CINE_DEFAULT, enriquecer: bool = True) -> list[dict]:
    """
    Obtiene la cartelera de un cine de Madrid.

    Args:
        cine:       Clave del cine (ver CINES_MADRID). Por defecto 'callao'.
        enriquecer: Si True, añade datos de OMDb.

    Returns:
        Lista de dicts con información de cada película.
    """
    url = CINES_MADRID.get(cine)
    if not url:
        claves = ", ".join(CINES_MADRID.keys())
        return [{"error": f"Cine '{cine}' no encontrado. Opciones: {claves}"}]

    try:
        peliculas = _scrape_cartelera(url)
        if enriquecer:
            peliculas = _enriquecer_con_omdb(peliculas)
        return peliculas

    except requests.exceptions.Timeout:
        return [{"error": "Tiempo de espera agotado al contactar eCartelera."}]
    except requests.exceptions.ConnectionError:
        return [{"error": "Sin conexión a Internet."}]
    except Exception as exc:
        return [{"error": f"Error inesperado: {exc}"}]


# ── Scraping ───────────────────────────────────────────────────────────────

def _scrape_cartelera(url: str) -> list[dict]:
    """
    Descarga la página y extrae las películas.

    Clave: los enlaces al slug de película aparecen 2-3 veces
    (título, sinopsis, fotos). Nos quedamos solo con el que tiene
    texto que NO está en TEXTOS_EXCLUIDOS → ese es el título real.
    """
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    peliculas = []
    slugs_vistos = set()

    # Todos los enlaces cuya URL encaja con el patrón de película
    for a in soup.find_all("a", href=RE_PELICULA):
        texto = a.get_text(strip=True)
        href  = a.get("href", "")

        # Saltamos si es un sub-enlace (sinopsis, fotos...) o ya procesamos este slug
        if texto.lower() in TEXTOS_EXCLUIDOS:
            continue
        if href in slugs_vistos:
            continue

        slugs_vistos.add(href)

        # Extraemos datos del bloque padre
        bloque = _encontrar_bloque(a)
        texto_bloque = bloque.get_text(" ", strip=True) if bloque else ""

        duracion = _extraer_duracion(texto_bloque)
        director = _extraer_director(texto_bloque)
        horarios = _extraer_horarios(bloque)
        nota_ec  = _extraer_nota_ec(texto_bloque)

        peliculas.append({
            "titulo_es":   texto,
            "duracion_ec": duracion,
            "director_ec": director,
            "nota_ec":     nota_ec,
            "horarios":    horarios,
            "url_ec":      href,
        })

    return peliculas


def _encontrar_bloque(tag) -> BeautifulSoup | None:
    """Sube en el árbol hasta encontrar un contenedor con imagen (el cartel)."""
    actual = tag.parent
    for _ in range(8):
        if actual is None:
            break
        if actual.find("img"):
            return actual
        actual = actual.parent
    return tag.parent


def _extraer_duracion(texto: str) -> str:
    m = re.search(r"(\d{2,3})\s*min", texto)
    return f"{m.group(1)} min" if m else "N/A"


def _extraer_director(texto: str) -> str:
    """El director aparece como 'Dir.: Nombre Apellido' en el texto del bloque."""
    m = re.search(r"Dir\.\s*:\s*(.+?)(?:Horarios|$)", texto)
    if m:
        # Limpia espacios extra y coge solo la primera línea
        nombres = m.group(1).strip().split("  ")[0]
        return nombres.strip()
    return "N/A"


def _extraer_horarios(bloque) -> list[str]:
    """Los horarios son enlaces a /cines/comprar/... con formato HH:MM."""
    if bloque is None:
        return []
    return [
        a.get_text(strip=True)
        for a in bloque.find_all("a", href=re.compile(r"/comprar/"))
        if re.match(r"\d{1,2}:\d{2}", a.get_text(strip=True))
    ]


def _extraer_nota_ec(texto: str) -> str:
    """
    La nota de eCartelera es un número entre 1-10 que aparece
    al final del bloque, después de los horarios.
    """
    m = re.search(r"(?:Horarios[^0-9]*).*\b(10|[1-9](?:\.\d)?)\s*$", texto)
    if m:
        return m.group(1)
    # fallback: último número entre 1-10 en el texto
    matches = re.findall(r"\b(10|[1-9](?:\.\d)?)\b", texto)
    return matches[-1] if matches else "N/A"


# ── Enriquecimiento con OMDb ───────────────────────────────────────────────

def _titulo_desde_slug(url_ec: str) -> str:
    """
    Extrae un título legible desde el slug de la URL de eCartelera.
    Ejemplo: '.../peliculas/proyecto-salvacion/' → 'proyecto salvacion'
    Sirve como segundo intento de búsqueda en OMDb cuando el título
    en español no se encuentra (p.ej. títulos con caracteres especiales).
    """
    m = re.search(r"/peliculas/([^/]+)/", url_ec or "")
    if m:
        return m.group(1).replace("-", " ")
    return ""


def _enriquecer_una(peli: dict) -> dict:
    """
    Enriquece UNA película con datos de OMDb.
    Diseñada para ejecutarse en un hilo independiente.
    """
    titulo = peli.get("titulo_es", "")
    omdb = get_movie_info(titulo)

    # Segundo intento: slug de la URL (sin guiones ni acentos)
    if "error" in omdb:
        titulo_slug = _titulo_desde_slug(peli.get("url_ec", ""))
        if titulo_slug and titulo_slug.lower() != titulo.lower():
            omdb = get_movie_info(titulo_slug)

    if "error" in omdb:
        return {
            "titulo_es":  titulo,
            "titulo_en":  "N/A",
            "anio":       "N/A",
            "nota_imdb":  "N/A",
            "nota_ec":    peli.get("nota_ec"),
            "votos":      "N/A",
            "genero":     "N/A",
            "director":   peli.get("director_ec"),
            "duracion":   peli.get("duracion_ec"),
            "sinopsis":   "N/A",
            "horarios":   peli.get("horarios", []),
            "url_imdb":   "N/A",
            "url_ec":     peli.get("url_ec"),
        }

    return {
        "titulo_es":  titulo,
        "titulo_en":  omdb.get("titulo"),
        "anio":       omdb.get("anio"),
        "nota_imdb":  omdb.get("nota"),
        "nota_ec":    peli.get("nota_ec"),
        "votos":      omdb.get("votos"),
        "genero":     omdb.get("genero"),
        "director":   omdb.get("director") or peli.get("director_ec"),
        "duracion":   omdb.get("duracion") or peli.get("duracion_ec"),
        "sinopsis":   omdb.get("sinopsis"),
        "horarios":   peli.get("horarios", []),
        "url_imdb":   omdb.get("url"),
        "url_ec":     peli.get("url_ec"),
    }


def _enriquecer_con_omdb(peliculas: list[dict]) -> list[dict]:
    """
    Lanza peticiones a OMDb en paralelo usando ThreadPoolExecutor.
    MAX_WORKERS hilos simultáneos → el tiempo baja de O(n) serie a O(n/workers).
    El orden de la lista de entrada se preserva gracias al índice.
    """
    resultados = [None] * len(peliculas)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Mapeamos cada future a su índice original para preservar el orden
        futures = {
            executor.submit(_enriquecer_una, peli): i
            for i, peli in enumerate(peliculas)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                resultados[idx] = future.result()
            except Exception as exc:
                # Si un hilo falla, devolvemos la info básica de eCartelera
                peli = peliculas[idx]
                resultados[idx] = {
                    "titulo_es": peli.get("titulo_es", "N/A"),
                    "error_omdb": str(exc),
                    "horarios":  peli.get("horarios", []),
                    "url_ec":    peli.get("url_ec"),
                }

    return resultados



# ── Ejecución directa ──────────────────────────────────────────────────────

if __name__ == "__main__":
    cine = sys.argv[1] if len(sys.argv) > 1 else CINE_DEFAULT
    print(f"\nCartelera del cine '{cine}' — Madrid")
    print(f"{'─' * 50}\n")

    peliculas = get_cartelera(cine, enriquecer=True)

    if not peliculas:
        print("No se encontraron películas.")
        sys.exit(1)

    for i, p in enumerate(peliculas, 1):
        if "error" in p:
            print(f"Error: {p['error']}\n")
            continue

        print(f"[{i}] {p.get('titulo_es', 'N/A')}  ({p.get('anio', 'N/A')})")
        print(f"     IMDb: {p.get('nota_imdb', 'N/A')}  |  "
              f"eCartelera: {p.get('nota_ec', 'N/A')}")
        print(f"     Género:   {p.get('genero', 'N/A')}")
        print(f"     Director: {p.get('director', 'N/A')}")
        print(f"     Duración: {p.get('duracion', 'N/A')}")
        print(f"     Horarios: {', '.join(p.get('horarios', [])) or 'N/A'}")
        print()

    print(f"Total: {len(peliculas)} película(s) encontrada(s).\n")