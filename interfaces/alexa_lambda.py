"""
alexa_lambda.py
---------------
Alexa Skill para consultar información de películas y cartelera de Madrid.

Intents disponibles:
  - BuscarPeliculaIntent   → "¿Qué nota tiene Inception?"
  - DirectorIntent         → "¿Quién dirige Interstellar?"
  - SinopsisIntent         → "Cuéntame de qué trata The Matrix"
  - CarreleraIntent        → "¿Qué hay en cartelera en Madrid?"
  - AMAZON.HelpIntent      → "Ayuda"
  - AMAZON.CancelIntent    → "Cancelar"
  - AMAZON.StopIntent      → "Para"

Despliegue:
  1. Sube este archivo a AWS Lambda (runtime: Python 3.12)
  2. Añade la layer de ask-sdk o incluye las dependencias en el zip
  3. Configura las variables de entorno: OMDB_API_KEY
  4. Enlaza la función Lambda con tu Alexa Skill en developer.amazon.com

IMPORTANTE: En Lambda los imports locales NO funcionan directamente.
  El scraper de OMDb está reimplementado inline para que el archivo
  sea completamente autónomo (un solo zip sin dependencias locales).
"""

import os
import logging
import requests

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model import Response

# ── Logger ─────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ── OMDb inline (autónomo para Lambda) ────────────────────────────────────

OMDB_URL = "https://www.omdbapi.com/"

def _omdb(titulo: str) -> dict:
    """Consulta OMDb y devuelve el dict de la película o {'error': '...'}."""
    api_key = os.environ.get("OMDB_API_KEY", "")
    if not api_key:
        return {"error": "API key no configurada"}
    try:
        resp = requests.get(
            OMDB_URL,
            params={"t": titulo, "apikey": api_key, "plot": "short", "r": "json"},
            timeout=8,
        )
        data = resp.json()
        if data.get("Response") == "False":
            return {"error": data.get("Error", "No encontrada")}
        return data
    except Exception as exc:
        return {"error": str(exc)}


def _get_slot(handler_input: HandlerInput, slot_name: str) -> str:
    """Extrae el valor de un slot del intent de forma segura."""
    try:
        slots = handler_input.request_envelope.request.intent.slots
        return slots[slot_name].value or ""
    except (AttributeError, KeyError, TypeError):
        return ""


# ── Textos de ayuda ────────────────────────────────────────────────────────

HELP_TEXT = (
    "Puedo ayudarte con información de películas. "
    "Prueba decir: ¿Qué nota tiene Inception?, "
    "o: ¿Quién dirige Interstellar?, "
    "o: De qué trata The Matrix. "
    "¿Qué quieres saber?"
)

WELCOME_TEXT = (
    "Bienvenido a Movie Agent. "
    "Puedo buscarte información de cualquier película. "
    "¿Sobre qué película quieres saber?"
)


# ── Handlers ───────────────────────────────────────────────────────────────

class LaunchHandler(AbstractRequestHandler):
    """Se ejecuta al abrir la skill sin decir nada más."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak(WELCOME_TEXT)
            .ask("¿Sobre qué película quieres saber?")
            .response
        )


class BuscarPeliculaHandler(AbstractRequestHandler):
    """
    Intent: BuscarPeliculaIntent
    Ejemplo: "¿Qué nota tiene {pelicula}?"
    Devuelve: nota, año, género, director y duración.
    Slot requerido: pelicula
    """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("BuscarPeliculaIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        titulo = _get_slot(handler_input, "pelicula")

        if not titulo:
            speech = "No entendí el nombre de la película. ¿Puedes repetirlo?"
            return (
                handler_input.response_builder
                .speak(speech)
                .ask(speech)
                .response
            )

        data = _omdb(titulo)

        if "error" in data:
            speech = f"No encontré información sobre {titulo}. Prueba con otro título."
        else:
            nombre   = data.get("Title", titulo)
            anio     = data.get("Year", "año desconocido")
            nota     = data.get("imdbRating", "sin nota")
            director = data.get("Director", "director desconocido")
            genero   = data.get("Genre", "género desconocido")
            duracion = data.get("Runtime", "duración desconocida")

            speech = (
                f"{nombre}, del año {anio}. "
                f"Tiene una nota de {nota} sobre 10 en I M D B. "
                f"Es una película de {genero}, "
                f"dirigida por {director}, "
                f"con una duración de {duracion}. "
                f"¿Quieres saber algo más sobre esta película?"
            )

        return (
            handler_input.response_builder
            .speak(speech)
            .ask("¿Quieres buscar otra película?")
            .response
        )


class DirectorHandler(AbstractRequestHandler):
    """
    Intent: DirectorIntent
    Ejemplo: "¿Quién dirige {pelicula}?"
    Slot requerido: pelicula
    """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("DirectorIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        titulo = _get_slot(handler_input, "pelicula")

        if not titulo:
            speech = "¿De qué película quieres saber el director?"
            return (
                handler_input.response_builder
                .speak(speech).ask(speech).response
            )

        data = _omdb(titulo)

        if "error" in data:
            speech = f"No encontré información sobre {titulo}."
        else:
            nombre   = data.get("Title", titulo)
            director = data.get("Director", "director desconocido")
            speech   = f"{nombre} está dirigida por {director}."

        return (
            handler_input.response_builder
            .speak(speech)
            .ask("¿Quieres saber algo más?")
            .response
        )


class SinopsisHandler(AbstractRequestHandler):
    """
    Intent: SinopsisIntent
    Ejemplo: "¿De qué trata {pelicula}?"
    Slot requerido: pelicula
    """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("SinopsisIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        titulo = _get_slot(handler_input, "pelicula")

        if not titulo:
            speech = "¿De qué película quieres la sinopsis?"
            return (
                handler_input.response_builder
                .speak(speech).ask(speech).response
            )

        data = _omdb(titulo)

        if "error" in data:
            speech = f"No encontré información sobre {titulo}."
        else:
            nombre   = data.get("Title", titulo)
            sinopsis = data.get("Plot", "sinopsis no disponible")
            speech   = f"{nombre}. {sinopsis}"

        return (
            handler_input.response_builder
            .speak(speech)
            .ask("¿Quieres saber algo más?")
            .response
        )


class CarreleraHandler(AbstractRequestHandler):
    """
    Intent: CarreleraIntent
    Ejemplo: "¿Qué hay en cartelera en Madrid?"
    Devuelve los títulos de las películas en cartelera (sin enriquecer,
    para que sea rápido en Lambda).
    """

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("CarreleraIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        # Import aquí para que no falle si el módulo no está disponible en Lambda
        try:
            from scrapers.cartelera_scraper import get_cartelera
            peliculas = get_cartelera("yelmo_ideal", enriquecer=False)
            titulos = [p.get("titulo_es", "") for p in peliculas if "error" not in p]

            if not titulos:
                speech = "No pude obtener la cartelera en este momento."
            else:
                lista = ", ".join(titulos[:6])  # máximo 6 para no saturar
                speech = (
                    f"Ahora mismo en el Yelmo Ideal de Madrid puedes ver: {lista}. "
                    f"¿Quieres información sobre alguna de estas películas?"
                )
        except Exception as exc:
            logger.error("Error cartelera: %s", exc)
            speech = "No pude obtener la cartelera en este momento. Inténtalo más tarde."

        return (
            handler_input.response_builder
            .speak(speech)
            .ask("¿Quieres saber algo de alguna de estas películas?")
            .response
        )


class HelpHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak(HELP_TEXT)
            .ask("¿Sobre qué película quieres saber?")
            .response
        )


class CancelAndStopHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input)
            or is_intent_name("AMAZON.StopIntent")(handler_input)
        )

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder
            .speak("¡Hasta luego! Disfruta del cine.")
            .response
        )


class SessionEndedHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response


class GenericExceptionHandler(AbstractExceptionHandler):
    """Captura cualquier error no previsto y responde con gracia."""

    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error("Error no controlado: %s", exception, exc_info=True)
        speech = "Hubo un problema procesando tu petición. Por favor inténtalo de nuevo."
        return (
            handler_input.response_builder
            .speak(speech)
            .ask(speech)
            .response
        )


# ── Skill builder ──────────────────────────────────────────────────────────

sb = SkillBuilder()

sb.add_request_handler(LaunchHandler())
sb.add_request_handler(BuscarPeliculaHandler())
sb.add_request_handler(DirectorHandler())
sb.add_request_handler(SinopsisHandler())
sb.add_request_handler(CarreleraHandler())
sb.add_request_handler(HelpHandler())
sb.add_request_handler(CancelAndStopHandler())
sb.add_request_handler(SessionEndedHandler())
sb.add_exception_handler(GenericExceptionHandler())

# Punto de entrada para AWS Lambda
lambda_handler = sb.lambda_handler()