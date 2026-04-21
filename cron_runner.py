"""
cron_runner.py
--------------
Script diseñado para ejecutarse automáticamente cada lunes a las 9:00
mediante cron (Linux/Mac) o el Programador de tareas (Windows).

Flujo:
  1. Obtiene la cartelera de Madrid (cine configurable)
  2. Aplica el filtro de perfil del usuario
  3. Formatea el resumen
  4. Lo envía por Telegram al chat configurado

Variables de entorno requeridas:
  - en local pueden definirse en .env
  - en AWS Lambda se configuran en Environment Variables

Cómo obtener tu TELEGRAM_CHAT_ID:
  1. Escribe cualquier mensaje a tu bot
  2. Abre en el navegador:
     https://api.telegram.org/bot<TOKEN>/getUpdates
  3. Busca el campo "chat": {"id": XXXXXXX}
  4. Ese número es tu CHAT_ID — añádelo al .env

Uso manual para probar:
  python cron_runner.py
  python cron_runner.py --cine callao
  python cron_runner.py --cine yelmo_ideal --dry-run   (no envía, solo imprime)
"""

import os
import sys
import argparse
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

import requests

from scrapers.cartelera_scraper import get_cartelera
from core.filtro import cargar_perfil, filtrar_peliculas, resumen_filtro

# ── Configuración ──────────────────────────────────────────────────────────

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CINE_DEFAULT     = "yelmo_ideal"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── Telegram ───────────────────────────────────────────────────────────────

def enviar_telegram(texto: str, chat_id: str, token: str) -> bool:
    """
    Envía un mensaje de texto a Telegram.
    Divide mensajes largos en bloques de máx. 4096 chars.
    Devuelve True si todos los envíos fueron exitosos.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    exito = True

    # Divide en bloques si el mensaje es muy largo
    bloques = [texto[i:i+4000] for i in range(0, len(texto), 4000)]

    for bloque in bloques:
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id":    chat_id,
                    "text":       bloque,
                    "parse_mode": "Markdown",
                },
                timeout=10,
            )
            if not resp.ok:
                logger.error("Error Telegram: %s", resp.text)
                exito = False
        except requests.exceptions.RequestException as exc:
            logger.error("Error de conexión con Telegram: %s", exc)
            exito = False

    return exito


# ── Formateo del mensaje ───────────────────────────────────────────────────

def formatear_mensaje(peliculas: list[dict], todas: list[dict],
                      perfil: dict, cine: str) -> str:
    """Construye el mensaje de Telegram con el resumen semanal."""
    DIAS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    MESES = ["enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    hoy = datetime.now()
    fecha = f"{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month-1]} de {hoy.year}"

    lineas = [
        f"*RECOMENDACIONES SEMANALES*",
        f"{fecha}",
        f"Cine: *{cine.upper()}*",
        f"",
        resumen_filtro(todas, peliculas, perfil),
        f"{'─' * 30}",
        f"",
    ]

    if not peliculas:
        lineas.append("No hay películas que coincidan con tu perfil esta semana.")
        lineas.append("Considera ajustar `data/perfil.json` para ver más opciones.")
        return "\n".join(lineas)

    for i, p in enumerate(peliculas, 1):
        titulo   = p.get("titulo_es", "N/A")
        anio     = p.get("anio", "N/A")
        nota     = p.get("nota_imdb", "N/A")
        genero   = p.get("genero", "N/A")
        director = p.get("director", "N/A")
        horarios = ", ".join(p.get("horarios", [])) or "N/A"

        lineas += [
            f"*{i}. {titulo}* ({anio})",
            f"IMDb: {nota} ⭐| {genero}",
            f"{director}",
            f"{horarios}",
            f"",
        ]

    lineas.append("_Enviado automáticamente por MovieAgent_")
    return "\n".join(lineas)


# ── Flujo principal ────────────────────────────────────────────────────────

def main(cine: str, dry_run: bool) -> None:
    logger.info("Iniciando cron_runner — cine: %s", cine)

    # 1. Cartelera
    logger.info("Obteniendo cartelera...")
    todas = get_cartelera(cine, enriquecer=True)

    if not todas or "error" in todas[0]:
        error = todas[0].get("error", "Error desconocido") if todas else "Sin resultados"
        logger.error("Error al obtener cartelera: %s", error)
        sys.exit(1)

    logger.info("%d películas encontradas", len(todas))

    # 2. Filtro
    logger.info("🔍 Aplicando filtro de perfil...")
    perfil    = cargar_perfil()
    filtradas = filtrar_peliculas(todas, perfil)
    logger.info("%d películas pasan el filtro", len(filtradas))

    # 3. Mensaje
    mensaje = formatear_mensaje(filtradas, todas, perfil, cine)

    # 4. Envío o dry-run
    if dry_run:
        print("\n" + "─" * 50)
        print("DRY-RUN — Mensaje que se enviaría por Telegram:")
        print("─" * 50)
        print(mensaje)
        print("─" * 50 + "\n")
        logger.info("Dry-run completado. No se envió nada.")
        return

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error(
            "Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en el .env.\n"
            "   Usa --dry-run para probar sin enviar."
        )
        sys.exit(1)

    logger.info("Enviando mensaje a Telegram (chat_id: %s)...", TELEGRAM_CHAT_ID)
    ok = enviar_telegram(mensaje, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)

    if ok:
        logger.info("Mensaje enviado correctamente.")
    else:
        logger.error("Hubo errores al enviar el mensaje.")
        sys.exit(1)


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Envía recomendaciones de cartelera por Telegram."
    )
    parser.add_argument(
        "--cine",
        default=CINE_DEFAULT,
        help=f"Clave del cine a consultar (por defecto: {CINE_DEFAULT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el mensaje por consola sin enviar a Telegram.",
    )
    args = parser.parse_args()
    main(cine=args.cine, dry_run=args.dry_run)


# ── Handler para AWS Lambda + EventBridge ─────────────────────────────────

def lambda_handler(event: dict, context) -> dict:
    """
    Punto de entrada para AWS Lambda.
    EventBridge llama a esta función con un evento vacío en el horario definido.
    Lee el cine desde la variable de entorno CINE (por defecto: yelmo_ideal).
    """
    cine = os.environ.get("CINE", CINE_DEFAULT)
    logger.info("Lambda invocada — cine: %s", cine)

    try:
        main(cine=cine, dry_run=False)
        return {"statusCode": 200, "body": "Recomendaciones enviadas correctamente"}
    except SystemExit as exc:
        # main() llama a sys.exit(1) en caso de error
        return {"statusCode": 500, "body": f"Error al procesar: {exc}"}
    except Exception as exc:
        logger.error("Error inesperado en Lambda: %s", exc, exc_info=True)
        return {"statusCode": 500, "body": str(exc)}