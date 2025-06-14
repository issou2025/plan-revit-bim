# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template_string, request, redirect, url_for, session, send_from_directory

from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key_2024"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "dwg", "rvt", "docx", "xlsx", "jpg", "jpeg", "png", "gif", "zip"}

# --- Données dynamiques ---
SITE = {
    "nom": "Issoufou Abdou Chefou",
    "titre": {
        "fr": "Ingénieur en Génie Civil & BIM | Freelance",
        "en": "Civil Engineer & BIM Specialist | Freelancer"
    },
    "slogan": {
        "fr": "Vous avez un projet ? Confiez-le à un professionnel passionné.",
        "en": "Have a project? Entrust it to a passionate professional."
    },
    "photo": "https://randomuser.me/api/portraits/men/75.jpg",
    "email": "revit.issoufou@gmail.com",
    "tel": "+227 90 00 00 00",
    "whatsapp": "+227 90 00 00 00",
    "linkedin": "https://www.linkedin.com/in/issoufou-chefou",
    "adresse": {
        "fr": "Niamey, Niger (disponible à l'international)",
        "en": "Niamey, Niger (available internationally)"
    },
    "horaires": {
        "fr": "Lundi-Samedi : 8h – 19h (GMT+1)",
        "en": "Monday–Saturday: 8AM – 7PM (GMT+1)"
    },
    "couleur": "#1f87e0",
    "font": "Montserrat"
}
ANNEE = 2025

SERVICES = [
    {"titre": {"fr":"Plans d’armatures Revit", "en":"Rebar plans (Revit)"}, "desc": {"fr":"Plans d’armatures clairs et complets pour béton armé.", "en":"Clear, complete rebar plans for reinforced concrete."}, "icon": "bi-diagram-3"},
    {"titre": {"fr":"Études et plans métalliques", "en":"Steel structure studies & plans"}, "desc": {"fr":"Calculs et plans pour charpentes, hangars, structures métalliques.", "en":"Design & drawings for steel frames, hangars, metal structures."}, "icon": "bi-building"},
    {"titre": {"fr":"Modélisation BIM complète", "en":"Complete BIM modeling"}, "desc": {"fr":"Maquettes numériques, familles paramétriques, coordination.", "en":"Digital models, parametric families, project coordination."}, "icon": "bi-boxes"},
    {"titre": {"fr":"Audit et optimisation", "en":"Audit & optimization"}, "desc": {"fr":"Vérification, corrections et conseils pour réduire coûts/risques.", "en":"Checks, corrections, advice to reduce cost & risks."}, "icon": "bi-search"},
    {"titre": {"fr":"Formation/Accompagnement", "en":"Training/Support"}, "desc": {"fr":"Formation Revit ou support ponctuel pour vos équipes.", "en":"Revit training or support for your team."}, "icon": "bi-person-video3"},
]
PORTFOLIO = [
    {
        "titre": {"fr":"Résidence de standing (Niamey)", "en":"Premium Residence (Niamey)"},
        "desc": {
            "fr":"Plans de coffrage et ferraillage, modélisation Revit, synthèse et quantitatifs.",
            "en":"Formwork and rebar plans, Revit modeling, syntheses and BOQs."
        },
        "imgs": ["https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=600&q=80"],
        "fichiers": []
    }
]
ATOUTS = [
    {
        "fr":"7 ans d’expérience sur des projets variés en Afrique et à l’international.",
        "en":"7 years of experience with varied projects in Africa and abroad."
    },
    {
        "fr":"Maîtrise avancée de Revit, AutoCAD, Robot Structural Analysis.",
        "en":"Advanced skills in Revit, AutoCAD, Robot Structural Analysis."
    },
    {
        "fr":"Réactivité : réponse à toutes demandes en moins de 24h.",
        "en":"Responsive: answers to all requests in less than 24h."
    },
    {
        "fr":"Travail 100% à distance, process sécurisé, confidentialité garantie.",
        "en":"100% remote work, secured process, guaranteed confidentiality."
    },
    {
        "fr":"Respect total des délais et adaptation à vos besoins spécifiques.",
        "en":"Strict respect for deadlines, adaptable to your needs."
    },
    {
        "fr":"Conseils gratuits avant devis : je vous oriente même sans plans précis.",
        "en":"Free advice before any quote, even if you don’t have precise plans."
    },
]
MSGS = []

# --- Admin config ---
ADMIN_USER = "bacseried@gmail.com"
ADMIN_PASS = "mx23fy"
ADMIN_SECRET_URL = "issoufouachraf_2025"

LANGS = {"fr": "Français", "en": "English"}

# --- Templates ---
BASE = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <title>{{ titre_page or 'Accueil' }} | {{ site.nom }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family={{ site.font|replace(' ','+') }}:wght@700;500;400&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        html { font-size: 17px;}
        body { font-family: '{{ site.font }}', Arial, sans-serif; background: #f6faff; }
        .navbar { background: linear-gradient(90deg,{{ site.couleur }},#43e3ff 100%);}
        .navbar-brand, .nav-link { color: #fff !important;}
        .nav-link.active {color:#ffd600!important;font-weight:bold;}
        .lang-select {margin-left:1.1em;}
        .hero {
            background: linear-gradient(105deg,{{ site.couleur }} 60%, #43e3ff 100%);
            color: #fff; padding: 44px 0 33px 0;
            border-radius: 0 0 36px 36px;
            margin-bottom:32px; text-shadow: 1px 1px 8px #2227;
            box-shadow:0 4px 20px #24315e28;
        }
        .hero img { width: 125px; border-radius: 100px; margin-bottom: 13px; border: 3px solid #ffd600; box-shadow:0 4px 16px #1113;}
        .btn-contact, .btn-projet { background: #ffd600; color: #24315e; font-weight:bold; border-radius:13px;}
        .btn-contact:hover, .btn-projet:hover { background: #fff200;}
        .section-title { color: {{ site.couleur }}; margin-top:26px; margin-bottom:11px; font-weight:bold; letter-spacing:0.5px;}
        .service-card { background:#fff; border-radius:19px; box-shadow:0 1px 12px #24315e1c; padding:23px 13px; text-align:center; margin-bottom:18px;}
        .service-card i { font-size:2.2rem; color:{{ site.couleur }}; margin-bottom:9px;}
        .portfolio-img-multi{height:65px;width:85px;object-fit:cover; margin-right:7px; margin-bottom:4px; border-radius:7px; border:2px solid #eee;}
        .footer { background: #222c41; color: #fff; padding: 22px 0; margin-top: 41px;}
        .project-cta {
            background: linear-gradient(90deg,{{ site.couleur }} 60%, #ffd600 120%);
            color:#24315e; border-radius:16px; padding:23px 10px; margin:27px 0 7px 0;
            box-shadow:0 2px 15px #0288d122;
            font-size:1.08rem; font-weight:500;
        }
        .admin-link {display:none;}
        .admin-nav { background:#22223b;padding:13px; border-radius:10px; margin-bottom:10px;}
        .admin-nav a {color:#ffd600; margin:0 8px; font-weight:bold;}
        .admin-panel { background:#fff; border-radius:14px; padding:17px 8px; margin-top:10px; box-shadow:0 3px 30px #0288d116;}
        .admin-table td, .admin-table th { vertical-align:middle;}
        .admin-msg{background:#fffae0; border:1px solid #ffd600; border-radius:8px;padding:10px 16px;}
        .alert-success{font-weight:bold;}
        .reassure {font-size:1.04rem; margin-bottom:0.55em;}
        .badge-file{background:{{ site.couleur }}; color:#fff; font-size:0.93em;}
        .drag-drop-area {
            border:2px dashed #bbb;
            border-radius:10px;
            background:#f8fbff;
            text-align:center;
            padding:17px 5px;
            color:#789;
            margin-bottom:10px;
            transition: border .2s;
        }
        .drag-drop-area.dragover { border:2.2px solid {{ site.couleur }}; background:#e7f7ff;}
        @media (max-width:600px) {
            html{font-size:15px;}
            .hero{padding: 9px 0 8px 0;}
            .project-cta{padding:7px 3px;}
            .admin-panel{padding:7px 1px;}
        }
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg sticky-top">
  <div class="container">
    <a class="navbar-brand" href="{{ url_for('index') }}">{{ site.nom }}</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link {% if page=='accueil' %}active{% endif %}" href="{{ url_for('index') }}">{{ "Accueil" if lang=='fr' else "Home" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if page=='services' %}active{% endif %}" href="{{ url_for('services') }}">{{ "Services" if lang=='fr' else "Services" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if page=='portfolio' %}active{% endif %}" href="{{ url_for('portfolio') }}">{{ "Portfolio" if lang=='fr' else "Portfolio" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if page=='pourquoi' %}active{% endif %}" href="{{ url_for('pourquoi') }}">{{ "Pourquoi moi ?" if lang=='fr' else "Why me?" }}</a></li>
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
      </ul>
    </div>
  </div>
</nav>
<div class="container">
    {% block content %}{% endblock %}
</div>
<footer class="footer text-center">
  <div class="container">
    <div>
      <strong>{{ site.nom }}</strong> – {{ site.titre[lang] }}<br>
      <span>{{ site.adresse[lang] }}</span> <br>
      <span>Email: <a href="mailto:{{ site.email }}" class="text-white">{{ site.email }}</a>
      | WhatsApp: <a href="https://wa.me/{{ site.whatsapp.replace(' ','').replace('+','') }}" class="text-white">{{ site.whatsapp }}</a>
      | LinkedIn : <a href="{{ site.linkedin }}" class="text-white">Profil</a></span>
      <br><span>{{ site.horaires[lang] }}</span>
    </div>
    <div class="mt-2 small">&copy; {{ annee }} – {{ "Développé par" if lang=='fr' else "Developed by" }} {{ site.nom }}</div>
  </div>
</footer>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
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

def get_lang():
    # Session, URL param, ou défaut français
    lang = session.get('lang', 'fr')
    if lang not in LANGS: lang = 'fr'
    return lang

def render(content, **kwargs):
    lang = get_lang()
    ctx = dict(site=SITE, annee=ANNEE, lang=lang, langs=LANGS, **kwargs)
    page = BASE.replace("{% block content %}{% endblock %}", content)
    return render_template_string(page, **ctx)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_logged_in():
    return session.get("admin") == True

@app.route('/set_lang', methods=["POST"])
def set_lang():
    lang = request.form.get('lang', 'fr')
    if lang in LANGS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# ----------- SITE PUBLIC -----------

@app.route('/')
def index():
    lang = get_lang()
    content = f"""
    <div class="hero text-center">
        <img src="{{{{ site.photo }}}}" alt="portrait {{{{ site.nom }}}}">
        <h1>{{{{ site.nom }}}}</h1>
        <h3 style="margin-bottom:10px;">{{{{ site.titre[lang] }}}}</h3>
        <div class="fs-5 mb-2">{{{{ site.slogan[lang] }}}}</div>
        <div style="font-size:1.07rem;">
            <b>{"Entreprises, particuliers, architectes, porteurs de projet :" if lang=='fr' else "Companies, individuals, architects, project owners:"}</b>
            <br>
            <span class="d-block mt-1">
                <i class="bi bi-arrow-right-circle"></i> {"Vous cherchez un plan d’armature, une maquette Revit, ou un conseil pour votre construction ? " if lang=='fr' else "Looking for a rebar plan, Revit model, or construction advice? "}
                <b style="color:#ffd600;">{"Parlons-en gratuitement !" if lang=='fr' else "Let's talk for free!"}</b>
            </span>
        </div>
        <a href="{{{{ url_for('contact') }}}}" class="btn btn-contact btn-lg mt-4"><i class="bi bi-chat-left-dots"></i> {('Proposez votre projet' if lang=='fr' else 'Submit your project')}</a>
    </div>
    <div class="project-cta text-center mt-5">
        <span class="fs-5"><i class="bi bi-lightbulb"></i> {('Votre projet mérite un expert passionné !' if lang=='fr' else 'Your project deserves a passionate expert!')}</span>
        <br>
        <span>
            {('Que vous soyez un particulier, une entreprise ou un bureau d’étude, contactez-moi pour donner vie à vos idées. Je réponds à toutes les demandes sous 24h.' if lang=='fr' else 'Whether you are an individual, a company or a design office, contact me to bring your ideas to life. I answer all requests within 24h.')}
            <br>
            <a href="{{{{ url_for('contact') }}}}" class="btn btn-projet mt-3"><i class="bi bi-send"></i> {('Je décris mon projet' if lang=='fr' else 'Describe my project')}</a>
        </span>
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
                <div>{{ serv.desc[lang] }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render(content, page="services", titre_page=("Services" if get_lang() == "fr" else "Services"), services=SERVICES)

@app.route('/portfolio')
def portfolio():
    lang = get_lang()
    content = """
    <h2 class="section-title text-center">{{ "Quelques réalisations" if lang=='fr' else "Some work samples" }}</h2>
    <div class="row mt-4">
        {% for projet in portfolio %}
        <div class="col-md-6 mb-4">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title text-primary">{{ projet.titre[lang] }}</h5>
                    <div class="card-text mb-2">{{ projet.desc[lang] }}</div>
                    {% if projet.imgs %}
                      {% for img in projet.imgs %}
                        <img src="{{ img }}" class="portfolio-img-multi mb-2" alt="Projet image">
                      {% endfor %}
                    {% endif %}
                    {% if projet.fichiers %}
                      <div class="mt-2"><b>{{ "Fichiers :" if lang=='fr' else "Files:" }}</b>
                      {% for f in projet.fichiers %}
                        <a href="{{ url_for('uploaded_file', filename=f) }}" class="badge badge-file" target="_blank"><i class="bi bi-download"></i> {{ f }}</a>
                      {% endfor %}
                      </div>
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
    <h2 class="section-title text-center">{{ "Pourquoi me confier votre projet ?" if lang=='fr' else "Why work with me?" }}</h2>
    <div class="row mt-4 justify-content-center">
      <div class="col-lg-10">
        {% for at in atouts %}
        <div class="reassure"><i class="bi bi-check-circle-fill" style="color:#ffd600"></i> {{ at[lang] }}</div>
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
    msg = None
    if request.method == "POST":
        nom = request.form.get("nom")
        email = request.form.get("email")
        projet = request.form.get("projet")
        fichiers = []
        files = request.files.getlist("fichier")
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                fichiers.append(filename)
        MSGS.append({"nom": nom, "email": email, "projet": projet, "fichiers": fichiers})
        msg = (f"Merci {nom}, j'ai bien reçu votre demande et vos fichiers ! Je vous répondrai sous 24h." if lang=="fr" else f"Thank you {nom}, your request and files have been received! I will get back to you within 24h.")
    content = """
    <h2 class="section-title text-center">{{ "Votre projet commence ici" if lang=='fr' else "Start your project here" }}</h2>
    <div class="row justify-content-center mt-4">
      <div class="col-md-8">
        {% if msg %}
          <div class="alert alert-success">{{ msg }}</div>
        {% endif %}
        <form method="post" class="border rounded p-4 shadow-sm bg-white" enctype="multipart/form-data">
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
        <div class="mt-4">
          <p><strong>Email direct :</strong> <a href="mailto:{{ site.email }}">{{ site.email }}</a></p>
          <p><strong>Téléphone/WhatsApp :</strong> <a href="https://wa.me/{{ site.whatsapp.replace(' ', '').replace('+','') }}" target="_blank">{{ site.whatsapp }}</a></p>
        </div>
      </div>
    </div>
    <div class="project-cta text-center mt-5">
        <span><i class="bi bi-people"></i> {{ "Conseils gratuits avant engagement.<br>Décrivez-moi votre idée, même si votre projet n’est pas encore précis !" if lang=='fr' else "Free advice before engagement.<br>Describe your idea, even if your project is not yet precise!" }}</span>
    </div>
    """
    return render(content, page="contact", titre_page=("Contact / Projet" if lang=="fr" else "Contact / Project"), msg=msg)

# ----------- ADMIN (SECRET URL) -----------

@app.route(f'/{ADMIN_SECRET_URL}', methods=['GET', 'POST'])
def admin():
    if not admin_logged_in():
        error = None
        if request.method == "POST":
            u = request.form.get("user")
            p = request.form.get("pass")
            if u == ADMIN_USER and p == ADMIN_PASS:
                session["admin"] = True
                return redirect(url_for('admin'))
            else:
                error = "Identifiants incorrects."
        login = """
        <div class="row justify-content-center mt-5">
          <div class="col-md-4 admin-panel">
            <h4 class="mb-3 text-center"><i class="bi bi-person-gear"></i> Connexion Admin</h4>
            {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
            <form method="post">
                <input class="form-control mb-2" type="text" name="user" placeholder="Email admin" required>
                <input class="form-control mb-3" type="password" name="pass" placeholder="Mot de passe" required>
                <button class="btn btn-contact w-100" type="submit">Se connecter</button>
            </form>
          </div>
        </div>
        """
        return render(login, titre_page="Connexion admin", error=error)
    content = """
    <div class="admin-nav text-center">
      <a href="{{ url_for('admin') }}">Accueil admin</a> | 
      <a href="{{ url_for('admin_services') }}">Services</a> | 
      <a href="{{ url_for('admin_portfolio') }}">Portfolio</a> | 
      <a href="{{ url_for('admin_atouts') }}">Pourquoi moi</a> | 
      <a href="{{ url_for('admin_messages') }}">Messages reçus</a> | 
      <a href="{{ url_for('admin_site') }}">Infos site/design</a> | 
      <a href="{{ url_for('admin_logout') }}">Déconnexion</a>
    </div>
    <div class="admin-panel">
      <h4><i class="bi bi-person-gear"></i> Tableau de bord Admin</h4>
      <ul>
        <li><b>Services</b> : Ajouter, éditer ou supprimer un service proposé.</li>
        <li><b>Portfolio</b> : Ajouter, éditer ou supprimer une réalisation (plusieurs images et fichiers téléchargeables).</li>
        <li><b>Pourquoi moi</b> : Modifier vos arguments professionnels.</li>
        <li><b>Messages reçus</b> : Lire, télécharger ou supprimer tous les messages envoyés (avec tous les fichiers).</li>
        <li><b>Infos site/design</b> : Modifier toutes les infos du site, slogan, photo, couleur, police, etc.</li>
      </ul>
    </div>
    """
    return render(content, titre_page="Admin", page="admin")

@app.route(f'/{ADMIN_SECRET_URL}/logout')
def admin_logout():
    session["admin"] = False
    return redirect(url_for('admin'))

@app.route(f'/{ADMIN_SECRET_URL}/services', methods=["GET", "POST"])
def admin_services():
    if not admin_logged_in():
        return redirect(url_for('admin'))
    if request.method == "POST":
        titre_fr = request.form.get("titre_fr")
        titre_en = request.form.get("titre_en")
        desc_fr = request.form.get("desc_fr")
        desc_en = request.form.get("desc_en")
        icon = request.form.get("icon")
        if titre_fr and desc_fr and titre_en and desc_en:
            SERVICES.append({"titre": {"fr":titre_fr, "en":titre_en}, "desc": {"fr":desc_fr, "en":desc_en}, "icon": icon or "bi-star"})
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(SERVICES):
            SERVICES.pop(idx)
        return redirect(url_for('admin_services'))
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> | 
      <a href="{{ url_for('admin_services') }}">Services</a>
    </div>
    <div class="admin-panel">
      <h5>Services proposés</h5>
      <table class="table admin-table">
        <tr><th>#</th><th>Français</th><th>English</th><th>Description FR</th><th>Description EN</th><th>Icône</th><th></th></tr>
        {% for serv in services %}
          <tr>
            <td>{{ loop.index0 }}</td>
            <td>{{ serv.titre['fr'] }}</td>
            <td>{{ serv.titre['en'] }}</td>
            <td>{{ serv.desc['fr'] }}</td>
            <td>{{ serv.desc['en'] }}</td>
            <td><i class="bi {{ serv.icon }}"></i> {{ serv.icon }}</td>
            <td><a href="?del={{ loop.index0 }}" class="btn btn-danger btn-sm">Suppr.</a></td>
          </tr>
        {% endfor %}
      </table>
      <hr>
      <form method="post" class="row">
        <div class="col-md-2"><input type="text" name="titre_fr" class="form-control" placeholder="Service (FR)" required></div>
        <div class="col-md-2"><input type="text" name="titre_en" class="form-control" placeholder="Service (EN)" required></div>
        <div class="col-md-2"><input type="text" name="desc_fr" class="form-control" placeholder="Description (FR)" required></div>
        <div class="col-md-2"><input type="text" name="desc_en" class="form-control" placeholder="Description (EN)" required></div>
        <div class="col-md-2"><input type="text" name="icon" class="form-control" placeholder="Icône bi-..." value="bi-star"></div>
        <div class="col-md-2"><button class="btn btn-contact" type="submit">Ajouter</button></div>
      </form>
    </div>
    """
    return render(content, services=SERVICES, page="admin")

@app.route(f'/{ADMIN_SECRET_URL}/portfolio', methods=["GET", "POST"])
def admin_portfolio():
    if not admin_logged_in():
        return redirect(url_for('admin'))
    if request.method == "POST":
        titre_fr = request.form.get("titre_fr")
        titre_en = request.form.get("titre_en")
        desc_fr = request.form.get("desc_fr")
        desc_en = request.form.get("desc_en")
        imgs = request.form.get("imgs", "")
        imgs = [img.strip() for img in imgs.split(",") if img.strip()]
        fichiers = []
        files = request.files.getlist("fichiers")
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                fichiers.append(filename)
        if titre_fr and desc_fr and titre_en and desc_en:
            PORTFOLIO.append({"titre": {"fr":titre_fr,"en":titre_en}, "desc": {"fr":desc_fr,"en":desc_en}, "imgs": imgs, "fichiers": fichiers})
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        for f in PORTFOLIO[idx].get("fichiers", []):
            try: os.remove(os.path.join(UPLOAD_FOLDER, f))
            except: pass
        PORTFOLIO.pop(idx)
        return redirect(url_for('admin_portfolio'))
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> | 
      <a href="{{ url_for('admin_portfolio') }}">Portfolio</a>
    </div>
    <div class="admin-panel">
      <h5>Réalisations du portfolio</h5>
      <table class="table admin-table">
        <tr><th>#</th><th>Français</th><th>English</th><th>Description FR</th><th>Description EN</th><th>Images</th><th>Fichiers</th><th></th></tr>
        {% for proj in portfolio %}
          <tr>
            <td>{{ loop.index0 }}</td>
            <td>{{ proj.titre['fr'] }}</td>
            <td>{{ proj.titre['en'] }}</td>
            <td>{{ proj.desc['fr'] }}</td>
            <td>{{ proj.desc['en'] }}</td>
            <td>
                {% for img in proj.imgs %}
                  <img src="{{ img }}" style="width:45px;height:32px;object-fit:cover;margin-right:3px;border-radius:6px;">
                {% endfor %}
            </td>
            <td>
                {% for f in proj.fichiers %}
                  <a href="{{ url_for('uploaded_file', filename=f) }}" class="badge badge-file" target="_blank">{{ f }}</a>
                {% endfor %}
            </td>
            <td><a href="?del={{ loop.index0 }}" class="btn btn-danger btn-sm">Suppr.</a></td>
          </tr>
        {% endfor %}
      </table>
      <hr>
      <form method="post" class="row" enctype="multipart/form-data">
        <div class="col-md-2"><input type="text" name="titre_fr" class="form-control" placeholder="Titre FR" required></div>
        <div class="col-md-2"><input type="text" name="titre_en" class="form-control" placeholder="Title EN" required></div>
        <div class="col-md-2"><input type="text" name="desc_fr" class="form-control" placeholder="Description FR" required></div>
        <div class="col-md-2"><input type="text" name="desc_en" class="form-control" placeholder="Description EN" required></div>
        <div class="col-md-2"><input type="text" name="imgs" class="form-control" placeholder="URLs images, virgule"></div>
        <div class="col-md-1"><input type="file" name="fichiers" class="form-control" multiple></div>
        <div class="col-md-1"><button class="btn btn-contact" type="submit">Ajouter</button></div>
      </form>
      <div class="small mt-1">Pour images, colle des URLs (ex: https://...img1.jpg, https://...img2.jpg)</div>
    </div>
    """
    return render(content, portfolio=PORTFOLIO, page="admin")

@app.route(f'/{ADMIN_SECRET_URL}/atouts', methods=["GET", "POST"])
def admin_atouts():
    if not admin_logged_in():
        return redirect(url_for('admin'))
    if request.method == "POST":
        at_fr = request.form.get("atout_fr")
        at_en = request.form.get("atout_en")
        if at_fr and at_en:
            ATOUTS.append({"fr":at_fr, "en":at_en})
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(ATOUTS):
            ATOUTS.pop(idx)
        return redirect(url_for('admin_atouts'))
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> | 
      <a href="{{ url_for('admin_atouts') }}">Pourquoi moi</a>
    </div>
    <div class="admin-panel">
      <h5>Arguments / Pourquoi me confier votre projet</h5>
      <ul>
        {% for at in atouts %}
        <li>
          <b>FR :</b> {{ at['fr'] }} <br><b>EN :</b> {{ at['en'] }}
          <a href="?del={{ loop.index0 }}" class="btn btn-danger btn-sm">Suppr.</a>
        </li>
        {% endfor %}
      </ul>
      <form method="post" class="row">
        <div class="col-md-5"><input type="text" name="atout_fr" class="form-control" placeholder="Argument FR" required></div>
        <div class="col-md-5"><input type="text" name="atout_en" class="form-control" placeholder="Argument EN" required></div>
        <div class="col-md-2"><button class="btn btn-contact" type="submit">Ajouter</button></div>
      </form>
    </div>
    """
    return render(content, atouts=ATOUTS, page="admin")

@app.route(f'/{ADMIN_SECRET_URL}/messages', methods=["GET", "POST"])
def admin_messages():
    if not admin_logged_in():
        return redirect(url_for('admin'))
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        for f in MSGS[idx].get("fichiers", []):
            try: os.remove(os.path.join(UPLOAD_FOLDER, f))
            except: pass
        MSGS.pop(idx)
        return redirect(url_for('admin_messages'))
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> | 
      <a href="{{ url_for('admin_messages') }}">Messages reçus</a>
    </div>
    <div class="admin-panel">
      <h5>Messages reçus via le formulaire</h5>
      {% if msgs %}
      <table class="table admin-table">
        <tr><th>#</th><th>Nom</th><th>Email/WhatsApp</th><th>Projet</th><th>Fichiers</th><th></th></tr>
        {% for msg in msgs %}
        <tr>
          <td>{{ loop.index0 }}</td>
          <td>{{ msg.nom }}</td>
          <td>
            {{ msg.email }}
            {% if msg.email %}
              <a href="mailto:{{ msg.email }}" title="Répondre" class="btn btn-sm btn-outline-primary ms-1"><i class="bi bi-envelope"></i></a>
            {% endif %}
          </td>
          <td>{{ msg.projet }}</td>
          <td>
            {% for f in msg.fichiers %}
              <a href="{{ url_for('uploaded_file', filename=f) }}" class="badge badge-file" target="_blank">{{ f }}</a>
            {% endfor %}
          </td>
          <td><a href="?del={{ loop.index0 }}" class="btn btn-danger btn-sm">Suppr.</a></td>
        </tr>
        {% endfor %}
      </table>
      {% else %}
      <div class="admin-msg">{{ "Aucun message pour l’instant." if lang=='fr' else "No messages yet." }}</div>
      {% endif %}
    </div>
    """
    return render(content, msgs=MSGS, page="admin")

@app.route(f'/{ADMIN_SECRET_URL}/site', methods=["GET", "POST"])
def admin_site():
    if not admin_logged_in():
        return redirect(url_for('admin'))
    keys = ["nom","photo","email","tel","whatsapp","linkedin","couleur","font"]
    keys_trans = ["titre","slogan","adresse","horaires"]
    if request.method == "POST":
        for k in keys:
            v = request.form.get(k)
            if v:
                SITE[k] = v
        for k in keys_trans:
            fr = request.form.get(f"{k}_fr")
            en = request.form.get(f"{k}_en")
            if fr and en:
                SITE[k] = {"fr":fr, "en":en}
    content = """
    <div class="admin-nav text-center mb-3">
      <a href="{{ url_for('admin') }}">Accueil admin</a> | 
      <a href="{{ url_for('admin_site') }}">Infos site/design</a>
    </div>
    <div class="admin-panel">
      <h5>Modifier les coordonnées / design du site</h5>
      <form method="post">
        <div class="row mb-2">
          <div class="col-md-3"><label>Nom :</label><input type="text" name="nom" class="form-control" value="{{ site.nom }}"></div>
          <div class="col-md-3"><label>Titre FR :</label><input type="text" name="titre_fr" class="form-control" value="{{ site.titre['fr'] }}"></div>
          <div class="col-md-3"><label>Titre EN :</label><input type="text" name="titre_en" class="form-control" value="{{ site.titre['en'] }}"></div>
          <div class="col-md-3"><label>Photo (url) :</label><input type="text" name="photo" class="form-control" value="{{ site.photo }}"></div>
        </div>
        <div class="row mb-2">
          <div class="col-md-3"><label>Email :</label><input type="text" name="email" class="form-control" value="{{ site.email }}"></div>
          <div class="col-md-3"><label>Téléphone :</label><input type="text" name="tel" class="form-control" value="{{ site.tel }}"></div>
          <div class="col-md-3"><label>WhatsApp :</label><input type="text" name="whatsapp" class="form-control" value="{{ site.whatsapp }}"></div>
          <div class="col-md-3"><label>LinkedIn :</label><input type="text" name="linkedin" class="form-control" value="{{ site.linkedin }}"></div>
        </div>
        <div class="row mb-2">
          <div class="col-md-3"><label>Adresse FR :</label><input type="text" name="adresse_fr" class="form-control" value="{{ site.adresse['fr'] }}"></div>
          <div class="col-md-3"><label>Adresse EN :</label><input type="text" name="adresse_en" class="form-control" value="{{ site.adresse['en'] }}"></div>
          <div class="col-md-3"><label>Horaires FR :</label><input type="text" name="horaires_fr" class="form-control" value="{{ site.horaires['fr'] }}"></div>
          <div class="col-md-3"><label>Horaires EN :</label><input type="text" name="horaires_en" class="form-control" value="{{ site.horaires['en'] }}"></div>
        </div>
        <div class="row mb-2">
          <div class="col-md-3"><label>Slogan FR :</label><input type="text" name="slogan_fr" class="form-control" value="{{ site.slogan['fr'] }}"></div>
          <div class="col-md-3"><label>Slogan EN :</label><input type="text" name="slogan_en" class="form-control" value="{{ site.slogan['en'] }}"></div>
          <div class="col-md-3"><label>Couleur principale :</label><input type="color" name="couleur" class="form-control form-control-color" value="{{ site.couleur }}"></div>
          <div class="col-md-3"><label>Police Google :</label><input type="text" name="font" class="form-control" value="{{ site.font }}"></div>
        </div>
        <button class="btn btn-contact" type="submit">Enregistrer les modifications</button>
      </form>
      <div class="small mt-1">Pour la police, exemple : Montserrat, Poppins, Open Sans…</div>
    </div>
    """
    return render(content, page="admin")
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

