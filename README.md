# Movie Agent

Agente inteligente para obtener información de películas, con interfaz web, bot de Telegram, Alexa Skill y automatización por cron.

---

## ¿Por qué OMDb y no IMDb directamente?

IMDb pertenece a Amazon y **no ofrece una API pública gratuita estándar**. El acceso a sus datos es de pago o restringido (AWS datasets, licencias comerciales). Además, IMDb bloquea activamente cualquier intento de scraping mediante:

- **Cloudflare** — protección anti-bot a nivel de red
- **Rate limiting agresivo** — bloquea IPs que hacen demasiadas peticiones
- **Cambios frecuentes de HTML** — los selectores se rompen constantemente

**Solución: [OMDb API](https://www.omdbapi.com/)** (Open Movie Database)

OMDb es la alternativa oficial y gratuita. Expone exactamente los mismos datos de IMDb (ratings, votos, sinopsis, director, duración...) a través de una API JSON estable, sin bloqueos y sin necesidad de scraping frágil. Es gratuita hasta **1.000 peticiones/día**.

---

## Estructura del proyecto

```
movie_agent/
│
├── scrapers/
│   ├── __init__.py
│   ├── imdb_scraper.py       # Consulta datos de películas via OMDb API
│   └── cartelera_scraper.py  # Cartelera de Madrid (ecartelera)
│
├── core/
│   ├── __init__.py
│   └── filtro.py             # Filtro de películas por perfil de usuario
│
├── interfaces/
│   ├── __init__.py
│   ├── web_app.py            # Interfaz web con Flask
│   ├── bot_telegram.py       # Bot de Telegram
│   └── alexa_lambda.py       # Alexa Skill para AWS Lambda
│
├── data/
│   └── perfil.json           # Perfil de usuario con géneros y nota mínima
│
├── main.py                   # CLI: busca películas desde la terminal
├── .env                      # Variables de entorno (NO subir a git)
├── requirements.txt          # Dependencias del proyecto
└── README.md
```

---

## Instalación

### 1. Clona o descarga el proyecto

```bash
git clone <url-del-repo>
cd movie_agent
```

### 2. Crea un entorno virtual

```bash
python -m venv venv

# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 4. Consigue tu API key de OMDb (gratis)

1. Ve a [https://www.omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx)
2. Selecciona **FREE** (1.000 peticiones/día)
3. Introduce tu email y envía el formulario
4. Activa la key desde el enlace que recibirás por email

### 5. Crea el archivo `.env`

En la raíz del proyecto crea un archivo `.env` con este contenido:

```env
OMDB_API_KEY=tu_api_key_aqui
TELEGRAM_TOKEN=tu_token_aqui
```

---

## 📦 Librerías instaladas (`requirements.txt`)

| Librería | Versión | Para qué se usa |
|---|---|---|
| `requests` | 2.32.3 | Peticiones HTTP a la API de OMDb y scraping de cartelera |
| `beautifulsoup4` | 4.12.3 | Parsear HTML de ecartelera (cartelera de Madrid) |
| `flask` | 3.0.3 | Interfaz web para buscar películas |
| `python-telegram-bot` | 21.3 | Bot de Telegram |
| `ask-sdk-core` | 1.19.0 | Alexa Skill en AWS Lambda |
| `python-dotenv` | 1.0.1 | Carga `OMDB_API_KEY` y `TELEGRAM_TOKEN` desde `.env` |

> **Nota:** `lxml` fue eliminado porque no tiene wheel precompilado para Python 3.14 en Windows. BeautifulSoup usa `html.parser`, que viene integrado en Python y no requiere instalación.

---

## Uso rápido

### Buscar una película desde la terminal

```bash
python main.py "Inception"
python main.py "El Padrino" --campo nota
python main.py "Interstellar" --campo director
```

### Arrancar la interfaz web

```bash
python interfaces/web_app.py
# Abre http://localhost:5000
```

### Arrancar el bot de Telegram

```bash
python interfaces/bot_telegram.py
```

---

## ⏰ Automatización con cron

Ejecuta el scraper de cartelera cada lunes a las 9:00 y envía resultados por Telegram:

```bash
# Edita el crontab:
crontab -e

# Añade esta línea (ajusta la ruta):
0 9 * * 1 /ruta/venv/bin/python /ruta/movie_agent/main.py --cartelera >> /tmp/cartelera.log 2>&1
```

---

## Notas

- Toda la información de películas se obtiene en tiempo real via OMDb API.
- La cartelera de Madrid se obtiene por scraping de ecartelera con BeautifulSoup.
- Los perfiles de usuario se definen en `data/perfil.json`.
- No se usa ninguna base de datos: todo es JSON o estructuras en memoria.
- **Nunca subas el archivo `.env` a git.** Añádelo a `.gitignore`.



python interfaces/web_app.py
python interfaces/bot_telegram.py