"""
bot_telegram.py
---------------
Bot de Telegram para buscar información de películas y cartelera de Madrid.

Comandos disponibles:
  /start            — Bienvenida y ayuda
  /pelicula <titulo> — Info completa de una película (OMDb)
  /cartelera [cine]  — Cartelera de Madrid (por defecto: yelmo_ideal)
  /recomendaciones [cine] — Cartelera filtrada por tu perfil
  /cines             — Lista de cines disponibles
  /ayuda             — Muestra esta ayuda

Uso:
  python interfaces/bot_telegram.py
"""

import os
import sys
import logging

# Permite importar módulos del proyecto desde cualquier carpeta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from scrapers.imdb_scraper import get_movie_info
from scrapers.cartelera_scraper import get_cartelera, CINES_MADRID
from core.filtro import cargar_perfil, filtrar_peliculas, resumen_filtro

# ── Configuración ─────────────────────────────────────────────────────────

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

CINE_DEFAULT = "yelmo_ideal"


# ── Formateadores ──────────────────────────────────────────────────────────

def _fmt_pelicula(p: dict) -> str:
    """Formatea un dict de película para Telegram (Markdown)."""
    titulo  = p.get("titulo_es") or p.get("titulo", "N/A")
    anio    = p.get("anio", "N/A")
    nota    = p.get("nota_imdb") or p.get("nota", "N/A")
    votos   = p.get("votos", "N/A")
    genero  = p.get("genero", "N/A")
    director = p.get("director", "N/A")
    duracion = p.get("duracion", "N/A")
    sinopsis = p.get("sinopsis", "N/A")
    url     = p.get("url_imdb") or p.get("url", "")

    horarios = p.get("horarios", [])
    horarios_txt = ", ".join(horarios) if horarios else "N/A"

    lineas = [
        f"*{titulo}* ({anio})",
        f"Nota IMDb: *{nota}* ({votos} votos)",
        f"Género: {genero}",
        f"Director: {director}",
        f"Duración: {duracion}",
    ]
    if horarios:
        lineas.append(f"Horarios: {horarios_txt}")
    if sinopsis and sinopsis != "N/A":
        # Limita la sinopsis a 300 caracteres para no saturar el chat
        sinopsis_corta = sinopsis[:300] + "..." if len(sinopsis) > 300 else sinopsis
        lineas.append(f"_{sinopsis_corta}_")
    if url and url != "N/A":
        lineas.append(f"🔗[Ver en IMDb]({url})")

    return "\n".join(lineas)


def _fmt_cartelera(peliculas: list[dict], nombre_cine: str) -> list[str]:
    """
    Divide la cartelera en mensajes de máximo 4096 chars (límite de Telegram).
    Devuelve una lista de strings, cada uno es un mensaje separado.
    """
    mensajes = []
    actual = f"🎬 *Cartelera — {nombre_cine.upper()}*\n{'─' * 30}\n\n"

    for i, p in enumerate(peliculas, 1):
        bloque = (
            f"*{i}. {p.get('titulo_es', 'N/A')}* ({p.get('anio', 'N/A')})\n"
            f"IMDb: {p.get('nota_imdb', 'N/A')} | "
            f"eCartelera: {p.get('nota_ec', 'N/A')}\n"
            f"{p.get('genero', 'N/A')}\n"
            f"{', '.join(p.get('horarios', [])) or 'N/A'}\n\n"
        )
        # Si el mensaje actual + bloque supera el límite, guárdalo y empieza uno nuevo
        if len(actual) + len(bloque) > 4000:
            mensajes.append(actual)
            actual = bloque
        else:
            actual += bloque

    if actual.strip():
        mensajes.append(actual)

    return mensajes if mensajes else ["No se encontraron películas."]

# ── Handlers de comandos ───────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texto = (
        "👋 ¡Hola! Soy *MovieAgent*, tu asistente de cine.\n\n"
        "*Comandos disponibles:*\n"
        "/pelicula `<título>` — Info de una película\n"
        "/cartelera `[cine]` — Cartelera de Madrid\n"
        "/recomendaciones `[cine]` — Filtrada por tu perfil\n"
        "/cines — Ver cines disponibles\n"
        "/ayuda — Ver esta ayuda\n\n"
        "💡 *Ejemplo:* `/pelicula Inception`"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_cines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lista = "\n".join(f"  • `{clave}`" for clave in CINES_MADRID.keys())
    texto = f"*Cines disponibles:*\n{lista}\n\n💡 Uso: `/cartelera palafox`"
    await update.message.reply_text(texto, parse_mode="Markdown")


async def cmd_pelicula(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca información de una película por título."""
    if not context.args:
        await update.message.reply_text(
            "Debes indicar el título.\n💡 Ejemplo: `/pelicula Inception`",
            parse_mode="Markdown",
        )
        return

    titulo = " ".join(context.args)
    msg = await update.message.reply_text(f"🔍 Buscando *{titulo}*...", parse_mode="Markdown")

    info = get_movie_info(titulo)

    if "error" in info:
        await msg.edit_text(f"{info['error']}")
        return

    await msg.edit_text(_fmt_pelicula(info), parse_mode="Markdown", disable_web_page_preview=True)


async def cmd_cartelera(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la cartelera completa de un cine."""
    cine = context.args[0].lower() if context.args else CINE_DEFAULT

    if cine not in CINES_MADRID:
        claves = ", ".join(f"`{k}`" for k in CINES_MADRID.keys())
        await update.message.reply_text(
            f"Cine *{cine}* no encontrado.\nCines disponibles: {claves}",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text(
        f"Obteniendo cartelera de *{cine}*...", parse_mode="Markdown"
    )

    peliculas = get_cartelera(cine, enriquecer=True)

    if not peliculas or "error" in peliculas[0]:
        error = peliculas[0].get("error", "Error desconocido") if peliculas else "Sin resultados"
        await msg.edit_text(f"{error}")
        return

    await msg.delete()
    for mensaje in _fmt_cartelera(peliculas, cine):
        await update.message.reply_text(mensaje, parse_mode="Markdown")


async def cmd_recomendaciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la cartelera filtrada según el perfil del usuario."""
    cine = context.args[0].lower() if context.args else CINE_DEFAULT

    if cine not in CINES_MADRID:
        claves = ", ".join(f"`{k}`" for k in CINES_MADRID.keys())
        await update.message.reply_text(
            f"Cine *{cine}* no encontrado.\nDisponibles: {claves}",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text(
        f"Buscando recomendaciones en *{cine}*...", parse_mode="Markdown"
    )

    todas = get_cartelera(cine, enriquecer=True)
    perfil = cargar_perfil()
    filtradas = filtrar_peliculas(todas, perfil)

    resumen = resumen_filtro(todas, filtradas, perfil)

    if not filtradas:
        await msg.edit_text(
            f"{resumen}\n\nNinguna película coincide con tu perfil.\n"
            f"Edita `data/perfil.json` para ajustar tus preferencias."
        )
        return

    await msg.edit_text(resumen)
    for mensaje in _fmt_cartelera(filtradas, f"{cine} (recomendadas)"):
        await update.message.reply_text(mensaje, parse_mode="Markdown")


# ── Arranque del bot ───────────────────────────────────────────────────────

def main() -> None:
    if not TOKEN:
        print("TELEGRAM_TOKEN no encontrado en .env")
        sys.exit(1)

    print("Iniciando MovieAgent Bot...")
    print("Presiona Ctrl+C para detenerlo.\n")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",           cmd_start))
    app.add_handler(CommandHandler("ayuda",           cmd_ayuda))
    app.add_handler(CommandHandler("cines",           cmd_cines))
    app.add_handler(CommandHandler("pelicula",        cmd_pelicula))
    app.add_handler(CommandHandler("cartelera",       cmd_cartelera))
    app.add_handler(CommandHandler("recomendaciones", cmd_recomendaciones))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()