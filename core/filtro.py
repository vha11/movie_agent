"""
filtro.py
---------
Filtra una lista de películas según el perfil de usuario definido en perfil.json.
 
Campos del perfil (data/perfil.json):
  - nombre           : nombre del usuario (informativo)
  - nota_minima      : float — descarta películas con nota IMDb por debajo de este valor
  - generos          : list[str] — géneros aceptados (vacío = todos)
  - excluir_generos  : list[str] — géneros que nunca se muestran
  - solo_con_horarios: bool — si True, descarta películas sin sesiones hoy
  - solo_con_nota_imdb: bool — si True, descarta películas sin nota IMDb
 
El filtro es AND: una película debe cumplir TODAS las condiciones para pasar.
"""
 
import json
import os
from typing import Any
 
# ── Ruta del perfil ────────────────────────────────────────────────────────
 
# Funciona independientemente de desde dónde se importe el módulo
_DIR = os.path.dirname(__file__)
PERFIL_PATH = os.path.join(_DIR, "..", "data", "perfil.json")
 
 
# ── Carga del perfil ───────────────────────────────────────────────────────
 
def cargar_perfil(ruta: str = PERFIL_PATH) -> dict:
    """
    Carga el perfil de usuario desde un JSON.
    Si el archivo no existe o tiene errores, devuelve el perfil por defecto.
    """
    defaults = {
        "nombre":            "Usuario",
        "nota_minima":       0.0,
        "generos":           [],
        "excluir_generos":   [],
        "solo_con_horarios": False,
        "solo_con_nota_imdb": False,
    }
 
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        # Mezcla con defaults para que campos opcionales siempre existan
        return {**defaults, **datos}
    except FileNotFoundError:
        print(f"Perfil no encontrado en '{ruta}'. Usando perfil por defecto.")
        return defaults
    except json.JSONDecodeError as e:
        print(f"Error al leer el perfil JSON: {e}. Usando perfil por defecto.")
        return defaults
 
 
def guardar_perfil(perfil: dict, ruta: str = PERFIL_PATH) -> None:
    """Guarda el perfil de usuario en el JSON."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(perfil, f, ensure_ascii=False, indent=2)
 
 
# ── Filtrado ───────────────────────────────────────────────────────────────
 
def filtrar_peliculas(peliculas: list[dict], perfil: dict | None = None) -> list[dict]:
    """
    Aplica el perfil de usuario a una lista de películas.
 
    Args:
        peliculas : lista de dicts devuelta por cartelera_scraper o imdb_scraper.
        perfil    : dict con las preferencias. Si None, carga desde perfil.json.
 
    Returns:
        Lista filtrada y ordenada por nota IMDb (descendente).
    """
    if perfil is None:
        perfil = cargar_perfil()
 
    resultado = [p for p in peliculas if _cumple_perfil(p, perfil)]
 
    # Ordena por nota IMDb descendente; películas sin nota van al final
    resultado.sort(key=lambda p: _nota_float(p.get("nota_imdb")), reverse=True)
 
    return resultado
 
 
def _cumple_perfil(pelicula: dict, perfil: dict) -> bool:
    """
    Devuelve True si la película cumple TODAS las condiciones del perfil.
    Cada condición es una función independiente → fácil de extender.
    """
    checks = [
        _check_nota_minima,
        _check_generos_aceptados,
        _check_generos_excluidos,
        _check_horarios,
        _check_nota_imdb_requerida,
    ]
    return all(check(pelicula, perfil) for check in checks)
 
 
# ── Checks individuales ────────────────────────────────────────────────────
# Cada función recibe (pelicula, perfil) y devuelve bool.
# Para añadir un nuevo criterio: crea una función y agrégala a `checks`.
 
def _check_nota_minima(pelicula: dict, perfil: dict) -> bool:
    """Descarta si la nota IMDb es menor que nota_minima."""
    nota_minima = float(perfil.get("nota_minima", 0))
    if nota_minima <= 0:
        return True  # sin restricción
    nota = _nota_float(pelicula.get("nota_imdb"))
    if nota is None:
        # Sin nota: pasa si no exigimos nota IMDb obligatoria
        return not perfil.get("solo_con_nota_imdb", False)
    return nota >= nota_minima
 
 
def _check_generos_aceptados(pelicula: dict, perfil: dict) -> bool:
    """Si el perfil tiene géneros preferidos, la película debe tener al menos uno."""
    generos_perfil = [g.lower() for g in perfil.get("generos", [])]
    if not generos_perfil:
        return True  # sin restricción de géneros
 
    genero_peli = pelicula.get("genero", "") or ""
    generos_peli = [g.strip().lower() for g in genero_peli.split(",")]
 
    return any(g in generos_peli for g in generos_perfil)
 
 
def _check_generos_excluidos(pelicula: dict, perfil: dict) -> bool:
    """Descarta si la película tiene algún género excluido."""
    excluidos = [g.lower() for g in perfil.get("excluir_generos", [])]
    if not excluidos:
        return True
 
    genero_peli = pelicula.get("genero", "") or ""
    generos_peli = [g.strip().lower() for g in genero_peli.split(",")]
 
    return not any(g in generos_peli for g in excluidos)
 
 
def _check_horarios(pelicula: dict, perfil: dict) -> bool:
    """Si solo_con_horarios es True, descarta películas sin sesiones."""
    if not perfil.get("solo_con_horarios", False):
        return True
    horarios = pelicula.get("horarios", [])
    return bool(horarios)
 
 
def _check_nota_imdb_requerida(pelicula: dict, perfil: dict) -> bool:
    """Si solo_con_nota_imdb es True, descarta películas sin nota IMDb."""
    if not perfil.get("solo_con_nota_imdb", False):
        return True
    nota = pelicula.get("nota_imdb", "N/A")
    return nota not in (None, "N/A", "")
 
 
# ── Utilidades ─────────────────────────────────────────────────────────────
 
def _nota_float(nota: Any) -> float | None:
    """Convierte la nota a float para comparaciones. Devuelve None si no es válida."""
    try:
        return float(nota)
    except (TypeError, ValueError):
        return None
 
 
def resumen_filtro(todas: list[dict], filtradas: list[dict], perfil: dict) -> str:
    """Devuelve un texto resumen del resultado del filtro."""
    nombre = perfil.get("nombre", "Usuario")
    total = len(todas)
    pasaron = len(filtradas)
    descartadas = total - pasaron
    return (
        f"Perfil: {nombre}\n"
        f"Total películas: {total} → "
        f"Pasan el filtro: {pasaron} | "
        f"Descartadas: {descartadas}"
    )
 
 
# ── Ejecución directa para pruebas ────────────────────────────────────────
 
if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
 
    from scrapers.cartelera_scraper import get_cartelera
 
    cine = sys.argv[1] if len(sys.argv) > 1 else "yelmo_ideal"
 
    print(f"\nObteniendo cartelera de '{cine}'...")
    todas = get_cartelera(cine, enriquecer=True)
 
    perfil = cargar_perfil()
    filtradas = filtrar_peliculas(todas, perfil)
 
    print(f"\n{resumen_filtro(todas, filtradas, perfil)}\n")
    print(f"{'─' * 50}\n")
 
    if not filtradas:
        print("No hay películas que coincidan con tu perfil.\n")
        sys.exit(0)
 
    for i, p in enumerate(filtradas, 1):
        print(f"[{i}] {p.get('titulo_es', 'N/A')}  ({p.get('anio', 'N/A')})")
        print(f"     IMDb: {p.get('nota_imdb', 'N/A')}  |  "
              f"eCartelera: {p.get('nota_ec', 'N/A')}")
        print(f"     Género:   {p.get('genero', 'N/A')}")
        print(f"     Director: {p.get('director', 'N/A')}")
        print(f"     Duración: {p.get('duracion', 'N/A')}")
        print(f"     Horarios: {', '.join(p.get('horarios', [])) or 'N/A'}")
        print()