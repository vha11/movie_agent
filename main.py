"""
main.py
-------
CLI para buscar información de películas usando OMDb API.

Uso:
    python main.py "Inception"
    python main.py "El Padrino" --campo nota
    python main.py "Interstellar" --campo director
    python main.py "The Matrix" --campo sinopsis

Campos disponibles: titulo, anio, nota, votos, sinopsis, director, duracion, genero, url
"""

import sys
import argparse
from scrapers.imdb_scraper import get_movie_info


# ── Campos disponibles y sus etiquetas legibles ───────────────────────────

CAMPOS = {
    "titulo":   "Título",
    "anio":     "Año",
    "nota":     "Nota IMDb",
    "votos":    "Votos",
    "sinopsis": "Sinopsis",
    "director": "Director",
    "duracion": "Duración",
    "genero":   "Género",
    "url":      "URL IMDb",
}


# ── Impresión de resultados ───────────────────────────────────────────────

def imprimir_resultado_completo(info: dict) -> None:
    """Muestra todos los campos de la película de forma clara."""
    print()
    print(f"{info.get('titulo', 'N/A')}  ({info.get('anio', 'N/A')})")
    print("─" * 50)
    print(f"Nota:      {info.get('nota', 'N/A')} / 10  ({info.get('votos', 'N/A')} votos)")
    print(f"Género:    {info.get('genero', 'N/A')}")
    print(f"Director:  {info.get('director', 'N/A')}")
    print(f"Duración:  {info.get('duracion', 'N/A')}")
    print(f"Sinopsis:  {info.get('sinopsis', 'N/A')}")
    print(f"URL:       {info.get('url', 'N/A')}")
    print()


def imprimir_campo(info: dict, campo: str) -> None:
    """Muestra únicamente el campo solicitado."""
    if campo not in CAMPOS:
        print(f"\nCampo '{campo}' no válido.")
        print(f"Campos disponibles: {', '.join(CAMPOS.keys())}\n")
        sys.exit(1)

    etiqueta = CAMPOS[campo]
    valor = info.get(campo, "N/A")
    print(f"\n{etiqueta}: {valor}\n")


# ── Parser de argumentos ──────────────────────────────────────────────────

def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="movie_agent",
        description="Busca información de películas usando OMDb (datos de IMDb).",
        epilog="Ejemplo: python main.py \"Inception\" --campo nota",
    )
    parser.add_argument(
        "pelicula",
        type=str,
        help="Nombre de la película a buscar (entre comillas si tiene espacios).",
    )
    parser.add_argument(
        "--campo",
        type=str,
        default=None,
        metavar="CAMPO",
        help=(
            "Campo específico a mostrar. "
            f"Opciones: {', '.join(CAMPOS.keys())}"
        ),
    )
    return parser


# ── Punto de entrada ──────────────────────────────────────────────────────

def main() -> None:
    parser = construir_parser()
    args = parser.parse_args()

    print(f"\nBuscando: {args.pelicula} ...")

    info = get_movie_info(args.pelicula)

    # Si hubo un error, mostrarlo y salir
    if "error" in info:
        print(f"\n{info['error']}\n")
        sys.exit(1)

    # Mostrar campo específico o resultado completo
    if args.campo:
        imprimir_campo(info, args.campo)
    else:
        imprimir_resultado_completo(info)


if __name__ == "__main__":
    main()