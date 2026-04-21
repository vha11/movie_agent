# Movie Agent

Agente inteligente para consultar información de películas y cartelera de Madrid. Integra una API REST, interfaz web, bot de Telegram, Alexa Skill y automatización serverless con AWS.

---

## ¿Por qué OMDb y no IMDb directamente?

IMDb pertenece a Amazon y **no ofrece una API pública gratuita estándar**. El acceso a sus datos es de pago o restringido (AWS datasets, licencias comerciales). Además, IMDb bloquea activamente cualquier intento de scraping mediante:

- **Cloudflare** — protección anti-bot a nivel de red
- **Rate limiting agresivo** — bloquea IPs que hacen demasiadas peticiones
- **Cambios frecuentes de HTML** — los selectores se rompen constantemente

**Solución: [OMDb API](https://www.omdbapi.com/)** (Open Movie Database)

OMDb expone exactamente los mismos datos de IMDb (ratings, votos, sinopsis, director, duración...) a través de una API JSON estable, sin bloqueos y sin scraping frágil. Es gratuita hasta **1.000 peticiones/día**.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        MOVIE AGENT                          │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   CLI        │   Web Flask  │  Bot Telegram│  Alexa Skill   │
│  main.py     │  web_app.py  │ bot_telegram │ alexa_lambda   │
└──────┬───────┴──────┬───────┴──────┬───────┴───────┬────────┘
       │              │              │               │
       └──────────────┴──────────────┴───────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
       imdb_scraper    cartelera_scraper    filtro
       (OMDb API)      (eCartelera)        (perfil.json)

Automatización serverless:
  EventBridge Scheduler (cada lunes 9:00)
          ↓
  Lambda  movieagent-cron
          ↓
  Scraper cartelera + OMDb API
          ↓
  Filtro por perfil de usuario
          ↓
  Mensaje Telegram
```

---

## Estructura del proyecto

```
movie_agent/
│
├── scrapers/
│   ├── __init__.py
│   ├── imdb_scraper.py        # Datos de películas via OMDb API
│   └── cartelera_scraper.py   # Cartelera de Madrid (eCartelera) en paralelo
│
├── core/
│   ├── __init__.py
│   └── filtro.py              # Filtro extensible por perfil de usuario
│
├── interfaces/
│   ├── __init__.py
│   ├── web_app.py             # Interfaz web con Flask
│   ├── bot_telegram.py        # Bot de Telegram (6 comandos)
│   └── alexa_lambda.py        # Alexa Skill para AWS Lambda
│
├── data/
│   └── perfil.json            # Perfil de usuario: géneros, nota mínima, etc.
│
├── main.py                    # CLI: busca películas desde la terminal
├── cron_runner.py             # Script de automatización (Lambda + EventBridge)
├── .env                       # Variables de entorno — NO subir a git
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Requisitos previos

- **Python 3.12** — versión recomendada. Otras versiones pueden tener incompatibilidades con algunas dependencias (por ejemplo, `lxml` no compila en Python 3.14 en Windows).
- Cuenta gratuita en [OMDb API](https://www.omdbapi.com/apikey.aspx)
- Bot de Telegram creado con [@BotFather](https://t.me/BotFather)
- (Opcional) Cuenta AWS para Lambda + EventBridge y dispositivo Alexa para la Skill

---

## Instalación

### 1. Clona o descarga el proyecto

```bash
git clone <url-del-repo>
cd movie_agent
```

### 2. Verifica que tienes Python 3.12

```bash
python --version
# Debe mostrar Python 3.12.x
```

### 3. Crea un entorno virtual

```bash
python -m venv venv
```

Actívalo según tu sistema operativo:

```bash
# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

Sabrás que está activo porque verás `(venv)` al inicio de la terminal.

### 4. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 5. Consigue tu API key de OMDb (gratis)

1. Ve a [https://www.omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)
2. Selecciona **FREE** (1.000 peticiones/día)
3. Introduce tu email y envía el formulario
4. **Activa la key** desde el enlace que recibirás por email (revisa spam)

### 6. Crea el archivo `.env`

En la raíz del proyecto crea un archivo llamado `.env` con este contenido:

```env
OMDB_API_KEY=tu_api_key_aqui
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

> **Cómo obtener el TELEGRAM_CHAT_ID:**
> 1. Escribe cualquier mensaje a tu bot
> 2. Abre en el navegador: `https://api.telegram.org/bot<TOKEN>/getUpdates`
> 3. Busca el campo `"chat": {"id": XXXXXXX}` — ese número es tu chat ID

---

## Librerías instaladas

| Librería | Versión | Para qué se usa |
|---|---|---|
| `requests` | 2.32.3 | Peticiones HTTP a OMDb y eCartelera |
| `beautifulsoup4` | 4.12.3 | Parsear HTML de eCartelera |
| `flask` | 3.0.3 | Interfaz web |
| `python-telegram-bot` | 21.3 | Bot de Telegram |
| `ask-sdk-core` | 1.19.0 | Alexa Skill en AWS Lambda |
| `python-dotenv` | 1.0.1 | Carga variables de entorno desde `.env` |

> `lxml` fue eliminado — no tiene wheel precompilado para Python 3.14 en Windows. BeautifulSoup usa `html.parser` nativo de Python sin necesidad de instalación adicional.

---

## Uso

### CLI — buscar una película

```bash
python main.py "Inception"
python main.py "The Godfather" --campo nota
python main.py "Interstellar" --campo director
python main.py "The Matrix" --campo sinopsis
```

Campos disponibles: `titulo`, `anio`, `nota`, `votos`, `sinopsis`, `director`, `duracion`, `genero`, `url`

### Interfaz web

```bash
python interfaces/web_app.py
```

Abre [http://localhost:5000](http://localhost:5000) en el navegador.

| URL | Qué muestra |
|---|---|
| `/` | Buscador principal |
| `/buscar?q=Inception` | Ficha de la película |
| `/cartelera` | Cartelera del cine por defecto |
| `/cartelera/callao` | Cartelera del Callao |
| `/cartelera/palafox` | Cartelera del Palafox |

### Bot de Telegram

```bash
python interfaces/bot_telegram.py
```

Comandos disponibles en el bot:

| Comando | Función |
|---|---|
| `/start` | Bienvenida y lista de comandos |
| `/pelicula Inception` | Info completa de una película |
| `/cartelera yelmo_ideal` | Cartelera de un cine |
| `/recomendaciones yelmo_ideal` | Cartelera filtrada por tu perfil |
| `/cines` | Lista de cines disponibles |
| `/ayuda` | Muestra la ayuda |

### Cartelera — cines disponibles

| Clave | Cine |
|---|---|
| `callao` | Cine Callao |
| `capitol` | Cine Capitol Gran Vía |
| `paz` | Paz |
| `palafox` | Palafox |
| `verdi` | Verdi Madrid |
| `yelmo_ideal` | Yelmo Cines Ideal |
| `renoir` | Renoir Plaza de España |
| `princesa` | Cines Princesa |

### Perfil de usuario

Edita `data/perfil.json` para personalizar el filtro:

```json
{
  "nombre": "Cinéfilo exigente",
  "nota_minima": 7.0,
  "generos": ["Action", "Drama", "Thriller", "Sci-Fi"],
  "excluir_generos": ["Horror", "Documentary"],
  "solo_con_horarios": true,
  "solo_con_nota_imdb": true
}
```

---

## Automatización — AWS Lambda + EventBridge

### Flujo completo

```
EventBridge Scheduler (cada lunes a las 9:00)
        ↓
Lambda  movieagent-cron  (cron_runner.lambda_handler)
        ↓
Scraper cartelera eCartelera + OMDb API
        ↓
Filtro por perfil de usuario (perfil.json)
        ↓
Mensaje de Telegram con recomendaciones semanales
```

### Prueba local antes de desplegar

```bash
# Simula el envío sin mandar nada a Telegram
python cron_runner.py --dry-run

# Prueba con un cine específico
python cron_runner.py --cine callao --dry-run

# Envío real a Telegram
python cron_runner.py --cine yelmo_ideal
```

### Paso 1 — Empaqueta el código para Lambda

Desde la raíz del proyecto, en Windows:

```bash
pip install requests beautifulsoup4 python-dotenv -t package/
xcopy scrapers package\scrapers\ /E /I
xcopy core package\core\ /E /I
copy cron_runner.py package\
copy data\perfil.json package\data\
cd package
tar -czf ..\cron_lambda.zip .
cd ..
```

En Linux/Mac:

```bash
pip install requests beautifulsoup4 python-dotenv -t package/
cp -r scrapers core data cron_runner.py package/
cd package && zip -r ../cron_lambda.zip . && cd ..
```

### Paso 2 — Crea la función Lambda

1. Ve a [AWS Lambda](https://console.aws.amazon.com/lambda) → **Crear función**
2. Nombre: `movieagent-cron`
3. Runtime: **Python 3.12**
4. Sube el archivo `cron_lambda.zip`
5. Handler: `cron_runner.lambda_handler`
6. Timeout: **60 segundos** (el scraping necesita tiempo)
7. Añade estas variables de entorno en la configuración:

```
OMDB_API_KEY      = tu_api_key
TELEGRAM_TOKEN    = tu_token
TELEGRAM_CHAT_ID  = tu_chat_id
CINE              = yelmo_ideal
```

### Paso 3 — Crea el horario en EventBridge Scheduler

1. Ve a [EventBridge Scheduler](https://console.aws.amazon.com/scheduler) → **Crear horario**
2. Nombre: `movieagent-lunes`
3. Tipo: **Cron-based**
4. Expresión cron — cada lunes a las 9:00 (Madrid = UTC+2, ajusta según tu zona):

```
cron(0 7 ? * MON *)
```

5. Destino: **AWS Lambda** → selecciona `movieagent-cron`
6. Payload: `{}` (vacío)
7. Permisos: deja que EventBridge cree el rol IAM automáticamente

### Paso 4 — Prueba manual desde Lambda

En la pestaña **Test** de la consola Lambda, crea un evento vacío:

```json
{}
```

Haz clic en **Test** — si todo está bien recibirás el mensaje en Telegram.

> **Coste:** Lambda free tier cubre 1 millón de invocaciones/mes. Una ejecución semanal tiene coste **cero**.
> Los logs quedan disponibles automáticamente en **CloudWatch**.

---

## Variables de entorno — resumen

| Variable | Dónde se usa | Descripción |
|---|---|---|
| `OMDB_API_KEY` | Todo el proyecto | Clave de OMDb API |
| `TELEGRAM_TOKEN` | Bot + cron_runner | Token del bot de Telegram |
| `TELEGRAM_CHAT_ID` | cron_runner | ID del chat donde enviar el resumen |
| `CINE` | cron_runner (Lambda) | Cine por defecto para el cron |

---

## Notas

- Toda la información de películas se obtiene en tiempo real via OMDb API — no hay base de datos.
- La cartelera de Madrid se obtiene por scraping de eCartelera con BeautifulSoup.
- Las peticiones a OMDb se hacen en paralelo con `ThreadPoolExecutor` para reducir el tiempo de espera.
- El perfil de usuario se define en `data/perfil.json` y es completamente configurable.
- El filtro es extensible: añadir un nuevo criterio solo requiere una función en `core/filtro.py`.