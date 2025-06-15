# -*- coding: utf-8 -*-
import os
import io
import json
import zipfile
import logging
from datetime import datetime
from flask import (
    Flask, render_template_string, request, redirect, url_for,
    session, send_from_directory, send_file, abort, flash
)
from werkzeug.utils import secure_filename

# ----------------------------------------
# Configuration de base et chemins persistants
# ----------------------------------------

# Variables d'environnement facultatives pour personnaliser les chemins persistants
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
MSG_FILE = os.environ.get("MSG_FILE_PATH", os.path.join(UPLOAD_FOLDER, "messages.json"))
TRAFFIC_FILE = os.environ.get("TRAFFIC_FILE_PATH", os.path.join(UPLOAD_FOLDER, "traffic.json"))
ROTATOR_FILE = os.environ.get("ROTATOR_FILE_PATH", os.path.join(UPLOAD_FOLDER, "rotator.json"))
CONFIG_FILE = os.environ.get("CONFIG_FILE_PATH", os.path.join(UPLOAD_FOLDER, "config.json"))

# Créer le dossier d'uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# S'assurer que les répertoires contenant les fichiers JSON existent
for path in [MSG_FILE, TRAFFIC_FILE, ROTATOR_FILE, CONFIG_FILE]:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

# Extensions autorisées pour upload
ALLOWED_EXTENSIONS = {"pdf", "dwg", "rvt", "docx", "xlsx", "jpg", "jpeg", "png", "gif", "zip"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
PDF_EXTENSIONS = {"pdf"}

# Taille maximale pour upload (optionnel) : ici pas défini, mais tu peux configurer via Flask config si souhaité
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # ex. 16 MB

# ----------------------------------------
# Configuration Flask et logs
# ----------------------------------------
app = Flask(__name__)
# En production, définir SECRET_KEY via variable d'environnement pour sécurité
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_2024")

# Fichier de logs
LOG_FILE = os.environ.get("LOG_FILE_PATH", "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# ----------------------------------------
# Fonctions utilitaires
# ----------------------------------------
def allowed_file(filename):
    """Vérifie l'extension autorisée pour upload."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_json_file(path):
    """
    Charge un JSON. Retourne dict ou list selon le contenu, ou initialise s'il n'existe pas ou erreur.
    - Si c'est config (config.json), on attend un dict.
    - Pour les autres (messages, traffic, rotator), on attend une list.
    """
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # On ne valide pas strictement la structure, mais on réinitialise si type inattendu
                if path.endswith("config.json"):
                    if isinstance(data, dict):
                        return data
                    else:
                        logging.warning(f"{path} n'est pas un dict JSON, réinitialisation.")
                else:
                    if isinstance(data, list):
                        return data
                    else:
                        logging.warning(f"{path} ne contient pas une liste JSON, réinitialisation.")
        except Exception as e:
            logging.error(f"Erreur lecture {path}: {e}. Réinitialisation.")
    # Initialisation
    default = {} if path.endswith("config.json") else []
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erreur création initiale de {path}: {e}")
    return default

def save_json_file(path, data):
    """Sauvegarde data (dict ou list) dans JSON, avec indentation pour lisibilité."""
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erreur écriture {path}: {e}")

# ----------------------------------------
# Chargement persistant au démarrage
# ----------------------------------------
# Messages reçus via formulaire
MSGS = load_json_file(MSG_FILE)
if isinstance(MSGS, list):
    for m in MSGS:
        if 'status' not in m: m['status'] = 'new'
        if 'timestamp' not in m: m['timestamp'] = ""
else:
    MSGS = []

# Traffic logs
TRAFFIC = load_json_file(TRAFFIC_FILE)
if not isinstance(TRAFFIC, list):
    TRAFFIC = []

# Carousel items
ROTATOR_ITEMS = load_json_file(ROTATOR_FILE)
if not isinstance(ROTATOR_ITEMS, list):
    ROTATOR_ITEMS = []

# Configuration thème (couleur, font, photo)
config_theme = load_json_file(CONFIG_FILE)
# Valeurs par défaut si absentes
default_color = "#1f87e0"
default_font = "Montserrat"
# Pour la photo de profil, on peut avoir :
# - une URL externe (commençant par http:// ou https://)
# - ou un chemin relatif vers uploads, p.ex. "/uploads/filename.jpg"
default_photo = "https://randomuser.me/api/portraits/men/75.jpg"
theme_color = config_theme.get("couleur", default_color)
theme_font = config_theme.get("font", default_font)
theme_photo = config_theme.get("photo", default_photo)

# ----------------------------------------
# Données dynamiques du site
# ----------------------------------------
SITE = {
    "nom": "Issoufou Abdou Chefou",
    "titre": {
        "fr": "Ingénieur en Génie Civil & BIM | Freelance",
        "en": "Civil Engineer & BIM Specialist | Freelancer"
    },
    "slogan": {
        "fr": "Vous avez un projet ? Confiez-le à un professionnel passionné.",
        "en": "Have a project? Entrust it to a passionate expert."
    },
    # Photo de profil : si URL externe, on utilise directement ; si chemin relatif (ex. "/uploads/xxx.jpg"), il faut que la route /uploads/<filename> serve le fichier
    "photo": theme_photo,
    "email": "entreprise2rc@gmail.com",
    "tel": "+227 96 38 08 77",
    "whatsapp": "+227 96 38 08 77",
    "linkedin": "https://www.linkedin.com/in/issoufou-chefou",
    "adresse": {
        "fr": "Niamey, Niger (disponible à l'international)",
        "en": "Niamey, Niger (available internationally)"
    },
    "horaires": {
        "fr": "Lundi–Samedi : 8h – 19h (GMT+1)",
        "en": "Monday–Saturday: 8AM – 7PM (GMT+1)"
    },
    "couleur": theme_color,
    "font": theme_font
}
ANNEE = 2025

# Exemple de services, portfolio, atouts (à personnaliser selon besoin)
SERVICES = [
    {"titre": {"fr": "Plans d’armatures Revit", "en": "Rebar plans (Revit)"},
     "desc": {"fr": "Plans d’armatures clairs et complets pour béton armé.",
              "en": "Clear, complete rebar plans for reinforced concrete."},
     "icon": "bi-diagram-3"},
    {"titre": {"fr": "Études et plans métalliques", "en": "Steel structure studies & plans"},
     "desc": {"fr": "Calculs et plans pour charpentes, hangars, structures métalliques.",
              "en": "Design & drawings for steel frames, hangars, metal structures."},
     "icon": "bi-building"},
    {"titre": {"fr": "Modélisation BIM complète", "en": "Complete BIM modeling"},
     "desc": {"fr": "Maquettes numériques, familles paramétriques, coordination.",
              "en": "Digital models, parametric families, project coordination."},
     "icon": "bi-boxes"},
    {"titre": {"fr": "Audit et optimisation", "en": "Audit & optimization"},
     "desc": {"fr": "Vérification, corrections et conseils pour réduire coûts/risques.",
              "en": "Checks, corrections, advice to reduce cost & risks."},
     "icon": "bi-search"},
    {"titre": {"fr": "Formation/Accompagnement", "en": "Training/Support"},
     "desc": {"fr": "Formation Revit ou support ponctuel pour vos équipes.",
              "en": "Revit training or support for your team."},
     "icon": "bi-person-video3"},
]

PORTFOLIO = [
    {
        "titre": {"fr": "Résidence de standing (Niamey)", "en": "Premium Residence (Niamey)"},
        "desc": {
            "fr": "Plans de coffrage et ferraillage, modélisation Revit, synthèse et quantitatifs.",
            "en": "Formwork and rebar plans, Revit modeling, syntheses and BOQs."
        },
        "imgs": ["https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=600&q=80"],
        "fichiers": []
    }
]

ATOUTS = [
    {"fr": "7 ans d’expérience sur des projets variés en Afrique et à l’international.",
     "en": "7 years of experience with varied projects in Africa and abroad."},
    {"fr": "Maîtrise avancée de Revit, AutoCAD, Robot Structural Analysis.",
     "en": "Advanced skills in Revit, AutoCAD, Robot Structural Analysis."},
    {"fr": "Réactivité : réponse à toutes demandes en moins de 24h.",
     "en": "Responsive: answers to all requests in less than 24h."},
    {"fr": "Travail 100% à distance, process sécurisé, confidentialité garantie.",
     "en": "100% remote work, secured process, guaranteed confidentiality."},
    {"fr": "Respect total des délais et adaptation à vos besoins spécifiques.",
     "en": "Strict respect for deadlines, adaptable to your needs."},
    {"fr": "Conseils gratuits avant devis : je vous oriente même sans plans précis.",
     "en": "Free advice before any quote, even if you don’t have precise plans."},
]

# ----------------------------------------
# Configuration admin
# ----------------------------------------
ADMIN_USER = os.environ.get("ADMIN_USER", "bacseried@gmail.com")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "mx23fy")
ADMIN_SECRET_URL = os.environ.get("ADMIN_SECRET_URL", "issoufouachraf_2025")
LANGS = {"fr": "Français", "en": "English"}

def send_email_notification(subject: str, body: str):
    """Stub: enregistre seulement dans les logs."""
    logging.info(f"[Notification stub] Sujet: {subject} | Corps: {body}")

# ----------------------------------------
# Template HTML de base (BASE)
# ----------------------------------------
# On inclut ici CSS/JS Bootstrap, Google Fonts dynamiques, et styles personnalisés pour rendre le site plus attrayant :
BASE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <title>{{ titre_page or 'Accueil' }} | {{ site.nom }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Google Font dynamique -->
    <link href="https://fonts.googleapis.com/css2?family={{ site.font|replace(' ','+') }}:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        /* Variables CSS dynamiques */
        :root {
            --primary-color: {{ site.couleur }};
            --font-family: '{{ site.font }}', Arial, sans-serif;
        }
        html { font-size: 17px; scroll-behavior: smooth; }
        body {
            font-family: var(--font-family);
            background: {% if session.get('dark_mode') %}#121212{% else %}#f6faff{% endif %};
            color: {% if session.get('dark_mode') %}#e0e0e0{% else %}#212529{% endif %};
            margin: 0; padding: 0;
            transition: background 0.3s, color 0.3s;
        }
        a {
            color: var(--primary-color);
            text-decoration: none;
            transition: color 0.2s;
        }
        a:hover {
            color: darken(var(--primary-color), 10%) !important;
            text-decoration: underline;
        }
        /* Navbar */
        .navbar {
            background: linear-gradient(90deg, var(--primary-color), #43e3ff 100%);
            transition: background 0.3s;
        }
        .navbar-brand, .nav-link { color: #fff !important; }
        .nav-link.active { color: #ffd600!important; font-weight:bold; }
        .lang-select { margin-left:1.1em; }
        .dark-toggle { cursor: pointer; color: #fff; margin-left: 1rem; }

        /* Hero avec image de profil ou background léger */
        .hero {
            position: relative;
            text-align: center;
            color: #fff;
            padding: 60px 0;
            background: 
                linear-gradient(rgba(0,0,0,0.4), rgba(0,0,0,0.4)),
                url('{{ site.photo }}') center/cover no-repeat;
        }
        .hero img {
            width: 140px; height:140px; object-fit:cover;
            border-radius: 50%;
            border: 3px solid #ffd600;
            box-shadow: 0 4px 16px rgba(0,0,0,0.6);
            transition: transform 0.3s;
        }
        .hero img:hover {
            transform: scale(1.05);
        }
        .hero h1, .hero h3, .hero p {
            text-shadow: 1px 1px 6px rgba(0,0,0,0.7);
            margin: 10px 0;
        }
        .hero .btn-contact {
            border-radius: 30px;
            padding: 12px 30px;
            font-size: 1.1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .hero .btn-contact:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }

        /* Carousel d'accueil */
        .carousel-item {
            text-align: center;
        }
        .carousel-item img {
            max-height: 400px;
            width: auto;
            margin-left: auto;
            margin-right: auto;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }
        .carousel-item img:hover {
            transform: scale(1.02);
        }
        .carousel-item .pdf-embed {
            max-width: 80%;
            height: 400px;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid #ccc;
            border-radius: 8px;
        }
        .carousel-caption {
            background: rgba(0,0,0,0.4);
            border-radius: 10px;
            padding: 10px;
        }

        /* Boutons globaux */
        .btn-contact, .btn-projet, .btn-admin {
            background: var(--primary-color);
            color: #fff;
            font-weight: 500;
            border-radius: 25px;
            transition: background 0.2s, transform 0.2s;
        }
        .btn-contact:hover, .btn-projet:hover, .btn-admin:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }

        /* Section titles */
        .section-title {
            color: var(--primary-color);
            margin-top: 32px;
            margin-bottom: 24px;
            font-weight: 600;
            letter-spacing: 0.5px;
            position: relative;
            display: inline-block;
        }
        .section-title::after {
            content: "";
            display: block;
            width: 60px;
            height: 3px;
            background: var(--primary-color);
            margin: 8px auto 0;
            border-radius: 2px;
        }

        /* Service cards */
        .service-card {
            background: {% if session.get('dark_mode') %}#1e1e1e{% else %}#fff{% endif %};
            border-radius:20px;
            padding:24px 16px;
            text-align:center;
            margin-bottom:20px;
            box-shadow:0 2px 14px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .service-card:hover {
            transform: translateY(-6px);
            box-shadow:0 6px 24px rgba(0,0,0,0.15);
        }
        .service-card i {
            font-size:2.4rem;
            color: var(--primary-color);
            margin-bottom:12px;
        }

        /* Portfolio cards */
        .card-portfolio {
            border: none;
            border-radius: 15px;
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
            background: {% if session.get('dark_mode') %}#1e1e1e{% else %}#fff{% endif %};
            color: {% if session.get('dark_mode') %}#e0e0e0{% else %}#212529{% endif %};
            box-shadow:0 2px 12px rgba(0,0,0,0.1);
        }
        .card-portfolio:hover {
            transform: translateY(-6px);
            box-shadow:0 8px 28px rgba(0,0,0,0.2);
        }
        .portfolio-img-multi {
            height:70px; width:90px; object-fit:cover;
            margin-right:8px; margin-bottom:6px; border-radius:8px; border:2px solid #eee;
            transition: transform 0.2s;
        }
        .portfolio-img-multi:hover {
            transform: scale(1.05);
        }

        /* Footer */
        .footer { background: #222c41; color: #fff; padding: 30px 0; margin-top: 0; }
        .footer a { color: #ffd600; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }

        .project-cta {
            background: linear-gradient(90deg,var(--primary-color) 60%, #ffd600 120%);
            color:#24315e;
            border-radius:20px;
            padding:25px 15px;
            margin:30px 0 15px 0;
            box-shadow:0 4px 16px rgba(0,0,0,0.15);
            font-size:1.1rem;
            font-weight:500;
            text-align: center;
        }

        /* Admin panel */
        .admin-nav { background:#2c2f33; padding:10px; border-radius:10px; margin-bottom:10px; }
        .admin-nav a { color:#ffd600; margin:0 8px; font-weight:bold; }
        .admin-panel {
            background:{% if session.get('dark_mode') %}#1e1e1e{% else %}#fff{% endif %};
            border-radius:14px;
            padding:20px 16px;
            margin-top:10px;
            box-shadow:0 4px 24px rgba(0,0,0,0.1);
            color: {% if session.get('dark_mode') %}#e0e0e0{% else %}#212529{% endif %};
        }
        .admin-table td, .admin-table th { vertical-align:middle; color: inherit; }
        .admin-msg { background:#fffae0; border:1px solid var(--primary-color); border-radius:8px; padding:12px 18px; }

        /* Contact form drag-drop */
        .drag-drop-area {
            border:2px dashed #bbb;
            border-radius:10px;
            background:#f8fbff;
            text-align:center;
            padding:20px 8px;
            color:#789;
            margin-bottom:12px;
            transition: border .2s, background .2s;
        }
        .drag-drop-area.dragover { border:2.2px solid var(--primary-color); background:#e7f7ff; }

        /* Table warning for unread */
        .table-warning { background-color: #fff3cd !important; }

        @media (max-width:600px) {
            html { font-size:15px; }
            .hero, .carousel { padding: 40px 0 30px 0; }
            .project-cta { padding:10px 5px; }
            .admin-panel { padding:10px 8px; }
            .carousel-item img, .carousel-item .pdf-embed {
                max-height: 250px;
                height: auto;
            }
            .hero img { width: 100px; height:100px; }
        }

        /* Petite fonction CSS pour assombrir la couleur (darken) */
        /* Note: Bootstrap n'a pas de fonction darken native dans CSS pur; 
           Mais certains navigateurs peuvent interpréter color-mod ou filter. 
           Pour simplicité, dans ce template, les hover plus sombres ne sont pas strictement calculés ici. */
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg sticky-top">
  <div class="container">
    <a class="navbar-brand" href="{{ url_for('index') }}">{{ site.nom }}</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav">
      <span class="navbar-toggler-icon" style="color:#fff;"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-auto align-items-center">
        <li class="nav-item"><a class="nav-link {% if page=='accueil' %}active{% endif %}" href="{{ url_for('index') }}">{{ "Accueil" if lang=='fr' else "Home" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if page=='services' %}active{% endif %}" href="{{ url_for('services') }}">{{ "Services" if lang=='fr' else "Services" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if page=='portfolio' %}active{% endif %}" href="{{ url_for('portfolio') }}">{{ "Portfolio" if lang=='fr' else "Portfolio" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if page=='pourquoi' %}active{% endif %}" href="{{ url_for('pourquoi') }}">{{ "Pourquoi moi ?" if lang=='fr' else "Why me?" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if page=='contact' %}active{% endif %}" href="{{ url_for('contact') }}">{{ "Contact / Projets" if lang=='fr' else "Contact / Project" }}</a></li>
        <li class="nav-item lang-select">
          <form method="post" action="{{ url_for('set_lang') }}" style="display:inline;">
            <select name="lang" onchange="this.form.submit()" class="form-select form-select-sm" style="display:inline;width:96px;">
              {% for code, name in langs.items() %}
                <option value="{{ code }}" {% if lang==code %}selected{% endif %}>{{ name }}</option>
              {% endfor %}
            </select>
          </form>
        </li>
        <li class="nav-item">
          <a href="{{ url_for('toggle_dark') }}" class="dark-toggle" title="{{ 'Mode sombre' if not session.get('dark_mode') else 'Mode clair' }}">
            {% if session.get('dark_mode') %}
              <i class="bi bi-sun-fill"></i>
            {% else %}
              <i class="bi bi-moon-fill"></i>
            {% endif %}
          </a>
        </li>
      </ul>
    </div>
  </div>
</nav>
<div class="container py-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
            {{ msg }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
<footer class="footer text-center">
  <div class="container">
    <div class="row">
      <div class="col-md-4 mb-3">
        <strong>{{ site.nom }}</strong><br>{{ site.titre[lang] }}
      </div>
      <div class="col-md-4 mb-3">
        <i class="bi bi-geo-alt-fill"></i> {{ site.adresse[lang] }}<br>
        <i class="bi bi-clock-fill"></i> {{ site.horaires[lang] }}
      </div>
      <div class="col-md-4 mb-3">
        <i class="bi bi-envelope-fill"></i> <a href="mailto:{{ site.email }}">{{ site.email }}</a><br>
        <i class="bi bi-whatsapp"></i> <a href="https://wa.me/{{ site.whatsapp.replace(' ','').replace('+','') }}" target="_blank">{{ site.whatsapp }}</a><br>
        <i class="bi bi-linkedin"></i> <a href="{{ site.linkedin }}" target="_blank">LinkedIn</a>
      </div>
    </div>
    <div class="mt-2 small">&copy; {{ annee }} – {{ "Développé par" if lang=='fr' else "Developed by" }} {{ site.nom }}</div>
  </div>
</footer>
<!-- Bootstrap JS et dépendances -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
// Gestion drag & drop pour contact
const dropArea = document.getElementById('dragDrop');
if (dropArea) {
  dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.classList.add('dragover'); });
  dropArea.addEventListener('dragleave', (e) => { dropArea.classList.remove('dragover'); });
  dropArea.addEventListener('drop', (e) => {
    e.preventDefault(); dropArea.classList.remove('dragover');
    let input = document.getElementById('fichier');
    input.files = e.dataTransfer.files;
    let list = document.getElementById('fileList');
    list.innerHTML = "";
    for (let i = 0; i < input.files.length; i++) {
        let file = input.files[i];
        let li = document.createElement('li');
        li.textContent = file.name;
        list.appendChild(li);
    }
  });
  document.getElementById('fichier').addEventListener('change', function(){
    let list = document.getElementById('fileList'); list.innerHTML = "";
    for (let i = 0; i < this.files.length; i++) {
        let file = this.files[i];
        let li = document.createElement('li'); li.textContent = file.name;
        list.appendChild(li);
    }
  });
}
</script>
</body>
</html>
"""

# ----------------------------------------
# Fonctions Flask utilitaires
# ----------------------------------------
def get_lang():
    lang = session.get('lang', 'fr')
    if lang not in LANGS:
        lang = 'fr'
    return lang

def render(content, **kwargs):
    """Rendu du template de base en injectant SITE, annee, lang, etc."""
    lang = get_lang()
    ctx = dict(site=SITE, annee=ANNEE, lang=lang, langs=LANGS, **kwargs)
    # Insérer content à la place du block content
    page = BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, **ctx)

def admin_logged_in():
    return session.get("admin") is True

@app.route('/toggle_dark')
def toggle_dark():
    current = session.get('dark_mode', False)
    session['dark_mode'] = not current
    ref = request.referrer or url_for('index')
    return redirect(ref)

@app.before_request
def log_traffic():
    path = request.path or ""
    ignore_prefixes = [f"/{ADMIN_SECRET_URL}", "/static", "/favicon.ico", "/sitemap.xml"]
    if any(path.startswith(pref) for pref in ignore_prefixes):
        return
    if request.method in ("GET", "POST"):
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "path": path,
            "method": request.method,
            "remote_addr": request.remote_addr or ""
        }
        TRAFFIC.append(entry)
        save_json_file(TRAFFIC_FILE, TRAFFIC)

# ----------------------------------------
# Routes publiques
# ----------------------------------------
@app.route('/set_lang', methods=["POST"])
def set_lang():
    lang = request.form.get("lang", 'fr')
    if lang in LANGS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    lang = get_lang()
    carousel_content = ""
    if ROTATOR_ITEMS:
        # Construire carousel Bootstrap
        carousel_content += """
        <div id="homepageCarousel" class="carousel slide mb-4" data-bs-ride="carousel" data-bs-interval="5000">
          <div class="carousel-indicators">
        """
        for idx in range(len(ROTATOR_ITEMS)):
            active = "active" if idx == 0 else ""
            aria_current = ' aria-current="true"' if idx == 0 else ""
            carousel_content += f'<button type="button" data-bs-target="#homepageCarousel" data-bs-slide-to="{idx}" class="{active}"{aria_current} aria-label="Slide {idx+1}"></button>'
        carousel_content += "</div><div class=\"carousel-inner\">"
        for idx, item in enumerate(ROTATOR_ITEMS):
            active = "active" if idx == 0 else ""
            filename = item.get("filename")
            ftype = item.get("type")
            file_url = url_for('uploaded_file', filename=filename)
            carousel_content += f'<div class="carousel-item {active}">'
            if ftype == "image":
                carousel_content += f'<img src="{file_url}" class="d-block" alt="Carousel image {idx+1}">'
            elif ftype == "pdf":
                carousel_content += f'''
                <div class="d-flex justify-content-center">
                  <object data="{file_url}" type="application/pdf" class="pdf-embed">
                    <p>Votre navigateur ne supporte pas l'affichage intégré du PDF.
                       <a href="{file_url}" target="_blank">Télécharger le PDF</a>.</p>
                  </object>
                </div>
                '''
            carousel_content += "</div>"
        carousel_content += """
          <button class="carousel-control-prev" type="button" data-bs-target="#homepageCarousel" data-bs-slide="prev">
            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Précédent</span>
          </button>
          <button class="carousel-control-next" type="button" data-bs-target="#homepageCarousel" data-bs-slide="next">
            <span class="carousel-control-next-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Suivant</span>
          </button>
        </div>
        """
    content = f"""
    {carousel_content}
    <div class="hero text-center">
      <div class="hero-content">
        <img src="{{{{ site.photo }}}}" alt="portrait {{{{ site.nom }}}}">
        <h1 class="mt-3">{{{{ site.nom }}}}</h1>
        <h3 class="mb-3">{{{{ site.titre[lang] }}}}</h3>
        <p class="lead">{{{{ site.slogan[lang] }}}}</p>
        <a href="{{{{ url_for('contact') }}}}" class="btn btn-contact btn-lg mt-3"><i class="bi bi-chat-left-dots"></i> {('Proposez votre projet' if lang=='fr' else 'Submit your project')}</a>
      </div>
    </div>
    <div class="project-cta text-center">
      <i class="bi bi-lightbulb"></i> {('Votre projet mérite un expert passionné !' if lang=='fr' else 'Your project deserves a passionate expert!')}
    </div>
    """
    return render(content, page="accueil", titre_page=("Accueil" if lang=="fr" else "Home"))

@app.route('/services')
def services():
    lang = get_lang()
    content = """
    <h2 class="section-title text-center">{{ "Mes services" if lang=='fr' else "My services" }}</h2>
    <div class="row mt-4 justify-content-center">
        {% for serv in services %}
        <div class="col-sm-6 col-md-4">
            <div class="service-card">
                <i class="bi {{ serv.icon }}"></i>
                <h5 class="mt-2 mb-2">{{ serv.titre[lang] }}</h5>
                <p>{{ serv.desc[lang] }}</p>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render(content, page="services", titre_page=("Services" if lang == "fr" else "Services"), services=SERVICES)

@app.route('/portfolio')
def portfolio():
    lang = get_lang()
    content = """
    <h2 class="section-title text-center">{{ "Quelques réalisations" if lang=='fr' else "Some work samples" }}</h2>
    <div class="row mt-4">
        {% for projet in portfolio %}
        <div class="col-md-6 mb-4">
            <div class="card card-portfolio">
                {% if projet.imgs %}
                <img src="{{ projet.imgs[0] }}" class="card-img-top" alt="Image projet">
                {% endif %}
                <div class="card-body">
                    <h5 class="card-title text-primary">{{ projet.titre[lang] }}</h5>
                    <p class="card-text">{{ projet.desc[lang] }}</p>
                    {% if projet.imgs|length > 1 %}
                      <div class="d-flex flex-wrap">
                        {% for img in projet.imgs[1:] %}
                          <img src="{{ img }}" class="portfolio-img-multi" alt="Projet image">
                        {% endfor %}
                      </div>
                    {% endif %}
                    {% if projet.fichiers %}
                      <p class="mt-2"><b>{{ "Fichiers :" if lang=='fr' else "Files:" }}</b>
                      {% for f in projet.fichiers %}
                        <a href="{{ url_for('uploaded_file', filename=f) }}" class="badge badge-file" target="_blank"><i class="bi bi-download"></i> {{ f }}</a>
                      {% endfor %}
                      </p>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render(content, page="portfolio", titre_page=("Portfolio" if lang=="fr" else "Portfolio"), portfolio=PORTFOLIO)

@app.route('/pourquoi')
def pourquoi():
    lang = get_lang()
    content = """
    <h2 class="section-title text-center">{{ "Pourquoi me confier votre projet ?" if lang=='fr' else "Why work with me?" }}</h2>
    <div class="row mt-4 justify-content-center">
      <div class="col-lg-10">
        {% for at in atouts %}
        <div class="reassure mb-2"><i class="bi bi-check-circle-fill" style="color:#28a745"></i> {{ at[lang] }}</div>
        {% endfor %}
      </div>
    </div>
    """
    return render(content, page="pourquoi", titre_page=("Pourquoi moi ?" if lang=="fr" else "Why me?"), atouts=ATOUTS)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve les fichiers uploadés (images, pdf, etc.)."""
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    lang = get_lang()
    if request.method == "POST":
        honeypot = request.form.get("website", "")
        if honeypot:
            logging.warning("Spam détecté via honeypot, formulaire ignoré.")
            flash("Erreur envoi formulaire.", "warning")
            return redirect(url_for('contact'))
        nom = request.form.get("nom")
        email = request.form.get("email")
        projet = request.form.get("projet")
        fichiers = []
        files = request.files.getlist("fichier")
        for file in files:
            if file and allowed_file(file.filename):
                # Générer un nom de fichier sécurisé avec timestamp
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                fichiers.append(filename)
        new_msg = {
            "nom": nom,
            "email": email,
            "projet": projet,
            "fichiers": fichiers,
            "status": "new",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        MSGS.append(new_msg)
        save_json_file(MSG_FILE, MSGS)
        # Notification stub
        subject = f"Nouveau message de {nom}"
        body = f"Nom: {nom}\nEmail: {email}\nProjet: {projet}\nTimestamp: {new_msg['timestamp']}\nFichiers: {', '.join(fichiers) if fichiers else 'aucun'}"
        send_email_notification(subject, body)
        flash((f"Merci {nom}, j'ai bien reçu votre demande et vos fichiers ! Je vous répondrai sous 24h." if lang=="fr"
               else f"Thank you {nom}, your request and files have been received! I will get back to you within 24h."), "success")
        return redirect(url_for('contact'))
    content = """
    <h2 class="section-title text-center">{{ "Votre projet commence ici" if lang=='fr' else "Start your project here" }}</h2>
    <div class="row justify-content-center mt-4">
      <div class="col-md-8">
        <form method="post" class="border rounded p-4 shadow-sm bg-white" enctype="multipart/form-data">
          <input type="text" name="website" style="display:none">
          <div class="mb-3">
            <label for="nom" class="form-label">{{ "Nom / Prénom ou société" if lang=='fr' else "Name / Company" }}</label>
            <input type="text" class="form-control" id="nom" name="nom" required>
          </div>
          <div class="mb-3">
            <label for="email" class="form-label">{{ "Votre adresse Email ou WhatsApp" if lang=='fr' else "Your Email or WhatsApp" }}</label>
            <input type="text" class="form-control" id="email" name="email" required>
          </div>
          <div class="mb-3">
            <label for="projet" class="form-label">{{ "Décrivez votre projet ou votre besoin" if lang=='fr' else "Describe your project or need" }}</label>
            <textarea class="form-control" id="projet" name="projet" rows="5" required></textarea>
          </div>
          <div class="mb-3">
            <label for="fichier" class="form-label">{{ "Joindre un ou plusieurs fichiers (pdf, dwg, rvt, images...)" if lang=='fr' else "Attach one or more files (pdf, dwg, rvt, images...)" }}</label>
            <div class="drag-drop-area" id="dragDrop">
                <i class="bi bi-cloud-arrow-up fs-2"></i><br>
                {{ "Glissez-déposez vos fichiers ici ou cliquez pour choisir" if lang=='fr' else "Drag & drop files here or click to select" }}
                <input class="form-control" type="file" name="fichier" id="fichier" accept=".pdf,.dwg,.rvt,.docx,.xlsx,.jpg,.jpeg,.png,.gif,.zip" multiple style="margin-top:10px;">
                <ul id="fileList" style="list-style:none; padding-left:0;"></ul>
            </div>
          </div>
          <button type="submit" class="btn btn-contact"><i class="bi bi-send"></i> {{ "Envoyer ma demande" if lang=='fr' else "Send my request" }}</button>
        </form>
        <div class="mt-4 text-center">
          <p><i class="bi bi-envelope"></i> <a href="mailto:{{ site.email }}">{{ site.email }}</a></p>
          <p><i class="bi bi-whatsapp"></i> <a href="https://wa.me/{{ site.whatsapp.replace(' ','').replace('+','') }}" target="_blank">{{ site.whatsapp }}</a></p>
        </div>
      </div>
    </div>
    """
    return render(content, page="contact", titre_page=("Contact / Projet" if get_lang()=="fr" else "Contact / Project"))

# ----------------------------------------
# Routes Admin
# ----------------------------------------
@app.route(f'/{ADMIN_SECRET_URL}', methods=['GET', 'POST'])
def admin():
    if not admin_logged_in():
        error = None
        if request.method == "POST":
            u = request.form.get("user")
            p = request.form.get("pass")
            if u == ADMIN_USER and p == ADMIN_PASS:
                session["admin"] = True
                flash("Connexion réussie.", "success")
                return redirect(url_for('admin'))
            else:
                error = "Identifiants incorrects."
                flash(error, "danger")
        login = """
        <div class="row justify-content-center mt-5">
          <div class="col-md-4 admin-panel">
            <h4 class="mb-3 text-center"><i class="bi bi-person-gear"></i> Connexion Admin</h4>
            <form method="post">
                <input class="form-control mb-2" type="text" name="user" placeholder="Email admin" required>
                <input class="form-control mb-3" type="password" name="pass" placeholder="Mot de passe" required>
                <button class="btn btn-contact w-100" type="submit">Se connecter</button>
            </form>
          </div>
        </div>
        """
        return render(login, titre_page="Connexion admin", page="admin_login")
    # Dashboard admin
    total_msgs = len(MSGS)
    unread_msgs = sum(1 for m in MSGS if m.get("status") == "new")
    total_services = len(SERVICES)
    total_portfolio = len(PORTFOLIO)
    total_atouts = len(ATOUTS)
    total_traffic = len(TRAFFIC)
    total_rotator = len(ROTATOR_ITEMS)
    today = datetime.now().strftime("%Y-%m-%d")
    visits_today = sum(1 for t in TRAFFIC if t.get("timestamp", "").startswith(today))
    content = """
    <div class="admin-nav text-center">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_services') }}">Services</a> |
      <a href="{{ url_for('admin_portfolio') }}">Portfolio</a> |
      <a href="{{ url_for('admin_atouts') }}">Atouts</a> |
      <a href="{{ url_for('admin_messages') }}">Messages{% if unread_msgs>0 %} ({{ unread_msgs }}){% endif %}</a> |
      <a href="{{ url_for('admin_carousel') }}">Carousel ({{ total_rotator }})</a> |
      <a href="{{ url_for('admin_analytics') }}">Analytics</a> |
      <a href="{{ url_for('admin_traffic') }}">Traffic</a> |
      <a href="{{ url_for('admin_settings') }}">Paramètres</a> |
      <a href="{{ url_for('download_all_uploads') }}">Télécharger Uploads</a> |
      <a href="{{ url_for('admin_logout') }}">Déconnexion</a>
    </div>
    <div class="admin-panel">
      <h4><i class="bi bi-speedometer2"></i> Tableau de bord Admin</h4>
      <div class="row">
        <div class="col-md-3"><div class="card text-center mb-3"><div class="card-body"><h5>{{ total_services }}</h5><p>Services</p></div></div></div>
        <div class="col-md-3"><div class="card text-center mb-3"><div class="card-body"><h5>{{ total_portfolio }}</h5><p>Portfolio</p></div></div></div>
        <div class="col-md-3"><div class="card text-center mb-3"><div class="card-body"><h5>{{ total_atouts }}</h5><p>Atouts</p></div></div></div>
        <div class="col-md-3"><div class="card text-center mb-3"><div class="card-body"><h5>{{ total_msgs }}</h5><p>Messages ({{ unread_msgs }} non lus)</p></div></div></div>
      </div>
      <p><strong>Visites totales :</strong> {{ total_traffic }}, <strong>Aujourd'hui :</strong> {{ visits_today }}</p>
      <p><strong>Items Carousel :</strong> {{ total_rotator }} (max 6)</p>
    </div>
    """
    return render(content,
                  titre_page="Admin",
                  page="admin_dashboard",
                  total_msgs=total_msgs,
                  unread_msgs=unread_msgs,
                  total_services=total_services,
                  total_portfolio=total_portfolio,
                  total_atouts=total_atouts,
                  total_traffic=total_traffic,
                  visits_today=visits_today,
                  total_rotator=total_rotator)

@app.route(f'/{ADMIN_SECRET_URL}/logout')
def admin_logout():
    session["admin"] = False
    flash("Déconnecté.", "info")
    return redirect(url_for('admin'))

# --- Gestion des services via admin ---
@app.route(f'/{ADMIN_SECRET_URL}/services', methods=["GET", "POST"])
def admin_services():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    edit_idx = request.args.get("edit")
    if request.method == "POST":
        titre_fr = request.form.get("titre_fr", "").strip()
        titre_en = request.form.get("titre_en", "").strip()
        desc_fr = request.form.get("desc_fr", "").strip()
        desc_en = request.form.get("desc_en", "").strip()
        icon = request.form.get("icon", "").strip() or "bi-star"
        if titre_fr and titre_en and desc_fr and desc_en:
            if request.form.get("edit_idx") and request.form.get("edit_idx").isdigit():
                idx = int(request.form.get("edit_idx"))
                if 0 <= idx < len(SERVICES):
                    SERVICES[idx] = {
                        "titre": {"fr": titre_fr, "en": titre_en},
                        "desc": {"fr": desc_fr, "en": desc_en},
                        "icon": icon
                    }
                    flash("Service mis à jour.", "success")
                else:
                    flash("Index invalide.", "danger")
            else:
                SERVICES.append({
                    "titre": {"fr": titre_fr, "en": titre_en},
                    "desc": {"fr": desc_fr, "en": desc_en},
                    "icon": icon
                })
                flash("Nouveau service ajouté.", "success")
        else:
            flash("Tous les champs sont requis.", "warning")
        return redirect(url_for('admin_services'))
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(SERVICES):
            SERVICES.pop(idx)
            flash("Service supprimé.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_services'))
    service_to_edit = None
    if edit_idx and edit_idx.isdigit():
        idx = int(edit_idx)
        if 0 <= idx < len(SERVICES):
            service_to_edit = SERVICES[idx]
        else:
            flash("Index invalide pour édition.", "warning")
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_services') }}">Services</a>
    </div>
    <div class="admin-panel">
      <h5>Gestion des Services</h5>
      {% if services %}
      <table class="table table-hover admin-table">
        <thead>
          <tr><th>#</th><th>FR</th><th>EN</th><th>Description FR</th><th>Description EN</th><th>Icon</th><th>Actions</th></tr>
        </thead>
        <tbody>
        {% for serv in services %}
          <tr>
            <td>{{ loop.index0 }}</td>
            <td>{{ serv.titre['fr'] }}</td>
            <td>{{ serv.titre['en'] }}</td>
            <td>{{ serv.desc['fr'] }}</td>
            <td>{{ serv.desc['en'] }}</td>
            <td><i class="bi {{ serv.icon }}"></i> {{ serv.icon }}</td>
            <td>
              <a href="{{ url_for('admin_services', edit=loop.index0) }}" class="btn btn-sm btn-primary">Éditer</a>
              <a href="{{ url_for('admin_services', del=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer ce service?');">Suppr.</a>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
      {% else %}
        <p>Aucun service défini.</p>
      {% endif %}
      <hr>
      <h6>{{ 'Modifier le service' if service_to_edit else 'Ajouter un nouveau service' }}</h6>
      <form method="post" class="row g-2">
        <input type="hidden" name="edit_idx" value="{{ request.args.get('edit') if service_to_edit is not none else '' }}">
        <div class="col-md-3"><input type="text" name="titre_fr" value="{{ service_to_edit.titre['fr'] if service_to_edit }}" class="form-control" placeholder="Service (FR)" required></div>
        <div class="col-md-3"><input type="text" name="titre_en" value="{{ service_to_edit.titre['en'] if service_to_edit }}" class="form-control" placeholder="Service (EN)" required></div>
        <div class="col-md-3"><input type="text" name="desc_fr" value="{{ service_to_edit.desc['fr'] if service_to_edit }}" class="form-control" placeholder="Description (FR)" required></div>
        <div class="col-md-3"><input type="text" name="desc_en" value="{{ service_to_edit.desc['en'] if service_to_edit }}" class="form-control" placeholder="Description (EN)" required></div>
        <div class="col-md-3"><input type="text" name="icon" value="{{ service_to_edit.icon if service_to_edit }}" class="form-control" placeholder="Icône bi-..." ></div>
        <div class="col-md-2"><button class="btn btn-contact w-100" type="submit">{{ 'Mettre à jour' if service_to_edit else 'Ajouter' }}</button></div>
      </form>
    </div>
    """
    return render(content, services=SERVICES, service_to_edit=service_to_edit)

# --- Gestion du portfolio via admin ---
@app.route(f'/{ADMIN_SECRET_URL}/portfolio', methods=["GET", "POST"])
def admin_portfolio():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    edit_idx = request.args.get("edit")
    if request.method == "POST":
        titre_fr = request.form.get("titre_fr", "").strip()
        titre_en = request.form.get("titre_en", "").strip()
        desc_fr = request.form.get("desc_fr", "").strip()
        desc_en = request.form.get("desc_en", "").strip()
        imgs_raw = request.form.get("imgs", "").strip()
        imgs = [img.strip() for img in imgs_raw.split(",") if img.strip()]
        fichiers_existants = []
        fichiers_nouveaux = []
        if request.form.get("edit_idx") and request.form.get("edit_idx").isdigit():
            idx = int(request.form.get("edit_idx"))
            if 0 <= idx < len(PORTFOLIO):
                fichiers_existants = PORTFOLIO[idx].get("fichiers", [])
        # Upload nouveaux fichiers
        files = request.files.getlist("fichiers")
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                fichiers_nouveaux.append(filename)
        fichiers = fichiers_existants + fichiers_nouveaux
        if titre_fr and titre_en and desc_fr and desc_en:
            if request.form.get("edit_idx") and request.form.get("edit_idx").isdigit():
                idx = int(request.form.get("edit_idx"))
                if 0 <= idx < len(PORTFOLIO):
                    # Conserver anciens fichiers + nouveaux
                    PORTFOLIO[idx] = {
                        "titre": {"fr": titre_fr, "en": titre_en},
                        "desc": {"fr": desc_fr, "en": desc_en},
                        "imgs": imgs,
                        "fichiers": fichiers
                    }
                    flash("Élément du portfolio mis à jour.", "success")
                else:
                    flash("Index invalide pour mise à jour.", "danger")
            else:
                PORTFOLIO.append({
                    "titre": {"fr": titre_fr, "en": titre_en},
                    "desc": {"fr": desc_fr, "en": desc_en},
                    "imgs": imgs,
                    "fichiers": fichiers
                })
                flash("Nouvel élément ajouté au portfolio.", "success")
        else:
            flash("Tous les champs texte sont requis.", "warning")
        return redirect(url_for('admin_portfolio'))
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(PORTFOLIO):
            # Supprimer physiquement les fichiers joints
            for f in PORTFOLIO[idx].get("fichiers", []):
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, f))
                except:
                    pass
            PORTFOLIO.pop(idx)
            flash("Élément portfolio supprimé.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_portfolio'))
    projet_to_edit = None
    if edit_idx and edit_idx.isdigit():
        idx = int(edit_idx)
        if 0 <= idx < len(PORTFOLIO):
            projet_to_edit = PORTFOLIO[idx]
        else:
            flash("Index invalide pour édition.", "warning")
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_portfolio') }}">Portfolio</a>
    </div>
    <div class="admin-panel">
      <h5>Gestion du Portfolio</h5>
      {% if portfolio %}
      <table class="table table-hover admin-table">
        <thead>
          <tr><th>#</th><th>FR</th><th>EN</th><th>Images (URLs)</th><th>Fichiers joints</th><th>Actions</th></tr>
        </thead>
        <tbody>
        {% for proj in portfolio %}
          <tr>
            <td>{{ loop.index0 }}</td>
            <td>{{ proj.titre['fr'] }}</td>
            <td>{{ proj.titre['en'] }}</td>
            <td>
              {% for img in proj.imgs %}
                <span class="badge bg-secondary text-truncate" style="max-width: 100px;">{{ img }}</span><br>
              {% endfor %}
            </td>
            <td>
              {% for f in proj.fichiers %}
                <a href="{{ url_for('uploaded_file', filename=f) }}" class="badge bg-info text-dark" target="_blank">{{ f }}</a><br>
              {% endfor %}
            </td>
            <td>
              <a href="{{ url_for('admin_portfolio', edit=loop.index0) }}" class="btn btn-sm btn-primary">Éditer</a>
              <a href="{{ url_for('admin_portfolio', del=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer cet élément?');">Suppr.</a>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
      {% else %}
        <p>Aucun élément dans le portfolio.</p>
      {% endif %}
      <hr>
      <h6>{{ 'Modifier l’élément' if projet_to_edit else 'Ajouter un nouvel élément' }}</h6>
      <form method="post" enctype="multipart/form-data" class="row g-2">
        <input type="hidden" name="edit_idx" value="{{ request.args.get('edit') if projet_to_edit is not none else '' }}">
        <div class="col-md-3"><input type="text" name="titre_fr" value="{{ projet_to_edit.titre['fr'] if projet_to_edit }}" class="form-control" placeholder="Titre FR" required></div>
        <div class="col-md-3"><input type="text" name="titre_en" value="{{ projet_to_edit.titre['en'] if projet_to_edit }}" class="form-control" placeholder="Titre EN" required></div>
        <div class="col-md-3"><input type="text" name="desc_fr" value="{{ projet_to_edit.desc['fr'] if projet_to_edit }}" class="form-control" placeholder="Description FR" required></div>
        <div class="col-md-3"><input type="text" name="desc_en" value="{{ projet_to_edit.desc['en'] if projet_to_edit }}" class="form-control" placeholder="Description EN" required></div>
        <div class="col-md-4"><input type="text" name="imgs" value="{{ projet_to_edit.imgs|join(', ') if projet_to_edit }}" class="form-control" placeholder="URLs images, séparées par virgule"></div>
        <div class="col-md-4"><input type="file" name="fichiers" class="form-control" multiple></div>
        <div class="col-md-2"><button class="btn btn-contact w-100" type="submit">{{ 'Mettre à jour' if projet_to_edit else 'Ajouter' }}</button></div>
      </form>
      <div class="small mt-1">Pour images, coller des URLs (ex: https://...jpg), séparées par virgule.</div>
    </div>
    """
    return render(content, portfolio=PORTFOLIO, projet_to_edit=projet_to_edit)

# --- Gestion des atouts via admin ---
@app.route(f'/{ADMIN_SECRET_URL}/atouts', methods=["GET", "POST"])
def admin_atouts():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    edit_idx = request.args.get("edit")
    if request.method == "POST":
        at_fr = request.form.get("atout_fr", "").strip()
        at_en = request.form.get("atout_en", "").strip()
        if at_fr and at_en:
            if request.form.get("edit_idx") and request.form.get("edit_idx").isdigit():
                idx = int(request.form.get("edit_idx"))
                if 0 <= idx < len(ATOUTS):
                    ATOUTS[idx] = {"fr": at_fr, "en": at_en}
                    flash("Argument mis à jour.", "success")
                else:
                    flash("Index invalide.", "danger")
            else:
                ATOUTS.append({"fr": at_fr, "en": at_en})
                flash("Nouvel argument ajouté.", "success")
        else:
            flash("Les deux champs (FR et EN) sont requis.", "warning")
        return redirect(url_for('admin_atouts'))
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(ATOUTS):
            ATOUTS.pop(idx)
            flash("Argument supprimé.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_atouts'))
    atout_to_edit = None
    if edit_idx and edit_idx.isdigit():
        idx = int(edit_idx)
        if 0 <= idx < len(ATOUTS):
            atout_to_edit = ATOUTS[idx]
        else:
            flash("Index invalide pour édition.", "warning")
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_atouts') }}">Atouts</a>
    </div>
    <div class="admin-panel">
      <h5>Gestion des Atouts / Arguments</h5>
      {% if atouts %}
      <ul class="list-group mb-3">
        {% for at in atouts %}
        <li class="list-group-item d-flex justify-content-between align-items-center">
          <div>
            <b>FR :</b> {{ at['fr'] }}<br><b>EN :</b> {{ at['en'] }}
          </div>
          <div>
            <a href="{{ url_for('admin_atouts', edit=loop.index0) }}" class="btn btn-sm btn-primary">Éditer</a>
            <a href="{{ url_for('admin_atouts', del=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer cet argument?');">Suppr.</a>
          </div>
        </li>
        {% endfor %}
      </ul>
      {% else %}
        <p>Aucun argument défini.</p>
      {% endif %}
      <hr>
      <h6>{{ 'Modifier l’argument' if atout_to_edit else 'Ajouter un nouvel argument' }}</h6>
      <form method="post" class="row g-2">
        <input type="hidden" name="edit_idx" value="{{ request.args.get('edit') if atout_to_edit is not none else '' }}">
        <div class="col-md-5"><input type="text" name="atout_fr" value="{{ atout_to_edit.fr if atout_to_edit }}" class="form-control" placeholder="Argument FR" required></div>
        <div class="col-md-5"><input type="text" name="atout_en" value="{{ atout_to_edit.en if atout_to_edit }}" class="form-control" placeholder="Argument EN" required></div>
        <div class="col-md-2"><button class="btn btn-contact w-100" type="submit">{{ 'Mettre à jour' if atout_to_edit else 'Ajouter' }}</button></div>
      </form>
    </div>
    """
    return render(content, atouts=ATOUTS, atout_to_edit=atout_to_edit)

# --- Gestion des messages reçus via admin ---
@app.route(f'/{ADMIN_SECRET_URL}/messages', methods=["GET", "POST"])
@app.route(f'/{ADMIN_SECRET_URL}/messages/')
def admin_messages():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    action = request.args.get("action")
    idx_param = request.args.get("idx")
    delid = request.args.get("del")
    filter_param = request.args.get("filter")
    search_q = request.args.get("search", "").strip()
    page = request.args.get("page", 1)
    try:
        page = int(page)
        if page < 1:
            page = 1
    except:
        page = 1
    per_page = 10

    # Toggle status lu/new
    if action == "toggle" and idx_param and idx_param.isdigit():
        idx = int(idx_param)
        if 0 <= idx < len(MSGS):
            current = MSGS[idx].get("status", "new")
            MSGS[idx]["status"] = "read" if current == "new" else "new"
            save_json_file(MSG_FILE, MSGS)
            flash("Statut du message modifié.", "success")
        return redirect(url_for('admin_messages', filter=filter_param, search=search_q, page=page))

    # Suppression
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(MSGS):
            for f in MSGS[idx].get("fichiers", []):
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, f))
                except:
                    pass
            MSGS.pop(idx)
            save_json_file(MSG_FILE, MSGS)
            flash("Message supprimé.", "info")
        else:
            flash("Index invalide pour suppression de message.", "danger")
        return redirect(url_for('admin_messages', filter=filter_param, search=search_q, page=page))

    def matches(msg):
        if filter_param == 'new' and msg.get("status") != "new":
            return False
        if search_q:
            text = f"{msg.get('nom','')} {msg.get('email','')} {msg.get('projet','')}".lower()
            if search_q.lower() not in text:
                return False
        return True

    filtered = [m for m in MSGS if matches(m)]
    total = len(filtered)
    start = (page-1)*per_page
    end = start + per_page
    paginated = filtered[start:end]
    total_pages = (total + per_page - 1)//per_page

    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_messages') }}">Messages reçus</a>
    </div>
    <div class="admin-panel">
      <h5>Messages reçus via le formulaire</h5>
      <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap">
        <div class="mb-2">
          <a href="{{ url_for('admin_messages') }}" class="btn btn-sm btn-outline-primary {% if not filter_param %}active{% endif %}">Tous</a>
          <a href="{{ url_for('admin_messages', filter='new') }}" class="btn btn-sm btn-outline-primary {% if filter_param=='new' %}active{% endif %}">{{ 'Non lus' if lang=='fr' else 'Unread' }}</a>
        </div>
        <form method="get" class="d-flex mb-2">
          <input type="hidden" name="filter" value="{{ filter_param or '' }}">
          <input type="text" name="search" value="{{ search_q }}" class="form-control form-control-sm" placeholder="{{ 'Recherche...' if lang=='fr' else 'Search...' }}">
          <button type="submit" class="btn btn-sm btn-primary ms-1">{{ 'Rechercher' if lang=='fr' else 'Search' }}</button>
        </form>
        <a href="{{ url_for('export_messages') }}" class="btn btn-sm btn-primary mb-2">{{ 'Exporter JSON' if lang=='fr' else 'Export JSON' }}</a>
      </div>
      {% if paginated %}
      <table class="table table-hover admin-table">
        <thead>
        <tr>
          <th>#</th>
          <th>{{ 'Nom' if lang=='fr' else 'Name' }}</th>
          <th>{{ 'Email/WhatsApp' if lang=='fr' else 'Email/WhatsApp' }}</th>
          <th>{{ 'Projet' if lang=='fr' else 'Project' }}</th>
          <th>{{ 'Date/Heure' if lang=='fr' else 'Timestamp' }}</th>
          <th>{{ 'Statut' if lang=='fr' else 'Status' }}</th>
          <th>{{ 'Fichiers' if lang=='fr' else 'Files' }}</th>
          <th>{{ 'Actions' if lang=='fr' else 'Actions' }}</th>
        </tr>
        </thead>
        <tbody>
        {% for msg in paginated %}
          {% set idx = MSGS.index(msg) %}
          <tr {% if msg.status=='new' %}class="table-warning"{% endif %}>
            <td>{{ idx }}</td>
            <td>{{ msg.nom }}</td>
            <td>
              {{ msg.email }}
              {% if msg.email %}
                <a href="mailto:{{ msg.email }}" title="{{ 'Répondre' if lang=='fr' else 'Reply' }}" class="btn btn-sm btn-outline-primary ms-1"><i class="bi bi-envelope"></i></a>
              {% endif %}
            </td>
            <td>{{ msg.projet[:30] }}{% if msg.projet|length > 30 %}...{% endif %}</td>
            <td>{{ msg.timestamp }}</td>
            <td>
              {% if msg.status=='new' %}
                <span class="badge bg-warning text-dark">{{ 'Non lu' if lang=='fr' else 'New' }}</span>
              {% else %}
                <span class="badge bg-success">{{ 'Lu' if lang=='fr' else 'Read' }}</span>
              {% endif %}
            </td>
            <td>
              {% if msg.fichiers %}
                <span class="text-primary">{{ msg.fichiers|length }}</span>
              {% else %}
                <span class="text-muted">-</span>
              {% endif %}
            </td>
            <td>
              <a href="{{ url_for('view_message', idx=idx) }}" class="btn btn-sm btn-primary">Voir</a>
              <a href="{{ url_for('admin_messages', action='toggle', idx=idx, filter=filter_param, search=search_q, page=page) }}" class="btn btn-sm btn-secondary ms-1">
                {% if msg.status=='new' %}{{ 'Marquer lu' if lang=='fr' else 'Mark read' }}{% else %}{{ 'Marquer non lu' if lang=='fr' else 'Mark unread' }}{% endif %}
              </a>
              {% if msg.fichiers %}
              <a href="{{ url_for('download_attachments', idx=idx) }}" class="btn btn-sm btn-info ms-1">{{ 'Télécharger' if lang=='fr' else 'Download' }}</a>
              {% endif %}
              <a href="{{ url_for('admin_messages', del=idx, filter=filter_param, search=search_q, page=page) }}" class="btn btn-sm btn-danger ms-1" onclick="return confirm('Supprimer ce message?');">{{ 'Suppr.' if lang=='fr' else 'Delete' }}</a>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
      <nav>
        <ul class="pagination justify-content-center">
          {% if page>1 %}
          <li class="page-item"><a class="page-link" href="{{ url_for('admin_messages', filter=filter_param, search=search_q, page=page-1) }}">&laquo;</a></li>
          {% else %}
          <li class="page-item disabled"><span class="page-link">&laquo;</span></li>
          {% endif %}
          {% for p in range(1, total_pages+1) %}
            <li class="page-item {% if p==page %}active{% endif %}">
              <a class="page-link" href="{{ url_for('admin_messages', filter=filter_param, search=search_q, page=p) }}">{{ p }}</a>
            </li>
          {% endfor %}
          {% if page<total_pages %}
          <li class="page-item"><a class="page-link" href="{{ url_for('admin_messages', filter=filter_param, search=search_q, page=page+1) }}">&raquo;</a></li>
          {% else %}
          <li class="page-item disabled"><span class="page-link">&raquo;</span></li>
          {% endif %}
        </ul>
      </nav>
      {% else %}
      <div class="admin-msg">{{ "Aucun message pour l’instant." if lang=='fr' else "No messages yet." }}</div>
      {% endif %}
    </div>
    """
    return render(content,
                  page="admin_messages",
                  filter_param=filter_param,
                  search_q=search_q,
                  paginated=paginated,
                  total_pages=total_pages,
                  MSGS=MSGS)

@app.route(f'/{ADMIN_SECRET_URL}/messages/view/<int:idx>', methods=['GET', 'POST'])
def view_message(idx):
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    if not (0 <= idx < len(MSGS)):
        flash("Index de message invalide.", "danger")
        return redirect(url_for('admin_messages'))
    msg = MSGS[idx]
    if request.method == "POST":
        action = request.form.get("action")
        if action == "toggle_status":
            current = msg.get("status", "new")
            msg["status"] = "read" if current == "new" else "new"
            save_json_file(MSG_FILE, MSGS)
            flash("Statut mis à jour.", "success")
        return redirect(url_for('view_message', idx=idx))
    lang = get_lang()
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_messages') }}">Messages reçus</a> |
      <a href="{{ url_for('view_message', idx=idx) }}">{{ 'Détail' if lang=='fr' else 'Detail' }}</a>
    </div>
    <div class="admin-panel">
      <h5>{{ 'Détail du message' if lang=='fr' else 'Message Detail' }} ({{ idx }})</h5>
      <p><strong>{{ 'Nom / Société:' if lang=='fr' else 'Name / Company:' }}</strong> {{ msg.nom }}</p>
      <p><strong>{{ 'Email / WhatsApp:' if lang=='fr' else 'Email / WhatsApp:' }}</strong>
        {% if msg.email %}
          <a href="mailto:{{ msg.email }}">{{ msg.email }}</a>
        {% else %}
          -
        {% endif %}
      </p>
      <p><strong>{{ 'Projet / Besoin:' if lang=='fr' else 'Project / Need:' }}</strong><br>{{ msg.projet }}</p>
      <p><strong>{{ 'Timestamp:' if lang=='fr' else 'Timestamp:' }}</strong> {{ msg.timestamp }}</p>
      <p><strong>{{ 'Statut:' if lang=='fr' else 'Status:' }}</strong>
        {% if msg.status=='new' %}
          <span class="badge bg-warning text-dark">{{ 'Non lu' if lang=='fr' else 'New' }}</span>
        {% else %}
          <span class="badge bg-success">{{ 'Lu' if lang=='fr' else 'Read' }}</span>
        {% endif %}
      </p>
      <p><strong>{{ 'Fichiers joints:' if lang=='fr' else 'Attached files:' }}</strong>
        {% if msg.fichiers %}
          <ul>
            {% for f in msg.fichiers %}
              <li><a href="{{ url_for('uploaded_file', filename=f) }}" target="_blank">{{ f }}</a></li>
            {% endfor %}
          </ul>
          <a href="{{ url_for('download_attachments', idx=idx) }}" class="btn btn-info btn-sm">{{ 'Télécharger tous' if lang=='fr' else 'Download all' }}</a>
        {% else %}
          <span class="text-muted">-</span>
        {% endif %}
      </p>
      <form method="post" class="mt-3">
        <input type="hidden" name="action" value="toggle_status">
        <button type="submit" class="btn btn-secondary btn-sm">
          {% if msg.status=='new' %}
            {{ 'Marquer comme lu' if lang=='fr' else 'Mark as read' }}
          {% else %}
            {{ 'Marquer non lu' if lang=='fr' else 'Mark as unread' }}
          {% endif %}
        </button>
      </form>
      <div class="mt-3">
        <a href="{{ url_for('admin_messages') }}" class="btn btn-primary btn-sm">{{ 'Retour à la liste' if lang=='fr' else 'Back to list' }}</a>
      </div>
    </div>
    """
    return render(content, idx=idx, msg=msg, lang=lang)

@app.route(f'/{ADMIN_SECRET_URL}/messages/download/<int:idx>')
def download_attachments(idx):
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    if 0 <= idx < len(MSGS):
        fichiers = MSGS[idx].get("fichiers", [])
        if not fichiers:
            flash("Aucun fichier à télécharger.", "warning")
            return redirect(url_for('view_message', idx=idx))
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in fichiers:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.exists(file_path):
                    zf.write(file_path, arcname=filename)
        memory_file.seek(0)
        timestamp = MSGS[idx].get("timestamp", "").replace(":", "-").replace(" ", "_")
        zip_name = f"message_{idx}_{timestamp}.zip" if timestamp else f"message_{idx}.zip"
        return send_file(memory_file, download_name=zip_name, as_attachment=True)
    flash("Index de message invalide.", "danger")
    return redirect(url_for('admin_messages'))

@app.route(f'/{ADMIN_SECRET_URL}/messages/export')
def export_messages():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    if os.path.exists(MSG_FILE):
        return send_file(MSG_FILE, as_attachment=True)
    data = json.dumps(MSGS, indent=2, ensure_ascii=False)
    return (data, 200, {
        'Content-Type': 'application/json',
        'Content-Disposition': 'attachment; filename="messages.json"'
    })

# --- Gestion du carousel via admin ---
@app.route(f'/{ADMIN_SECRET_URL}/carousel', methods=["GET", "POST"])
def admin_carousel():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    # Suppression
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(ROTATOR_ITEMS):
            filename = ROTATOR_ITEMS[idx].get("filename")
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, filename))
            except:
                pass
            ROTATOR_ITEMS.pop(idx)
            save_json_file(ROTATOR_FILE, ROTATOR_ITEMS)
            flash("Item supprimé du carousel.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_carousel'))
    # Réordonner
    move = request.args.get("move")
    idx_param = request.args.get("idx")
    if move and idx_param and idx_param.isdigit():
        idx = int(idx_param)
        if 0 <= idx < len(ROTATOR_ITEMS):
            if move == "up" and idx > 0:
                ROTATOR_ITEMS[idx-1], ROTATOR_ITEMS[idx] = ROTATOR_ITEMS[idx], ROTATOR_ITEMS[idx-1]
                save_json_file(ROTATOR_FILE, ROTATOR_ITEMS)
                flash("Item déplacé vers le haut.", "success")
            elif move == "down" and idx < len(ROTATOR_ITEMS)-1:
                ROTATOR_ITEMS[idx+1], ROTATOR_ITEMS[idx] = ROTATOR_ITEMS[idx], ROTATOR_ITEMS[idx+1]
                save_json_file(ROTATOR_FILE, ROTATOR_ITEMS)
                flash("Item déplacé vers le bas.", "success")
        return redirect(url_for('admin_carousel'))
    # Upload nouveau fichier carousel
    if request.method == "POST":
        if len(ROTATOR_ITEMS) >= 6:
            flash("Limite atteinte: maximum 6 items autorisés.", "warning")
            return redirect(url_for('admin_carousel'))
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Aucun fichier sélectionné.", "warning")
            return redirect(url_for('admin_carousel'))
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext not in IMAGE_EXTENSIONS.union(PDF_EXTENSIONS):
                flash("Type de fichier non pris en charge pour le carousel (seulement images ou PDF).", "danger")
                return redirect(url_for('admin_carousel'))
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            ftype = "image" if ext in IMAGE_EXTENSIONS else "pdf"
            ROTATOR_ITEMS.append({"filename": filename, "type": ftype})
            save_json_file(ROTATOR_FILE, ROTATOR_ITEMS)
            flash("Fichier ajouté au carousel.", "success")
        else:
            flash("Fichier non valide.", "danger")
        return redirect(url_for('admin_carousel'))
    lang = get_lang()
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_carousel') }}">Carousel</a>
    </div>
    <div class="admin-panel">
      <h5>Gestion du Carousel (page d'accueil)</h5>
      <p>Nombre d'items actuels: {{ items|length }} / 6</p>
      {% if items %}
      <div class="table-responsive">
      <table class="table table-hover admin-table align-middle">
        <thead>
          <tr><th>#</th><th>Aperçu</th><th>Nom du fichier</th><th>Actions</th></tr>
        </thead>
        <tbody>
        {% for item in items %}
          <tr>
            <td>{{ loop.index0 }}</td>
            <td>
              {% if item.type=='image' %}
                <img src="{{ url_for('uploaded_file', filename=item.filename) }}" alt="img" style="max-height:80px;">
              {% elif item.type=='pdf' %}
                <i class="bi bi-file-earmark-pdf-fill" style="font-size:2rem;color:#dc3545;"></i>
              {% endif %}
            </td>
            <td style="max-width:200px; word-break:break-all;">{{ item.filename }}</td>
            <td>
              {% if not loop.first %}
                <a href="{{ url_for('admin_carousel', move='up', idx=loop.index0) }}" class="btn btn-sm btn-secondary">↑</a>
              {% else %}
                <button class="btn btn-sm btn-secondary" disabled>↑</button>
              {% endif %}
              {% if not loop.last %}
                <a href="{{ url_for('admin_carousel', move='down', idx=loop.index0) }}" class="btn btn-sm btn-secondary">↓</a>
              {% else %}
                <button class="btn btn-sm btn-secondary" disabled>↓</button>
              {% endif %}
              <a href="{{ url_for('admin_carousel', del=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer cet item?');">Suppr.</a>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
      </div>
      {% else %}
        <p>Aucun item dans le carousel.</p>
      {% endif %}
      <hr>
      {% if items|length < 6 %}
      <h6>Ajouter un nouvel item</h6>
      <form method="post" enctype="multipart/form-data" class="row g-2 align-items-center">
        <div class="col-auto">
          <input type="file" name="file" class="form-control" accept=".jpg,.jpeg,.png,.gif,.pdf" required>
        </div>
        <div class="col-auto">
          <button class="btn btn-contact" type="submit">{{ 'Ajouter' if lang=='fr' else 'Add' }}</button>
        </div>
      </form>
      <div class="small mt-1">{{ 'Formats acceptés: jpg, jpeg, png, gif, pdf. Maximum 6 items.' if lang=='fr' else 'Accepted formats: jpg, jpeg, png, gif, pdf. Up to 6 items.' }}</div>
      {% else %}
      <div class="alert alert-info">{{ 'Limite atteinte: 6 items. Supprimez-en avant d’ajouter.' if lang=='fr' else 'Limit reached: 6 items. Remove some before adding.' }}</div>
      {% endif %}
    </div>
    """
    return render(content, items=ROTATOR_ITEMS)

# --- Analytics ---
@app.route(f'/{ADMIN_SECRET_URL}/analytics')
def admin_analytics():
    if not admin_logged_in():
        flash("Veuillez vous connecter.", "warning")
        return redirect(url_for('admin'))
    counts = {}
    for m in MSGS:
        ts = m.get("timestamp", "")
        if ts:
            date = ts.split(" ")[0]
            counts[date] = counts.get(date, 0) + 1
    sorted_dates = sorted(counts.items(), key=lambda x: x[0], reverse=True)
    total_msgs = len(MSGS)
    unread_msgs = sum(1 for m in MSGS if m.get("status") == "new")
    total_services = len(SERVICES)
    total_portfolio = len(PORTFOLIO)
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_analytics') }}">Analytics</a>
    </div>
    <div class="admin-panel">
      <h5>Analytics du site</h5>
      <p><b>{{ 'Nombre total de messages' if lang=='fr' else 'Total messages' }}:</b> {{ total_msgs }}</p>
      <p><b>{{ 'Messages non lus' if lang=='fr' else 'Unread messages' }}:</b> {{ unread_msgs }}</p>
      <p><b>{{ 'Services proposés' if lang=='fr' else 'Services offered' }}:</b> {{ total_services }}</p>
      <p><b>{{ 'Éléments du portfolio' if lang=='fr' else 'Portfolio items' }}:</b> {{ total_portfolio }}</p>
      <h6 class="mt-4">{{ 'Messages par date' if lang=='fr' else 'Messages by date' }}:</h6>
      {% if sorted_dates %}
      <ul>
        {% for date, cnt in sorted_dates %}
        <li>{{ date }}: {{ cnt }}</li>
        {% endfor %}
      </ul>
      {% else %}
      <p>{{ 'Aucune donnée de message.' if lang=='fr' else 'No message data.' }}</p>
      {% endif %}
    </div>
    """
    return render(content,
                  total_msgs=total_msgs,
                  unread_msgs=unread_msgs,
                  total_services=total_services,
                  total_portfolio=total_portfolio,
                  sorted_dates=sorted_dates)

# --- Télécharger tout uploads ---
@app.route(f'/{ADMIN_SECRET_URL}/download_uploads')
def download_all_uploads():
    if not admin_logged_in():
        flash("Veuillez vous connecter.", "warning")
        return redirect(url_for('admin'))
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, UPLOAD_FOLDER)
                zf.write(file_path, arcname=arcname)
    memory_file.seek(0)
    zip_name = f"all_uploads_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    return send_file(memory_file, download_name=zip_name, as_attachment=True)

# --- Trafic ---
@app.route(f'/{ADMIN_SECRET_URL}/traffic')
def admin_traffic():
    if not admin_logged_in():
        flash("Veuillez vous connecter.", "warning")
        return redirect(url_for('admin'))
    agg = {}
    for entry in TRAFFIC:
        ts = entry.get("timestamp", "")
        date = ts.split(" ")[0] if ts else ""
        path = entry.get("path", "")
        key = (date, path)
        agg[key] = agg.get(key, 0) + 1
    rows = [{"date": date, "path": path, "count": count} for (date, path), count in agg.items()]
    rows_sorted = sorted(rows, key=lambda x: (x["date"], x["count"]), reverse=True)
    page = request.args.get("page", 1)
    try:
        page = int(page)
        if page < 1: page = 1
    except:
        page = 1
    per_page = 20
    total = len(rows_sorted)
    total_pages = (total + per_page - 1)//per_page
    start = (page-1)*per_page; end = start + per_page
    page_rows = rows_sorted[start:end]
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_traffic') }}">Traffic</a>
    </div>
    <div class="admin-panel">
      <h5>Tableau du trafic</h5>
      <p><b>{{ 'Enregistrements total' if lang=='fr' else 'Total records' }}:</b> {{ total }}</p>
      {% if page_rows %}
      <table class="table table-hover admin-table">
        <thead><tr><th>{{ 'Date' if lang=='fr' else 'Date' }}</th><th>{{ 'Chemin' if lang=='fr' else 'Path' }}</th><th>{{ 'Visites' if lang=='fr' else 'Visits' }}</th></tr></thead>
        <tbody>
        {% for row in page_rows %}
        <tr>
          <td>{{ row.date }}</td>
          <td>{{ row.path }}</td>
          <td>{{ row.count }}</td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
      <nav>
        <ul class="pagination justify-content-center">
          {% if page>1 %}
          <li class="page-item"><a class="page-link" href="{{ url_for('admin_traffic', page=page-1) }}">&laquo;</a></li>
          {% else %}
          <li class="page-item disabled"><span class="page-link">&laquo;</span></li>
          {% endif %}
          {% for p in range(1, total_pages+1) %}
            <li class="page-item {% if p==page %}active{% endif %}">
              <a class="page-link" href="{{ url_for('admin_traffic', page=p) }}">{{ p }}</a>
            </li>
          {% endfor %}
          {% if page<total_pages %}
          <li class="page-item"><a class="page-link" href="{{ url_for('admin_traffic', page=page+1) }}">&raquo;</a></li>
          {% else %}
          <li class="page-item disabled"><span class="page-link">&raquo;</span></li>
          {% endif %}
        </ul>
      </nav>
      {% else %}
      <p>{{ 'Aucun enregistrement de trafic.' if lang=='fr' else 'No traffic records.' }}</p>
      {% endif %}
      <hr>
      <p><i>{{ 'Note: ce tableau agrège les visites par date et chemin. Les entrées brutes sont stockées dans traffic.json.' if lang=='fr' else 'Note: this table aggregates visits by date and path. Raw entries are stored in traffic.json.' }}</i></p>
    </div>
    """
    return render(content,
                  total=total,
                  page_rows=page_rows,
                  page=page,
                  total_pages=total_pages)

# --- Sitemap SEO ---
@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = [
        url_for('index', _external=True),
        url_for('services', _external=True),
        url_for('portfolio', _external=True),
        url_for('pourquoi', _external=True),
        url_for('contact', _external=True),
        url_for('toggle_dark', _external=True),
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for page in pages:
        xml.append(f"<url><loc>{page}</loc></url>")
    xml.append("</urlset>")
    response = app.response_class("\n".join(xml), mimetype='application/xml')
    return response

@app.route('/favicon.ico')
def favicon():
    return abort(404)

# --- Nouvelle route admin: Paramètres du thème + photo ---
@app.route(f'/{ADMIN_SECRET_URL}/settings', methods=['GET', 'POST'])
def admin_settings():
    if not admin_logged_in():
        flash("Veuillez vous connecter.", "warning")
        return redirect(url_for('admin'))
    lang = get_lang()
    if request.method == "POST":
        # Récupération valeurs du formulaire :
        nouvelle_couleur = request.form.get("couleur", "").strip()
        nouvelle_font = request.form.get("font", "").strip()
        nouvelle_photo_url = request.form.get("photo_url", "").strip()
        photo_file = request.files.get("photo_file")
        changed = False

        # Couleur principale : validation hex #RRGGBB
        if nouvelle_couleur:
            if nouvelle_couleur.startswith("#") and len(nouvelle_couleur) == 7:
                SITE["couleur"] = nouvelle_couleur
                config_theme["couleur"] = nouvelle_couleur
                changed = True
            else:
                flash("Format de couleur invalide. Utilisez #RRGGBB.", "warning")

        # Police : on accepte tout nom, mais l'utilisateur doit s'assurer que c'est disponible via Google Fonts
        if nouvelle_font:
            SITE["font"] = nouvelle_font
            config_theme["font"] = nouvelle_font
            changed = True

        # Photo de profil :
        # - Si un fichier uploadé est présent, on l'utilise en priorité.
        # - Sinon si URL fournie non vide, on l'utilise.
        if photo_file and photo_file.filename:
            # Vérifier extension image
            ext = photo_file.filename.rsplit('.', 1)[1].lower() if '.' in photo_file.filename else ''
            if ext in IMAGE_EXTENSIONS:
                filename = secure_filename(f"profile_{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo_file.filename}")
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                photo_file.save(save_path)
                # On stocke le chemin relatif pour l'accès via /uploads/<filename>
                photo_path = url_for('uploaded_file', filename=filename)
                SITE["photo"] = photo_path
                config_theme["photo"] = photo_path
                changed = True
            else:
                flash("Fichier de profil non valide. Extensions autorisées: jpg, jpeg, png, gif.", "warning")
        else:
            # Pas de fichier uploadé, on regarde l'URL
            if nouvelle_photo_url:
                # On peut faire une validation basique : doit commencer par http:// ou https://
                if nouvelle_photo_url.startswith("http://") or nouvelle_photo_url.startswith("https://"):
                    SITE["photo"] = nouvelle_photo_url
                    config_theme["photo"] = nouvelle_photo_url
                    changed = True
                else:
                    flash("URL de photo invalide. Commencez par http:// ou https://", "warning")
        if changed:
            save_json_file(CONFIG_FILE, config_theme)
            flash(("Paramètres du thème mis à jour." if lang=="fr" else "Theme settings updated."), "success")
        return redirect(url_for('admin_settings'))

    # GET : afficher formulaire avec valeurs actuelles
    current_color = SITE.get("couleur", default_color)
    current_font = SITE.get("font", default_font)
    current_photo = SITE.get("photo", default_photo)
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_settings') }}">Paramètres</a>
    </div>
    <div class="admin-panel">
      <h5>{{ 'Paramètres du thème' if lang=='fr' else 'Theme Settings' }}</h5>
      <form method="post" class="row g-3" enctype="multipart/form-data">
        <div class="col-md-4">
          <label for="couleur" class="form-label">{{ 'Couleur principale (hex)' if lang=='fr' else 'Primary color (hex)' }}</label>
          <input type="text" class="form-control" id="couleur" name="couleur" value="{{ current_color }}" placeholder="#RRGGBB" required>
        </div>
        <div class="col-md-4">
          <label for="font" class="form-label">{{ 'Police (Google Font ou locale)' if lang=='fr' else 'Font (Google Font or local)' }}</label>
          <input type="text" class="form-control" id="font" name="font" value="{{ current_font }}" placeholder="Montserrat">
        </div>
        <div class="col-md-4">
          <label class="form-label">{{ 'Photo de profil actuelle' if lang=='fr' else 'Current profile photo' }}</label><br>
          {% if current_photo %}
            <img src="{{ current_photo }}" alt="Photo profil" style="max-height:100px; border-radius:50%; border:2px solid var(--primary-color);">
          {% else %}
            <span class="text-muted">{{ 'Aucune photo définie' if lang=='fr' else 'No photo set' }}</span>
          {% endif %}
        </div>

        <div class="col-md-4">
          <label for="photo_url" class="form-label">{{ 'Nouvelle URL de photo' if lang=='fr' else 'New photo URL' }}</label>
          <input type="text" class="form-control" id="photo_url" name="photo_url" value="" placeholder="https://...">
          <div class="form-text">{{ 'Si vous fournissez une URL valide, elle sera utilisée.' if lang=='fr' else 'If you provide a valid URL, it will be used.' }}</div>
        </div>
        <div class="col-md-4">
          <label for="photo_file" class="form-label">{{ 'Ou uploader un fichier image' if lang=='fr' else 'Or upload an image file' }}</label>
          <input type="file" class="form-control" id="photo_file" name="photo_file" accept=".jpg,.jpeg,.png,.gif">
          <div class="form-text">{{ 'Le fichier uploadé sera utilisé en priorité.' if lang=='fr' else 'Uploaded file will be used in priority.' }}</div>
        </div>
        <div class="col-md-4 d-flex align-items-end">
          <button type="submit" class="btn btn-contact">{{ 'Enregistrer' if lang=='fr' else 'Save' }}</button>
        </div>
      </form>
      <div class="mt-3">
        <p class="small">{{ 'La couleur, la police et la photo seront appliquées immédiatement sur tout le site.' if lang=='fr' else 'Color, font and photo will apply immediately across the site.' }}</p>
      </div>
    </div>
    """
    return render(content, current_color=current_color, current_font=current_font, current_photo=current_photo)

# ----------------------------------------
# Lancement de l'application
# ----------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    debug_env = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(host=host, port=port, debug=debug_env)
