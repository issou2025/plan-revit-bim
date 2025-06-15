# -*- coding: utf-8 -*-
import os
import io
import json
import zipfile
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory, send_file, abort, flash

from werkzeug.utils import secure_filename

# ----------------------------------------
# Configuration de base
# ----------------------------------------
app = Flask(__name__)
# En production, définissez SECRET_KEY via variable d'environnement pour sécurité
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_2024")

# Dossier des uploads
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Fichiers de persistance
MSG_FILE = "messages.json"
TRAFFIC_FILE = "traffic.json"

# Autorisations d'extensions upload
ALLOWED_EXTENSIONS = {"pdf", "dwg", "rvt", "docx", "xlsx", "jpg", "jpeg", "png", "gif", "zip"}

# Fichier de logs
LOG_FILE = "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------
# Chargement / sauvegarde JSON
# ----------------------------------------
def load_json_file(path):
    """Charge un JSON comme liste, ou retourne [] si échec."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                logging.warning(f"{path} ne contient pas une liste, réinitialisation.")
        except Exception as e:
            logging.error(f"Erreur lecture {path}: {e}")
    return []

def save_json_file(path, data):
    """Sauvegarde la liste data dans le fichier JSON."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erreur écriture {path}: {e}")

# Charger au démarrage
MSGS = load_json_file(MSG_FILE)
# Assurer champ status et timestamp si manquants
for m in MSGS:
    if 'status' not in m:
        m['status'] = 'new'
    if 'timestamp' not in m:
        m['timestamp'] = ""

TRAFFIC = load_json_file(TRAFFIC_FILE)
# TRAFFIC entries: dicts {"timestamp": "YYYY-MM-DD HH:MM:SS", "path": "/...", "method": "GET", "remote_addr": "IP"}

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
        "en": "Have a project? Entrust it to a passionate professional."
    },
    "photo": "https://randomuser.me/api/portraits/men/75.jpg",
    "email": "entreprise2rc@gmail.com",  # Adresse utilisée pour notifications email
    "tel": "+227 96 38 08 77",
    "whatsapp": "+227 96 38 08 77",
    "linkedin": "https://www.linkedin.com/in/issoufou-chefou",
    "adresse": {
        "fr": "Niamey, Niger (disponible à l'international)",
        "en": "Niamey, Niger (available internationally)"
    },
    "horaires": {
        "fr": "Lundi-Samedi : 8h – 19h (GMT+1)",
        "en": "Monday–Saturday: 8AM – 7PM (GMT+1)"
    },
    "couleur": "#1f87e0",
    "font": "Montserrat"
}
ANNEE = 2025

# Structures initiales : Services, Portfolio, Atouts
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
ADMIN_USER = "bacseried@gmail.com"
ADMIN_PASS = "mx23fy"
ADMIN_SECRET_URL = "issoufouachraf_2025"  # À adapter si vous voulez un autre chemin
LANGS = {"fr": "Français", "en": "English"}

# ----------------------------------------
# Configuration SMTP pour notifications email
# ----------------------------------------
MAIL_SERVER = os.environ.get("MAIL_SERVER")
MAIL_PORT = int(os.environ.get("MAIL_PORT", 0)) if os.environ.get("MAIL_PORT") else None
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "False").lower() in ("true", "1", "yes")
MAIL_FROM = os.environ.get("MAIL_FROM", MAIL_USERNAME)
MAIL_TO = os.environ.get("MAIL_TO", SITE.get("email"))

def send_email_notification(subject: str, body: str):
    """Envoie un email si configuration SMTP présente."""
    if not (MAIL_SERVER and MAIL_PORT and MAIL_USERNAME and MAIL_PASSWORD and MAIL_TO):
        logging.info("SMTP non configuré, email non envoyé.")
        return
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = MAIL_FROM
        msg['To'] = MAIL_TO
        msg.set_content(body)
        server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
        if MAIL_USE_TLS:
            server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logging.info("Notification email envoyée.")
    except Exception as e:
        logging.error(f"Erreur envoi email: {e}")

# ----------------------------------------
# Template HTML de base (BASE)
# ----------------------------------------
# Utilise Bootstrap 5.3, icônes Bootstrap Icons.
# Inclut la gestion des flashs et un drag-drop simplifié.
BASE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <title>{{ titre_page or 'Accueil' }} | {{ site.nom }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Google Font -->
    <link href="https://fonts.googleapis.com/css2?family={{ site.font|replace(' ','+') }}:wght@700;500;400&display=swap" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        html { font-size: 17px; scroll-behavior: smooth; }
        body {
            font-family: '{{ site.font }}', Arial, sans-serif;
            background: {% if session.get('dark_mode') %}#121212{% else %}#f6faff{% endif %};
            color: {% if session.get('dark_mode') %}#e0e0e0{% else %}#212529{% endif %};
            margin: 0; padding: 0;
        }
        a { color: {% if session.get('dark_mode') %}#66b2ff{% else %}#1f87e0{% endif %}; }
        .navbar, .footer { transition: background 0.3s; }
        /* Navbar */
        .navbar { background: linear-gradient(90deg,{{ site.couleur }},#43e3ff 100%); }
        .navbar-brand, .nav-link { color: #fff !important; }
        .nav-link.active { color:#ffd600!important; font-weight:bold; }
        .lang-select { margin-left:1.1em; }
        .dark-toggle { cursor: pointer; color: #fff; margin-left: 1rem; }
        /* Hero section */
        .hero {
            background: linear-gradient(105deg,{{ site.couleur }} 60%, #43e3ff 100%), url('https://images.unsplash.com/photo-1581091870627-3fd7fddc9575?auto=format&fit=crop&w=1350&q=80') no-repeat center/cover;
            color: #fff; padding: 80px 0 60px 0;
            border-radius: 0 0 36px 36px;
            margin-bottom:32px; text-shadow: 1px 1px 8px #0008;
            box-shadow:0 4px 20px #0006; position: relative;
        }
        .hero::before {
            content: "";
            position: absolute; top:0; left:0; width:100%; height:100%;
            background: rgba(0,0,0,0.4); border-radius: 0 0 36px 36px;
        }
        .hero .hero-content { position: relative; z-index: 1; }
        .hero img {
            width: 140px; border-radius: 100px; margin-bottom: 15px;
            border: 3px solid #ffd600; box-shadow:0 4px 16px #0008;
        }
        .btn-contact, .btn-projet, .btn-admin {
            background: #ffd600; color: #24315e; font-weight:bold; border-radius:13px;
            transition: transform 0.2s, background 0.2s;
        }
        .btn-contact:hover, .btn-projet:hover, .btn-admin:hover {
            background: #fff200; transform: translateY(-2px);
        }
        /* Section titles */
        .section-title {
            color: {{ site.couleur }}; margin-top:26px; margin-bottom:18px; font-weight:bold; letter-spacing:0.5px;
            position: relative; display: inline-block;
        }
        .section-title::after {
            content: ""; display: block; width: 50px; height: 3px;
            background: {{ site.couleur }}; margin: 8px auto 0; border-radius: 2px;
        }
        /* Service cards */
        .service-card {
            background: {% if session.get('dark_mode') %}#1e1e1e{% else %}#fff{% endif %};
            border-radius:19px; box-shadow:0 1px 12px #24315e1c;
            padding:23px 13px; text-align:center; margin-bottom:18px;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .service-card:hover {
            transform: translateY(-5px); box-shadow:0 4px 20px rgba(0,0,0,0.2);
        }
        .service-card i {
            font-size:2.2rem; color:{{ site.couleur }}; margin-bottom:9px;
        }
        /* Portfolio cards */
        .card-portfolio {
            border: none; border-radius: 15px; overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s;
            background: {% if session.get('dark_mode') %}#1e1e1e{% else %}#fff{% endif %};
            color: {% if session.get('dark_mode') %}#e0e0e0{% else %}#212529{% endif %};
        }
        .card-portfolio:hover {
            transform: translateY(-5px); box-shadow:0 4px 20px rgba(0,0,0,0.2);
        }
        .portfolio-img-multi {
            height:65px; width:85px; object-fit:cover;
            margin-right:7px; margin-bottom:4px; border-radius:7px; border:2px solid #eee;
        }
        /* Footer */
        .footer { background: #222c41; color: #fff; padding: 30px 0; margin-top: 0; }
        .footer a { color: #ffd600; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
        .project-cta {
            background: linear-gradient(90deg,{{ site.couleur }} 60%, #ffd600 120%);
            color:#24315e; border-radius:16px; padding:23px 10px; margin:27px 0 7px 0;
            box-shadow:0 2px 15px #0288d122; font-size:1.08rem; font-weight:500; text-align: center;
        }
        /* Admin panel */
        .admin-nav { background:#22223b; padding:10px; border-radius:10px; margin-bottom:10px; }
        .admin-nav a { color:#ffd600; margin:0 8px; font-weight:bold; }
        .admin-panel {
            background:{% if session.get('dark_mode') %}#1e1e1e{% else %}#fff{% endif %};
            border-radius:14px; padding:17px 8px; margin-top:10px;
            box-shadow:0 3px 30px #0288d116;
            color: {% if session.get('dark_mode') %}#e0e0e0{% else %}#212529{% endif %};
        }
        .admin-table td, .admin-table th { vertical-align:middle; color: inherit; }
        .admin-msg { background:#fffae0; border:1px solid #ffd600; border-radius:8px; padding:10px 16px; }
        /* Contact form drag-drop */
        .drag-drop-area {
            border:2px dashed #bbb; border-radius:10px; background:#f8fbff;
            text-align:center; padding:17px 5px; color:#789; margin-bottom:10px;
            transition: border .2s, background .2s;
        }
        .drag-drop-area.dragover { border:2.2px solid {{ site.couleur }}; background:#e7f7ff; }
        /* Table warning for unread */
        .table-warning { background-color: #fff3cd !important; }
        @media (max-width:600px) {
            html { font-size:15px; }
            .hero { padding: 40px 0 30px 0; }
            .project-cta { padding:7px 3px; }
            .admin-panel { padding:7px 1px; }
        }
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
// Gestion du drag & drop simplifié pour le formulaire contact
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
# Fonctions utilitaires Flask
# ----------------------------------------
def get_lang():
    lang = session.get('lang', 'fr')
    if lang not in LANGS:
        lang = 'fr'
    return lang

def render(content, **kwargs):
    lang = get_lang()
    ctx = dict(site=SITE, annee=ANNEE, lang=lang, langs=LANGS, **kwargs)
    page = BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, **ctx)

def admin_logged_in():
    return session.get("admin") is True

# ----------------------------------------
# Route toggle dark mode
# ----------------------------------------
@app.route('/toggle_dark')
def toggle_dark():
    current = session.get('dark_mode', False)
    session['dark_mode'] = not current
    ref = request.referrer or url_for('index')
    return redirect(ref)

# ----------------------------------------
# Traçage du trafic : before_request
# ----------------------------------------
@app.before_request
def log_traffic():
    path = request.path or ""
    ignore_prefixes = [
        f"/{ADMIN_SECRET_URL}", "/static", "/favicon.ico", "/sitemap.xml"
    ]
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
    content = f"""
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
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    lang = get_lang()
    if request.method == "POST":
        # Honeypot anti-spam
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
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
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
        # Notification email si configuré
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
    # Dashboard admin avec analytics et traffic
    total_msgs = len(MSGS)
    unread_msgs = sum(1 for m in MSGS if m.get("status") == "new")
    total_services = len(SERVICES)
    total_portfolio = len(PORTFOLIO)
    total_atouts = len(ATOUTS)
    total_traffic = len(TRAFFIC)
    today = datetime.now().strftime("%Y-%m-%d")
    visits_today = sum(1 for t in TRAFFIC if t.get("timestamp", "").startswith(today))
    content = """
    <div class="admin-nav text-center">
      <a href="{{ url_for('admin') }}">Accueil admin</a> |
      <a href="{{ url_for('admin_services') }}">Services</a> |
      <a href="{{ url_for('admin_portfolio') }}">Portfolio</a> |
      <a href="{{ url_for('admin_atouts') }}">Pourquoi moi</a> |
      <a href="{{ url_for('admin_messages') }}">Messages reçus{% if unread_msgs>0 %} ({{ unread_msgs }}){% endif %}</a> |
      <a href="{{ url_for('admin_analytics') }}">Analytics</a> |
      <a href="{{ url_for('admin_traffic') }}">Traffic</a> |
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
                  visits_today=visits_today)

@app.route(f'/{ADMIN_SECRET_URL}/logout')
def admin_logout():
    session["admin"] = False
    flash("Déconnecté.", "info")
    return redirect(url_for('admin'))

# --- Gestion des services via admin (CRUD complet) ---
@app.route(f'/{ADMIN_SECRET_URL}/services', methods=["GET", "POST"])
def admin_services():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    # GET param edit: index à éditer
    edit_idx = request.args.get("edit")
    # POST: création ou mise à jour
    if request.method == "POST":
        titre_fr = request.form.get("titre_fr", "").strip()
        titre_en = request.form.get("titre_en", "").strip()
        desc_fr = request.form.get("desc_fr", "").strip()
        desc_en = request.form.get("desc_en", "").strip()
        icon = request.form.get("icon", "").strip() or "bi-star"
        if titre_fr and titre_en and desc_fr and desc_en:
            if request.form.get("edit_idx") is not None and request.form.get("edit_idx").isdigit():
                idx = int(request.form.get("edit_idx"))
                if 0 <= idx < len(SERVICES):
                    SERVICES[idx] = {
                        "titre": {"fr": titre_fr, "en": titre_en},
                        "desc": {"fr": desc_fr, "en": desc_en},
                        "icon": icon
                    }
                    flash("Service mis à jour.", "success")
                else:
                    flash("Index de service invalide.", "danger")
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
    # Suppression
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(SERVICES):
            SERVICES.pop(idx)
            flash("Service supprimé.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_services'))
    # Pré-remplir si édition
    service_to_edit = None
    if edit_idx and edit_idx.isdigit():
        idx = int(edit_idx)
        if 0 <= idx < len(SERVICES):
            service_to_edit = SERVICES[idx]
        else:
            flash("Index invalide pour édition.", "warning")
    # Rendu template
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

# --- Gestion du portfolio via admin (CRUD complet) ---
@app.route(f'/{ADMIN_SECRET_URL}/portfolio', methods=["GET", "POST"])
def admin_portfolio():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    edit_idx = request.args.get("edit")
    # POST: création ou mise à jour
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
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                fichiers_nouveaux.append(filename)
        fichiers = fichiers_existants + fichiers_nouveaux
        if titre_fr and titre_en and desc_fr and desc_en:
            if request.form.get("edit_idx") and request.form.get("edit_idx").isdigit():
                idx = int(request.form.get("edit_idx"))
                if 0 <= idx < len(PORTFOLIO):
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
    # Suppression
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(PORTFOLIO):
            # supprimer fichiers associés
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
    # Pré-remplir si édition
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

# --- Gestion des atouts / arguments via admin (CRUD complet) ---
@app.route(f'/{ADMIN_SECRET_URL}/atouts', methods=["GET", "POST"])
def admin_atouts():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    edit_idx = request.args.get("edit")
    # POST: création ou mise à jour
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
                    flash("Index invalide pour mise à jour.", "danger")
            else:
                ATOUTS.append({"fr": at_fr, "en": at_en})
                flash("Nouvel argument ajouté.", "success")
        else:
            flash("Les deux champs (FR et EN) sont requis.", "warning")
        return redirect(url_for('admin_atouts'))
    # Suppression
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(ATOUTS):
            ATOUTS.pop(idx)
            flash("Argument supprimé.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_atouts'))
    # Pré-remplir si édition
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
      <a href="{{ url_for('admin_atouts') }}">Pourquoi moi</a>
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

# --- Gestion des messages reçus via admin, avec options avancées ---
@app.route(f'/{ADMIN_SECRET_URL}/messages', methods=["GET", "POST"])
@app.route(f'/{ADMIN_SECRET_URL}/messages/')  # prise en charge avec slash terminal
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

    # Toggle status
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
              <!-- Bouton Voir le détail -->
              <a href="{{ url_for('view_message', idx=idx) }}" class="btn btn-sm btn-primary">Voir</a>
              <!-- Toggle lu/non lu -->
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

# Route détail message
@app.route(f'/{ADMIN_SECRET_URL}/messages/view/<int:idx>', methods=['GET', 'POST'])
def view_message(idx):
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
        return redirect(url_for('admin'))
    if not (0 <= idx < len(MSGS)):
        flash("Index de message invalide.", "danger")
        return redirect(url_for('admin_messages'))
    msg = MSGS[idx]
    # Si admin clique sur form pour toggler le statut
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

# ----------------------------------------
# Analytics route
# ----------------------------------------
@app.route(f'/{ADMIN_SECRET_URL}/analytics')
def admin_analytics():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
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
                  sorted_dates=sorted_dates,
                  page="admin_analytics")

# ----------------------------------------
# Télécharger tout le dossier uploads en ZIP
# ----------------------------------------
@app.route(f'/{ADMIN_SECRET_URL}/download_uploads')
def download_all_uploads():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
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

# ----------------------------------------
# Gestion du trafic via admin
# ----------------------------------------
@app.route(f'/{ADMIN_SECRET_URL}/traffic')
def admin_traffic():
    if not admin_logged_in():
        flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
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
    start = (page-1)*per_page
    end = start + per_page
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

# ----------------------------------------
# Sitemap (fonctionnalité SEO)
# ----------------------------------------
@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    base_url = request.url_root.strip('/')
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

# ----------------------------------------
# Favicon
# ----------------------------------------
@app.route('/favicon.ico')
def favicon():
    return abort(404)

# ----------------------------------------
# Lancement de l'application
# ----------------------------------------
if __name__ == '__main__':
    # Pour debug, vous pouvez afficher la liste des routes :
    # with app.test_request_context():
    #     print("Routes disponibles :")
    #     for rule in app.url_map.iter_rules():
    #         print(rule)
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    debug_env = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
    # En production, DEBUG=False par défaut
    app.run(host=host, port=port, debug=debug_env)
