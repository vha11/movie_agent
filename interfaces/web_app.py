"""
web_app.py
----------
Interfaz web con Flask para buscar películas y ver la cartelera de Madrid.

Rutas:
  GET  /                    — Página principal con buscador
  GET  /buscar?q=titulo     — Resultado de búsqueda de película
  GET  /cartelera           — Cartelera del cine por defecto
  GET  /cartelera/<cine>    — Cartelera de un cine específico

Uso:
  python interfaces/web_app.py
  Abre http://localhost:5000
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template_string, request, redirect, url_for
from scrapers.imdb_scraper import get_movie_info
from scrapers.cartelera_scraper import get_cartelera, CINES_MADRID
from core.filtro import cargar_perfil, filtrar_peliculas

app = Flask(__name__)

CINE_DEFAULT = "yelmo_ideal"

# ── HTML base (layout compartido) ─────────────────────────────────────────

BASE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MovieAgent</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #0a0a0f;
      --surface:   #13131a;
      --border:    #1e1e2e;
      --accent:    #e8b84b;
      --accent2:   #e05a2b;
      --text:      #e8e6e0;
      --muted:     #6b6975;
      --success:   #4caf82;
      --font-head: 'Bebas Neue', sans-serif;
      --font-body: 'DM Sans', sans-serif;
      --radius:    6px;
    }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-body);
      font-weight: 300;
      min-height: 100vh;
      line-height: 1.6;
    }

    /* ── Grain overlay ── */
    body::before {
      content: '';
      position: fixed; inset: 0;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
      pointer-events: none; z-index: 0;
    }

    /* ── Header ── */
    header {
      border-bottom: 1px solid var(--border);
      padding: 1.2rem 2rem;
      display: flex;
      align-items: center;
      gap: 2rem;
      position: sticky; top: 0;
      background: rgba(10,10,15,0.92);
      backdrop-filter: blur(12px);
      z-index: 100;
    }

    .logo {
      font-family: var(--font-head);
      font-size: 1.8rem;
      letter-spacing: 3px;
      color: var(--accent);
      text-decoration: none;
      white-space: nowrap;
    }

    .logo span { color: var(--accent2); }

    /* ── Search bar ── */
    .search-form {
      display: flex;
      flex: 1;
      max-width: 520px;
      gap: 0;
    }

    .search-form input {
      flex: 1;
      background: var(--surface);
      border: 1px solid var(--border);
      border-right: none;
      color: var(--text);
      padding: 0.55rem 1rem;
      font-family: var(--font-body);
      font-size: 0.95rem;
      border-radius: var(--radius) 0 0 var(--radius);
      outline: none;
      transition: border-color 0.2s;
    }

    .search-form input:focus { border-color: var(--accent); }
    .search-form input::placeholder { color: var(--muted); }

    .search-form button {
      background: var(--accent);
      color: #0a0a0f;
      border: none;
      padding: 0.55rem 1.2rem;
      font-family: var(--font-head);
      font-size: 1rem;
      letter-spacing: 1px;
      cursor: pointer;
      border-radius: 0 var(--radius) var(--radius) 0;
      transition: background 0.2s;
    }

    .search-form button:hover { background: #f5c85a; }

    nav { margin-left: auto; display: flex; gap: 1.5rem; }
    nav a {
      color: var(--muted);
      text-decoration: none;
      font-size: 0.85rem;
      letter-spacing: 1px;
      text-transform: uppercase;
      transition: color 0.2s;
    }
    nav a:hover, nav a.active { color: var(--accent); }

    /* ── Main ── */
    main {
      position: relative; z-index: 1;
      max-width: 1100px;
      margin: 0 auto;
      padding: 2.5rem 2rem;
    }

    /* ── Hero (home) ── */
    .hero {
      text-align: center;
      padding: 5rem 1rem 4rem;
    }

    .hero h1 {
      font-family: var(--font-head);
      font-size: clamp(3.5rem, 10vw, 8rem);
      letter-spacing: 8px;
      line-height: 1;
      color: var(--text);
    }

    .hero h1 span { color: var(--accent); }

    .hero p {
      margin: 1.2rem auto 2.5rem;
      max-width: 460px;
      color: var(--muted);
      font-size: 1rem;
    }

    .hero .search-form {
      max-width: 500px;
      margin: 0 auto;
    }

    /* ── Section title ── */
    .section-title {
      font-family: var(--font-head);
      font-size: 2rem;
      letter-spacing: 4px;
      color: var(--text);
      margin-bottom: 0.3rem;
    }

    .section-sub {
      color: var(--muted);
      font-size: 0.85rem;
      margin-bottom: 2rem;
      letter-spacing: 1px;
      text-transform: uppercase;
    }

    /* ── Movie card (resultado búsqueda) ── */
    .movie-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 2rem;
      animation: fadeIn 0.4s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(12px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .movie-badge {
      background: var(--accent);
      color: #0a0a0f;
      font-family: var(--font-head);
      font-size: 2.8rem;
      letter-spacing: 2px;
      padding: 1rem 1.5rem;
      border-radius: var(--radius);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-width: 100px;
      text-align: center;
      line-height: 1.1;
    }

    .movie-badge small {
      font-family: var(--font-body);
      font-size: 0.65rem;
      font-weight: 500;
      letter-spacing: 2px;
      text-transform: uppercase;
      opacity: 0.7;
    }

    .movie-info h2 {
      font-family: var(--font-head);
      font-size: 2.2rem;
      letter-spacing: 3px;
      color: var(--text);
      line-height: 1.1;
    }

    .movie-info .year {
      color: var(--accent);
      font-size: 1rem;
      font-weight: 500;
      margin-bottom: 1rem;
    }

    .meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 1rem;
      margin: 1.2rem 0;
    }

    .meta-item label {
      display: block;
      color: var(--muted);
      font-size: 0.7rem;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-bottom: 0.2rem;
    }

    .meta-item span {
      color: var(--text);
      font-size: 0.95rem;
      font-weight: 400;
    }

    .sinopsis {
      color: #b0adb8;
      font-size: 0.92rem;
      line-height: 1.7;
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
    }

    .imdb-link {
      display: inline-block;
      margin-top: 1.2rem;
      color: var(--accent);
      text-decoration: none;
      font-size: 0.8rem;
      letter-spacing: 2px;
      text-transform: uppercase;
      border-bottom: 1px solid transparent;
      transition: border-color 0.2s;
    }

    .imdb-link:hover { border-color: var(--accent); }

    /* ── Cartelera grid ── */
    .cine-nav {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 2rem;
    }

    .cine-btn {
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--muted);
      padding: 0.4rem 0.9rem;
      border-radius: 2rem;
      font-family: var(--font-body);
      font-size: 0.8rem;
      letter-spacing: 1px;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s;
    }

    .cine-btn:hover, .cine-btn.active {
      border-color: var(--accent);
      color: var(--accent);
      background: rgba(232,184,75,0.08);
    }

    .cartelera-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1.2rem;
    }

    .peli-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.4rem;
      transition: border-color 0.2s, transform 0.2s;
      animation: fadeIn 0.4s ease both;
    }

    .peli-card:hover {
      border-color: var(--accent);
      transform: translateY(-2px);
    }

    .peli-card h3 {
      font-family: var(--font-head);
      font-size: 1.3rem;
      letter-spacing: 2px;
      color: var(--text);
      margin-bottom: 0.2rem;
      line-height: 1.2;
    }

    .peli-card .peli-meta {
      display: flex;
      gap: 0.8rem;
      align-items: center;
      margin: 0.6rem 0;
      flex-wrap: wrap;
    }

    .tag {
      background: rgba(232,184,75,0.1);
      color: var(--accent);
      border: 1px solid rgba(232,184,75,0.2);
      padding: 0.15rem 0.55rem;
      border-radius: 2rem;
      font-size: 0.72rem;
      letter-spacing: 1px;
      white-space: nowrap;
    }

    .tag.verde {
      background: rgba(76,175,130,0.1);
      color: var(--success);
      border-color: rgba(76,175,130,0.2);
    }

    .tag.gris {
      background: rgba(107,105,117,0.1);
      color: var(--muted);
      border-color: rgba(107,105,117,0.2);
    }

    .peli-director {
      color: var(--muted);
      font-size: 0.82rem;
      margin-top: 0.4rem;
    }

    .horarios {
      margin-top: 0.8rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }

    .horario-badge {
      background: var(--border);
      color: var(--text);
      padding: 0.2rem 0.6rem;
      border-radius: 3px;
      font-size: 0.8rem;
      font-weight: 500;
      letter-spacing: 1px;
    }

    /* ── Error / empty ── */
    .error-box, .empty-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 2.5rem;
      text-align: center;
      color: var(--muted);
    }

    .error-box { border-color: var(--accent2); }
    .error-box strong { color: var(--accent2); display: block; font-size: 1.2rem; margin-bottom: 0.5rem; }

    /* ── Footer ── */
    footer {
      position: relative; z-index: 1;
      border-top: 1px solid var(--border);
      padding: 1.5rem 2rem;
      text-align: center;
      color: var(--muted);
      font-size: 0.78rem;
      letter-spacing: 1px;
    }

    @media (max-width: 600px) {
      .movie-card { grid-template-columns: 1fr; }
      .movie-badge { flex-direction: row; gap: 0.5rem; min-width: auto; padding: 0.8rem 1rem; }
      header { flex-wrap: wrap; }
      nav { display: none; }
    }
  </style>
</head>
<body>

<header>
  <a href="/" class="logo">MOVIE<span>AGENT</span></a>
  <form class="search-form" action="/buscar" method="get">
    <input type="text" name="q" placeholder="Buscar película..." autocomplete="off" value="{{ query|default('') }}">
    <button type="submit">BUSCAR</button>
  </form>
  <nav>
    <a href="/" {% if active == 'home' %}class="active"{% endif %}>Inicio</a>
    <a href="/cartelera" {% if active == 'cartelera' %}class="active"{% endif %}>Cartelera</a>
  </nav>
</header>

<main>
  {% block content %}{% endblock %}
</main>

<footer>
  MOVIEAGENT — Datos de OMDb API &amp; eCartelera
</footer>

</body>
</html>
"""

# ── Templates de páginas ───────────────────────────────────────────────────

HOME_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
<div class="hero">
  <h1>MOVIE<span>AGENT</span></h1>
  <p>Busca cualquier película o consulta la cartelera de Madrid</p>
  <form class="search-form" action="/buscar" method="get">
    <input type="text" name="q" placeholder="Ej: Inception, El Padrino..." autocomplete="off" autofocus>
    <button type="submit">BUSCAR</button>
  </form>
</div>
""")

RESULTADO_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
{% if error %}
  <div class="error-box">
    <strong>No encontrado</strong>
    {{ error }}
  </div>
{% else %}
  <div class="movie-card">
    <div class="movie-badge">
      {{ info.nota }}
      <small>IMDb</small>
    </div>
    <div class="movie-info">
      <h2>{{ info.titulo }}</h2>
      <div class="year">{{ info.anio }} &nbsp;·&nbsp; {{ info.duracion }}</div>
      <div class="meta-grid">
        <div class="meta-item">
          <label>Género</label>
          <span>{{ info.genero }}</span>
        </div>
        <div class="meta-item">
          <label>Director</label>
          <span>{{ info.director }}</span>
        </div>
        <div class="meta-item">
          <label>Votos IMDb</label>
          <span>{{ info.votos }}</span>
        </div>
      </div>
      <div class="sinopsis">{{ info.sinopsis }}</div>
      {% if info.url and info.url != 'N/A' %}
        <a href="{{ info.url }}" target="_blank" class="imdb-link">Ver en IMDb →</a>
      {% endif %}
    </div>
  </div>
{% endif %}
""")

CARTELERA_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
<div class="section-title">CARTELERA MADRID</div>
<div class="section-sub">{{ cine_actual.upper() }} — {{ peliculas|length }} películas hoy</div>

<div class="cine-nav">
  {% for clave in cines %}
    <a href="/cartelera/{{ clave }}"
       class="cine-btn {% if clave == cine_actual %}active{% endif %}">
      {{ clave.replace('_', ' ') }}
    </a>
  {% endfor %}
</div>

{% if error %}
  <div class="error-box"><strong>Error</strong>{{ error }}</div>
{% elif not peliculas %}
  <div class="empty-box">No se encontraron películas para este cine hoy.</div>
{% else %}
  <div class="cartelera-grid">
    {% for p in peliculas %}
      <div class="peli-card" style="animation-delay: {{ loop.index0 * 0.05 }}s">
        <h3>{{ p.titulo_es }}</h3>
        <div class="peli-meta">
          {% if p.nota_imdb and p.nota_imdb != 'N/A' %}
            <span class="tag verde">⭐ {{ p.nota_imdb }}</span>
          {% endif %}
          {% if p.nota_ec and p.nota_ec != 'N/A' %}
            <span class="tag">eC {{ p.nota_ec }}</span>
          {% endif %}
          {% if p.anio and p.anio != 'N/A' %}
            <span class="tag gris">{{ p.anio }}</span>
          {% endif %}
          {% if p.duracion and p.duracion != 'N/A' %}
            <span class="tag gris">{{ p.duracion }}</span>
          {% endif %}
        </div>
        {% if p.genero and p.genero != 'N/A' %}
          <div class="peli-director">{{ p.genero }}</div>
        {% endif %}
        {% if p.director and p.director != 'N/A' %}
          <div class="peli-director">{{ p.director }}</div>
        {% endif %}
        {% if p.horarios %}
          <div class="horarios">
            {% for h in p.horarios %}
              <span class="horario-badge">{{ h }}</span>
            {% endfor %}
          </div>
        {% endif %}
      </div>
    {% endfor %}
  </div>
{% endif %}
""")


# ── Rutas Flask ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HOME_HTML, active="home", query="")


@app.route("/buscar")
def buscar():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("index"))

    info = get_movie_info(query)
    error = info.get("error") if "error" in info else None

    return render_template_string(
        RESULTADO_HTML,
        active="home",
        query=query,
        info=info,
        error=error,
    )


@app.route("/cartelera")
@app.route("/cartelera/<cine>")
def cartelera(cine=CINE_DEFAULT):
    cine = cine.lower()
    if cine not in CINES_MADRID:
        cine = CINE_DEFAULT

    peliculas = get_cartelera(cine, enriquecer=True)
    error = None

    if peliculas and "error" in peliculas[0]:
        error = peliculas[0]["error"]
        peliculas = []

    return render_template_string(
        CARTELERA_HTML,
        active="cartelera",
        query="",
        cine_actual=cine,
        cines=list(CINES_MADRID.keys()),
        peliculas=peliculas,
        error=error,
    )


# ── Arranque ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nMovieAgent Web — http://localhost:5000\n")
    app.run(debug=True, port=5000)