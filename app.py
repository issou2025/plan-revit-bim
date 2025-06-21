# -*- coding: utf-8 -*-
import os
import io
import json
import zipfile
import logging
from datetime import datetime
from flask import (
    Flask, render_template, render_template_string, request, redirect, url_for,
    session, send_from_directory, send_file, abort, flash, Response
)
from werkzeug.utils import secure_filename
from jinja2 import DictLoader
from functools import wraps

# ----------------------------------------
# CONFIGURATION DE BASE
# ----------------------------------------
# Dossier pour stocker uploads et JSON persistants
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
# Chemins JSON
MSG_FILE = os.environ.get("MSG_FILE_PATH", os.path.join(UPLOAD_FOLDER, "messages.json"))
TRAFFIC_FILE = os.environ.get("TRAFFIC_FILE_PATH", os.path.join(UPLOAD_FOLDER, "traffic.json"))
ROTATOR_FILE = os.environ.get("ROTATOR_FILE_PATH", os.path.join(UPLOAD_FOLDER, "rotator.json"))
CONFIG_FILE = os.environ.get("CONFIG_FILE_PATH", os.path.join(UPLOAD_FOLDER, "config.json"))
GALLERY_FILE = os.environ.get("GALLERY_FILE_PATH", os.path.join(UPLOAD_FOLDER, "gallery.json"))

# Admin credentials (à sécuriser via variables d’environnement en production)
ADMIN_USER = os.environ.get("ADMIN_USER", "bacseried@gmail.com")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "mx23fy")
# URL secret pour l’admin (changer en production)
ADMIN_SECRET_URL = os.environ.get("ADMIN_SECRET_URL", "issoufouachraf_2025")

# Extensions autorisées pour upload
ALLOWED_EXTENSIONS = {"pdf", "dwg", "rvt", "docx", "xlsx", "jpg", "jpeg", "png", "gif", "zip",
                      "mp4", "webm", "ogg"}
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
PDF_EXTENSIONS = {"pdf"}
VIDEO_EXTENSIONS = {"mp4", "webm", "ogg"}

# Application Flask
app = Flask(__name__)
# Clé secrète pour session/flash (à personnaliser en production)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_key_2024")

# Logging
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
# FONCTIONS UTILITAIRES
# ----------------------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_json_file(path, expect_dict=False):
    """
    Charge un fichier JSON. Si absent ou invalide, crée un fichier par défaut ([] ou {}).
    expect_dict=True pour un dict, sinon pour une liste.
    """
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if expect_dict:
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
    # Création du dossier parent si besoin
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception as e:
            logging.error(f"Impossible de créer dossier parent {parent}: {e}")
    default = {} if expect_dict else []
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erreur création initiale de {path}: {e}")
    return default

def save_json_file(path, data):
    """
    Sauvegarde data dans path. Crée les dossiers parents si besoin.
    """
    try:
        parent = os.path.dirname(path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erreur écriture {path}: {e}")

def send_email_notification(subject: str, body: str):
    # Stub d'envoi d’e-mail : à remplacer par implémentation pro si nécessaire
    logging.info(f"[Notification stub] Sujet: {subject} | Corps: {body}")

def admin_login_required(f):
    """
    Décorateur pour protéger les routes admin.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Veuillez vous connecter pour accéder au panneau admin.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ----------------------------------------
# CHARGEMENT DES DONNÉES PERSISTANTES AU DÉMARRAGE
# ----------------------------------------
# Création dossier d’uploads si nécessaire
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Messages de contact
MSGS = load_json_file(MSG_FILE, expect_dict=False)
if isinstance(MSGS, list):
    for m in MSGS:
        if 'status' not in m:
            m['status'] = 'new'
        if 'timestamp' not in m:
            m['timestamp'] = ""
else:
    MSGS = []

# Trafic logs
TRAFFIC = load_json_file(TRAFFIC_FILE, expect_dict=False)
if not isinstance(TRAFFIC, list):
    TRAFFIC = []

# Carousel items
ROTATOR_ITEMS = load_json_file(ROTATOR_FILE, expect_dict=False)
if not isinstance(ROTATOR_ITEMS, list):
    ROTATOR_ITEMS = []

# Config thème (dict)
config_theme = load_json_file(CONFIG_FILE, expect_dict=True)
# Valeurs par défaut si non présentes
default_color = "#E91E63"     # magenta vif par défaut
default_secondary = "#FF5722" # orange vif
default_accent = "#4CAF50"    # vert vif
default_font = "Montserrat"
default_photo = "https://randomuser.me/api/portraits/men/75.jpg"
theme_color = config_theme.get("couleur", default_color)
theme_secondary = config_theme.get("secondary", default_secondary)
theme_accent = config_theme.get("accent", default_accent)
theme_font = config_theme.get("font", default_font)
theme_photo = config_theme.get("photo", default_photo)

# Galerie items
GALLERY_ITEMS = load_json_file(GALLERY_FILE, expect_dict=False)
if not isinstance(GALLERY_ITEMS, list):
    GALLERY_ITEMS = []

# Variables globales du site
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
    "photo": theme_photo,
    "email": "entreprise2rc@gmail.com",
    "tel": "+227 96 38 08 77",
    "whatsapp": "+227 96 38 08 77",
    # Mise à jour du lien LinkedIn selon votre indication :
    "linkedin": "https://www.linkedin.com/in/abdou-chefou-issoufou-99555684",
    "adresse": {
        "fr": "Niamey, Niger (disponible à l'international)",
        "en": "Niamey, Niger (available internationally)"
    },
    "horaires": {
        "fr": "Lundi–Samedi : 8h – 19h (GMT+1)",
        "en": "Monday–Saturday: 8AM – 7PM (GMT+1)"
    },
    "couleur": theme_color,
    "secondary": theme_secondary,
    "accent": theme_accent,
    "font": theme_font
}
ANNEE = datetime.now().year

# Services initiaux
SERVICES = [
    {"titre": {"fr": "Plans d'armatures Revit", "en": "Rebar plans (Revit)"},
     "desc": {"fr": "Plans d'armatures clairs et complets pour béton armé.",
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

# Portfolio initial
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

# Atouts initiaux
ATOUTS = [
    {"fr": "7 ans d'expérience sur des projets variés en Afrique et à l'international.",
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
     "en": "Free advice before any quote, even if you don't have precise plans."},
]

# ----------------------------------------
# INJECTION DE VARIABLES GLOBALES DANS JINJA
# ----------------------------------------
@app.context_processor
def inject_global_vars():
    lang = session.get("lang", "fr")
    return {
        "site": SITE,
        "annee": ANNEE,
        "langs": {"fr": "Français", "en": "English"},
        "lang": lang,
        "SERVICES": SERVICES,
        "PORTFOLIO": PORTFOLIO,
        "ATOUTS": ATOUTS,
        "ROTATOR_ITEMS": ROTATOR_ITEMS,
        "GALLERY_ITEMS": GALLERY_ITEMS
    }

# ----------------------------------------
# LOGGING DU TRAFIC (GET/POST) pour analytics
# ----------------------------------------
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
# GESTION DE LA LANGUE
# ----------------------------------------
@app.route('/set_lang', methods=["POST"])
def set_lang():
    lang = request.form.get("lang")
    if lang in ("fr", "en"):
        session["lang"] = lang
    return redirect(request.referrer or url_for('index'))

# ----------------------------------------
# TOGGLE DARK MODE
# ----------------------------------------
@app.route('/toggle_dark')
def toggle_dark():
    session['dark_mode'] = not session.get('dark_mode', False)
    return redirect(request.referrer or url_for('index'))

# ----------------------------------------
# ROUTES PUBLIQUES
# ----------------------------------------
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/services')
def services():
    return render_template("services.html", titre_page="Services")

@app.route('/portfolio')
def portfolio():
    return render_template("portfolio.html", titre_page="Portfolio")

@app.route('/galeries')
def galeries():
    return render_template("galleries.html", titre_page="Galeries")

@app.route('/pourquoi')
def pourquoi():
    return render_template("pourquoi.html", titre_page="Pourquoi moi ?")

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        nom = request.form.get("nom", "").strip()
        email = request.form.get("email", "").strip()
        sujet = request.form.get("sujet", "").strip()
        message = request.form.get("message", "").strip()
        fichiers_info = []
        files = request.files.getlist("fichiers")
        for file in files:
            if file and file.filename:
                if allowed_file(file.filename):
                    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(save_path)
                    fichiers_info.append(filename)
                else:
                    flash(f"Fichier non autorisé : {file.filename}", "warning")
        msg_obj = {
            "nom": nom,
            "email": email,
            "sujet": sujet,
            "message": message,
            "fichiers": fichiers_info,
            "status": "new",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        MSGS.append(msg_obj)
        save_json_file(MSG_FILE, MSGS)
        send_email_notification(f"Nouveau message: {sujet}", f"De {nom} <{email}>: {message}")
        flash(("Message envoyé avec succès!" if session.get("lang","fr")=="fr" else "Message sent successfully!"), "success")
        return redirect(url_for('contact'))
    return render_template("contact.html", titre_page="Contact")

# ----------------------------------------
# ADMIN LOGIN / LOGOUT
# ----------------------------------------
@app.route(f'/{ADMIN_SECRET_URL}/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get("username", "")
        pwd = request.form.get("password", "")
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session['admin_logged_in'] = True
            flash("Connecté en tant qu’admin.", "success")
            return redirect(url_for('admin_index'))
        else:
            flash("Identifiants invalides.", "danger")
            return redirect(url_for('admin_login'))
    return render_template("admin/login.html", titre_page="Admin Login")

@app.route(f'/{ADMIN_SECRET_URL}/logout')
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Déconnecté.", "info")
    return redirect(url_for('admin_login'))

# ----------------------------------------
# ROUTES ADMIN (protégées)
# ----------------------------------------
@app.route(f'/{ADMIN_SECRET_URL}')
@admin_login_required
def admin_index():
    total_msgs = len(MSGS)
    unread_msgs = sum(1 for m in MSGS if m.get("status")=="new")
    total_services = len(SERVICES)
    total_portfolio = len(PORTFOLIO)
    total_atouts = len(ATOUTS)
    total_rotator = len(ROTATOR_ITEMS)
    total_gallery = len(GALLERY_ITEMS)
    total_traffic = len(TRAFFIC)
    return render_template("admin/index.html",
                           messages_total=total_msgs,
                           unread_msgs=unread_msgs,
                           total_services=total_services,
                           total_portfolio=total_portfolio,
                           total_atouts=total_atouts,
                           total_rotator=total_rotator,
                           total_gallery=total_gallery,
                           total_traffic=total_traffic,
                           titre_page="Admin Dashboard")

# --- Gestion Services ---
@app.route(f'/{ADMIN_SECRET_URL}/services', methods=["GET", "POST"])
@admin_login_required
def admin_services():
    edit_idx = request.args.get("edit")
    service_to_edit = None
    if edit_idx is not None and edit_idx.isdigit():
        idx = int(edit_idx)
        if 0 <= idx < len(SERVICES):
            service_to_edit = SERVICES[idx]
    if request.method == "POST":
        idx_post = request.form.get("edit_idx")
        titre_fr = request.form.get("titre_fr","").strip()
        titre_en = request.form.get("titre_en","").strip()
        desc_fr = request.form.get("desc_fr","").strip()
        desc_en = request.form.get("desc_en","").strip()
        icon = request.form.get("icon","").strip()
        new_obj = {"titre": {"fr": titre_fr, "en": titre_en},
                   "desc": {"fr": desc_fr, "en": desc_en},
                   "icon": icon}
        if idx_post and idx_post.isdigit():
            idx2 = int(idx_post)
            if 0 <= idx2 < len(SERVICES):
                SERVICES[idx2] = new_obj
                flash("Service mis à jour.", "success")
        else:
            SERVICES.append(new_obj)
            flash("Service ajouté.", "success")
        return redirect(url_for('admin_services'))
    return render_template("admin/services.html", service_to_edit=service_to_edit, titre_page="Gestion Services")

@app.route(f'/{ADMIN_SECRET_URL}/services/delete/<int:idx>')
@admin_login_required
def admin_services_delete(idx):
    if 0 <= idx < len(SERVICES):
        SERVICES.pop(idx)
        flash("Service supprimé.", "info")
    else:
        flash("Index invalide.", "danger")
    return redirect(url_for('admin_services'))

# --- Gestion Portfolio ---
@app.route(f'/{ADMIN_SECRET_URL}/portfolio', methods=["GET", "POST"])
@admin_login_required
def admin_portfolio():
    edit_idx = request.args.get("edit")
    projet_to_edit = None
    if edit_idx is not None and edit_idx.isdigit():
        idx = int(edit_idx)
        if 0 <= idx < len(PORTFOLIO):
            projet_to_edit = PORTFOLIO[idx]
            proj = PORTFOLIO[idx]
            proj['imgs_str'] = ",".join(proj.get("imgs", []))
    if request.method == "POST":
        idx_post = request.form.get("edit_idx")
        titre_fr = request.form.get("titre_fr","").strip()
        titre_en = request.form.get("titre_en","").strip()
        desc_fr = request.form.get("desc_fr","").strip()
        desc_en = request.form.get("desc_en","").strip()
        imgs_str = request.form.get("imgs","").strip()
        imgs_list = [u.strip() for u in imgs_str.split(",") if u.strip()]
        fichiers_upload = request.files.getlist("fichiers")
        fichiers_saved = []
        for file in fichiers_upload:
            if file and file.filename:
                if allowed_file(file.filename):
                    filename = secure_filename(f"port_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                    save_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(save_path)
                    fichiers_saved.append(filename)
                else:
                    flash(f"Fichier non autorisé: {file.filename}", "warning")
        new_obj = {
            "titre": {"fr": titre_fr, "en": titre_en},
            "desc": {"fr": desc_fr, "en": desc_en},
            "imgs": imgs_list,
            "fichiers": fichiers_saved
        }
        if idx_post and idx_post.isdigit():
            idx2 = int(idx_post)
            if 0 <= idx2 < len(PORTFOLIO):
                PORTFOLIO[idx2] = new_obj
                flash("Élément du portfolio mis à jour.", "success")
        else:
            PORTFOLIO.append(new_obj)
            flash("Élément ajouté au portfolio.", "success")
        return redirect(url_for('admin_portfolio'))
    return render_template("admin/portfolio.html", projet_to_edit=projet_to_edit, titre_page="Gestion Portfolio")

@app.route(f'/{ADMIN_SECRET_URL}/portfolio/delete/<int:idx>')
@admin_login_required
def admin_portfolio_delete(idx):
    if 0 <= idx < len(PORTFOLIO):
        PORTFOLIO.pop(idx)
        flash("Élément du portfolio supprimé.", "info")
    else:
        flash("Index invalide.", "danger")
    return redirect(url_for('admin_portfolio'))

# --- Gestion Atouts ---
@app.route(f'/{ADMIN_SECRET_URL}/atouts', methods=["GET", "POST"])
@admin_login_required
def admin_atouts():
    edit_idx = request.args.get("edit")
    atout_to_edit = None
    if edit_idx is not None and edit_idx.isdigit():
        idx = int(edit_idx)
        if 0 <= idx < len(ATOUTS):
            atout_to_edit = ATOUTS[idx]
    if request.method == "POST":
        idx_post = request.form.get("edit_idx")
        atout_fr = request.form.get("atout_fr","").strip()
        atout_en = request.form.get("atout_en","").strip()
        new_obj = {"fr": atout_fr, "en": atout_en}
        if idx_post and idx_post.isdigit():
            idx2 = int(idx_post)
            if 0 <= idx2 < len(ATOUTS):
                ATOUTS[idx2] = new_obj
                flash("Atout mis à jour.", "success")
        else:
            ATOUTS.append(new_obj)
            flash("Atout ajouté.", "success")
        return redirect(url_for('admin_atouts'))
    return render_template("admin/atouts.html", atout_to_edit=atout_to_edit, titre_page="Gestion Atouts")

@app.route(f'/{ADMIN_SECRET_URL}/atouts/delete/<int:idx>')
@admin_login_required
def admin_atouts_delete(idx):
    if 0 <= idx < len(ATOUTS):
        ATOUTS.pop(idx)
        flash("Atout supprimé.", "info")
    else:
        flash("Index invalide.", "danger")
    return redirect(url_for('admin_atouts'))

# --- Gestion Messages ---
@app.route(f'/{ADMIN_SECRET_URL}/messages', methods=["GET"])
@admin_login_required
def admin_messages():
    page = request.args.get("page", 1, type=int)
    per_page = 10
    search = request.args.get("search","").strip().lower()
    if search:
        filtered = [m for m in MSGS if search in m.get("nom","").lower()
                     or search in m.get("email","").lower()
                     or search in m.get("sujet","").lower()]
    else:
        filtered = MSGS
    total = len(filtered)
    start = (page-1)*per_page
    end = start + per_page
    paginated = filtered[start:end]
    return render_template("admin/messages.html",
                           messages=paginated,
                           page=page,
                           per_page=per_page,
                           total_messages=total,
                           search_query=search,
                           titre_page="Gestion Messages")

@app.route(f'/{ADMIN_SECRET_URL}/messages/view/<int:idx>', methods=["GET","POST"])
@admin_login_required
def view_message(idx):
    if idx < 0 or idx >= len(MSGS):
        flash("Message introuvable.", "danger")
        return redirect(url_for('admin_messages'))
    msg = MSGS[idx]
    if request.method == "POST":
        action = request.form.get("action")
        if action == "mark_read":
            msg['status'] = 'read'
            save_json_file(MSG_FILE, MSGS)
            flash("Message marqué comme lu.", "success")
        elif action == "delete":
            MSGS.pop(idx)
            save_json_file(MSG_FILE, MSGS)
            flash("Message supprimé.", "info")
            return redirect(url_for('admin_messages'))
    return render_template("admin/message_view.html", msg=msg, idx=idx, titre_page="Voir Message")

# --- Gestion Carousel ---
@app.route(f'/{ADMIN_SECRET_URL}/carousel', methods=["GET", "POST"])
@admin_login_required
def admin_carousel():
    # Suppression
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(ROTATOR_ITEMS):
            filename = ROTATOR_ITEMS[idx].get("filename")
            try:
                if filename:
                    path = os.path.join(UPLOAD_FOLDER, filename)
                    if os.path.exists(path):
                        os.remove(path)
            except:
                pass
            ROTATOR_ITEMS.pop(idx)
            save_json_file(ROTATOR_FILE, ROTATOR_ITEMS)
            flash("Item supprimé du carousel.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_carousel'))
    # Déplacement up/down
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
                flash("Type non supporté pour carousel (images ou PDF).", "danger")
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
    return render_template("admin/carousel.html", titre_page="Gestion Carousel")

# --- Gestion Galerie (avec vues tournantes) ---
@app.route(f'/{ADMIN_SECRET_URL}/gallery', methods=["GET", "POST"])
@admin_login_required
def admin_gallery():
    # Suppression
    delid = request.args.get("del")
    if delid and delid.isdigit():
        idx = int(delid)
        if 0 <= idx < len(GALLERY_ITEMS):
            item = GALLERY_ITEMS.pop(idx)
            # Si local, supprimer les fichiers
            try:
                if item.get("type") == "image":
                    src = item.get("source","")
                    if src and not src.startswith("http"):
                        filename = src.split("/")[-1]
                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                elif item.get("type") == "video":
                    src = item.get("source","")
                    if src and not src.startswith("http"):
                        filename = src.split("/")[-1]
                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                elif item.get("type") == "rotation":
                    # supprimer chaque frame locale
                    for src in item.get("frames", []):
                        if not src.startswith("http"):
                            filename = src.split("/")[-1]
                            file_path = os.path.join(UPLOAD_FOLDER, filename)
                            if os.path.exists(file_path):
                                os.remove(file_path)
            except:
                pass
            save_json_file(GALLERY_FILE, GALLERY_ITEMS)
            flash("Élément galerie supprimé.", "info")
        else:
            flash("Index invalide pour suppression.", "danger")
        return redirect(url_for('admin_gallery'))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        url_input = request.form.get("url_input", "").strip()
        files = request.files.getlist("files")  # multiple upload
        added = False

        # Cas 1 : plusieurs fichiers uploadés => rotation
        valid_images = []
        for file in files:
            if file and file.filename:
                if allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    if ext in IMAGE_EXTENSIONS:
                        filename = secure_filename(f"gallery_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                        save_path = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(save_path)
                        source = url_for('uploaded_file', filename=filename)
                        valid_images.append(source)
                    else:
                        # On ignore les non-images pour la rotation
                        flash(f"Fichier ignoré (non-image) pour rotation: {file.filename}", "warning")
                else:
                    flash(f"Fichier non autorisé: {file.filename}", "warning")
        if len(valid_images) > 1:
            # Crée un item rotation
            GALLERY_ITEMS.append({
                "type": "rotation",
                "frames": valid_images,
                "title": title,
                "description": description
            })
            added = True
        elif len(valid_images) == 1 and not url_input:
            # Un seul fichier image uploadé => item image classique
            GALLERY_ITEMS.append({
                "type": "image",
                "source": valid_images[0],
                "title": title,
                "description": description
            })
            added = True
        else:
            # Cas URL input
            if url_input:
                # Si plusieurs URLs séparées par virgule => rotation
                urls = [u.strip() for u in url_input.split(",") if u.strip()]
                if len(urls) > 1:
                    valid_urls = []
                    for u in urls:
                        if u.startswith("http://") or u.startswith("https://"):
                            ext = u.rsplit('.', 1)[-1].lower()
                            if ext in IMAGE_EXTENSIONS:
                                valid_urls.append(u)
                            else:
                                flash(f"URL ignorée (non-image) pour rotation: {u}", "warning")
                        else:
                            flash(f"URL invalide: {u}", "warning")
                    if len(valid_urls) > 1:
                        GALLERY_ITEMS.append({
                            "type": "rotation",
                            "frames": valid_urls,
                            "title": title,
                            "description": description
                        })
                        added = True
                    elif len(valid_urls) == 1:
                        # Cas improbable : une URL unique => traiter plus bas
                        single_url = valid_urls[0]
                        GALLERY_ITEMS.append({
                            "type": "image",
                            "source": single_url,
                            "title": title,
                            "description": description
                        })
                        added = True
                else:
                    # Une seule URL => image ou vidéo
                    u = urls[0]
                    if u.startswith("http://") or u.startswith("https://"):
                        ext = u.rsplit('.', 1)[-1].lower()
                        if ext in IMAGE_EXTENSIONS:
                            GALLERY_ITEMS.append({
                                "type": "image",
                                "source": u,
                                "title": title,
                                "description": description
                            })
                            added = True
                        elif ext in VIDEO_EXTENSIONS:
                            GALLERY_ITEMS.append({
                                "type": "video",
                                "source": u,
                                "title": title,
                                "description": description
                            })
                            added = True
                        else:
                            flash("L’URL ne pointe pas vers un format supporté (image/vidéo).", "warning")
                    else:
                        flash("URL invalide. Doit commencer par http:// ou https://", "warning")
            else:
                # Ni fichiers uploadés, ni URL => rien à faire
                if not valid_images:
                    flash("Veuillez fournir des fichiers ou des URLs pour la galerie.", "warning")

        if added:
            save_json_file(GALLERY_FILE, GALLERY_ITEMS)
            flash("Élément ajouté à la galerie.", "success")
        return redirect(url_for('admin_gallery'))

    return render_template("admin/gallery.html", titre_page="Gestion Galerie")

# --- Analytics ---
@app.route(f'/{ADMIN_SECRET_URL}/analytics')
@admin_login_required
def admin_analytics():
    counts = {}
    for m in MSGS:
        ts = m.get("timestamp","")
        if ts:
            date = ts.split(" ")[0]
            counts[date] = counts.get(date, 0) + 1
    sorted_dates = sorted(counts.items(), key=lambda x: x[0], reverse=True)
    total_msgs = len(MSGS)
    unread_msgs = sum(1 for m in MSGS if m.get("status")=="new")
    total_services = len(SERVICES)
    total_portfolio = len(PORTFOLIO)
    return render_template("admin/analytics.html",
                           sorted_dates=sorted_dates,
                           total_msgs=total_msgs,
                           unread_msgs=unread_msgs,
                           total_services=total_services,
                           total_portfolio=total_portfolio,
                           titre_page="Analytics")

# --- Download all uploads ---
@app.route(f'/{ADMIN_SECRET_URL}/download_uploads')
@admin_login_required
def download_all_uploads():
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

# --- Traffic logs display ---
@app.route(f'/{ADMIN_SECRET_URL}/traffic')
@admin_login_required
def admin_traffic():
    search_query = request.args.get('search', '').lower()
    page = request.args.get('page', 1, type=int)
    per_page = 20
    filtered = TRAFFIC
    if search_query:
        filtered = [log for log in TRAFFIC if search_query in log.get('path',"").lower() or search_query in log.get('remote_addr',"").lower()]
    total = len(filtered)
    start = (page-1)*per_page
    end = start + per_page
    paginated = filtered[start:end]
    return render_template("admin/traffic.html",
                           logs=paginated,
                           total_logs=total,
                           page=page,
                           per_page=per_page,
                           search_query=search_query,
                           titre_page="Logs Traffic")

# --- Robots.txt ---
@app.route('/robots.txt')
def robots_txt():
    disallow_path = f"/{ADMIN_SECRET_URL}/"
    content = f"User-agent: *\nDisallow: {disallow_path}\n"
    return Response(content, mimetype='text/plain')

# --- Sitemap.xml ---
@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    pages = [
        url_for('index', _external=True),
        url_for('services', _external=True),
        url_for('portfolio', _external=True),
        url_for('galeries', _external=True),
        url_for('pourquoi', _external=True),
        url_for('contact', _external=True),
        url_for('toggle_dark', _external=True),
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        xml.append(f"<url><loc>{p}</loc></url>")
    xml.append("</urlset>")
    response = app.response_class("\n".join(xml), mimetype='application/xml')
    return response

# ----------------------------------------
# DÉFINITION DES TEMPLATES INLINE (DictLoader)
# ----------------------------------------
# Pour rester en single-file, on stocke tous les templates Jinja dans un dict.
# Le CSS est retravaillé pour des couleurs vives et alternances de sections.
base_template = """
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8">
    <title>{% if titre_page %}{{ titre_page }} | {% endif %}{{ site.nom }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- AOS animations -->
    <link href="https://cdn.jsdelivr.net/npm/aos@2.3.4/dist/aos.css" rel="stylesheet">
    <!-- Google Font dynamique -->
    <link href="https://fonts.googleapis.com/css2?family={{ site.font|replace(' ','+') }}:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    <!-- SpriteSpin (pour vues tournantes) -->
    <script src="https://cdn.jsdelivr.net/npm/jquery@3.6.0/dist/jquery.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/spritespin@4.0.11/release/spritespin.min.js"></script>
    <style>
        /* Palette vive via variables CSS */
        :root {
            --color-primary: {{ site.couleur }};           /* magenta vif ou valeur admin */
            --color-secondary: {{ site.secondary }};       /* orange vif ou valeur admin */
            --color-accent: {{ site.accent }};             /* vert vif ou valeur admin */
            --color-alt1: #FFF3E0;   /* pastel pêche clair pour alternance */
            --color-alt2: #E8F5E9;   /* pastel vert clair */
            --color-alt3: #E3F2FD;   /* pastel bleu clair */
            --bg-light: #FAFAFA;     /* fond clair */
            --bg-dark: #121212;      /* fond sombre plus doux */
            --text-dark: #212121;    /* texte sombre */
            --text-light: #F5F5F5;   /* texte clair */
            --card-bg-light: #FFFFFF;/* carte en mode clair */
            --card-bg-alt: #F1F1F1;  /* alternatif clair */
            --card-bg-dark: #1E1E1E; /* carte en mode sombre */
            --gradient-primary: linear-gradient(135deg, {{ site.couleur }}, {{ site.secondary }}); 
            --gradient-secondary: linear-gradient(135deg, {{ site.secondary }}, {{ site.accent }});
            --gradient-accent: linear-gradient(135deg, {{ site.accent }}, {{ site.couleur }});
            --font-family: '{{ site.font }}', Arial, sans-serif;
        }
        body {
            font-family: var(--font-family);
            background: var(--bg-light);
            color: var(--text-dark);
            margin: 0; padding: 0;
            transition: background 0.3s, color 0.3s;
        }
        body.dark-mode {
            background: var(--bg-dark) !important;
            color: var(--text-light) !important;
        }
        a {
            color: var(--color-primary);
            text-decoration: none;
            transition: color 0.2s;
        }
        a:hover {
            color: var(--color-accent);
            text-decoration: underline;
        }
        /* Navbar */
        .navbar {
            background: var(--gradient-primary) !important;
        }
        .navbar .nav-link {
            color: #fff !important;
        }
        .navbar .nav-link.active {
            color: var(--color-accent) !important;
            font-weight: bold;
            border-bottom: 2px solid var(--color-accent);
        }
        .navbar .nav-link:hover {
            color: var(--color-accent) !important;
        }
        .dark-toggle { cursor: pointer; color: #fff; margin-left: 1rem; }
        /* Hero */
        .hero {
            position: relative;
            text-align: center;
            color: var(--text-light);
            padding: 80px 0;
            background:
                linear-gradient(135deg, rgba(233,30,99,0.8), rgba(255,87,34,0.8)),
                url('{{ site.photo }}') center/cover no-repeat;
        }
        .hero img {
            width: 140px; height:140px; object-fit:cover;
            border-radius: 50%;
            border: 3px solid var(--color-accent);
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
            background: var(--color-secondary);
            color: #fff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .hero .btn-contact:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
            background: var(--color-accent);
        }
        /* Section titles */
        .section-title {
            color: var(--color-primary);
            margin-top: 48px;
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
            background: var(--color-primary);
            margin: 8px auto 0;
            border-radius: 2px;
        }
        /* Service cards */
        .service-card {
            background: var(--card-bg-light);
            border-radius:20px;
            padding:24px 16px;
            text-align:center;
            margin-bottom:20px;
            box-shadow:0 2px 14px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s, background 0.3s;
            border-top: 4px solid var(--color-primary);
        }
        .service-card:hover {
            transform: translateY(-6px);
            box-shadow:0 6px 24px rgba(0,0,0,0.15);
            background: var(--card-bg-alt);
        }
        .service-card i {
            font-size:2.4rem;
            color: var(--color-secondary);
            margin-bottom:12px;
        }
        body.dark-mode .service-card {
            background: var(--card-bg-dark);
            color: var(--text-light);
        }
        body.dark-mode .service-card:hover {
            background: #2a2a2a;
        }
        /* Portfolio */
        .card-portfolio {
            border: none;
            border-radius: 15px;
            overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s, background 0.3s;
            background: var(--card-bg-light);
            color: var(--text-dark);
            box-shadow:0 2px 12px rgba(0,0,0,0.1);
            margin-bottom: 24px;
            border-left: 4px solid var(--color-secondary);
        }
        .card-portfolio:hover {
            transform: translateY(-6px);
            box-shadow:0 8px 28px rgba(0,0,0,0.2);
            background: var(--card-bg-alt);
        }
        .portfolio-img {
            height:200px; width:100%; object-fit:cover;
        }
        body.dark-mode .card-portfolio {
            background: var(--card-bg-dark);
            color: var(--text-light);
        }
        /* Gallery */
        .gallery-container {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            justify-content: center;
        }
        .gallery-item {
            background: var(--card-bg-light);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s, background 0.3s;
            width: 300px;
            display: flex;
            flex-direction: column;
            border-top: 4px solid var(--color-accent);
        }
        .gallery-item:hover {
            transform: translateY(-4px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            background: var(--card-bg-alt);
        }
        .gallery-item img,
        .gallery-item video {
            max-width: 100%;
            height: auto;
            display: block;
        }
        .gallery-caption {
            padding: 12px;
        }
        .gallery-caption h5 {
            margin: 0 0 8px;
            font-size: 1.1rem;
            color: var(--color-primary);
        }
        .gallery-caption p {
            margin: 0;
            font-size: 0.95rem;
            color: #555;
        }
        body.dark-mode .gallery-item {
            background: var(--card-bg-dark);
            color: var(--text-light);
        }
        /* Viewer 360° */
        .rotation-viewer {
            width: 100%;
            aspect-ratio: 1 / 1;
            background: #f2f2f2;
            position: relative;
            border: 2px solid var(--color-primary);
        }
        /* Footer */
        .footer { background: var(--bg-dark); color: #fff; padding: 30px 0; margin-top: 0; }
        .footer a { color: var(--color-accent); text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
        .project-cta {
            background: var(--gradient-secondary);
            color:#fff;
            border-radius:20px;
            padding:25px 15px;
            margin:30px 0 15px 0;
            box-shadow:0 4px 16px rgba(0,0,0,0.15);
            font-size:1.1rem;
            font-weight:500;
            text-align: center;
        }
        /* Admin */
        .admin-nav { background:#2c2f33; padding:10px; border-radius:10px; margin-bottom:10px; }
        .admin-nav a { color:#FFD700; margin:0 8px; font-weight:bold; text-decoration:none;}
        .admin-panel {
            background: var(--card-bg-light);
            border-radius:14px;
            padding:20px 16px;
            margin-top:10px;
            box-shadow:0 4px 24px rgba(0,0,0,0.1);
            color: var(--text-dark);
        }
        body.dark-mode .admin-panel {
            background: var(--card-bg-dark);
            color: var(--text-light);
        }
        .admin-table td, .admin-table th { vertical-align:middle; color: inherit; }
        .admin-msg { background: #fff3cd; border:1px solid var(--color-primary); border-radius:8px; padding:12px 18px; }
        /* Drag-drop */
        .drag-drop-area {
            border:2px dashed #bbb;
            border-radius:10px;
            background:#f8fbff;
            text-align:center;
            padding:20px 8px;
            color:#789;
            margin-bottom:12px;
            transition: border .2s, background .2s;
            position: relative;
        }
        .drag-drop-area.dragover { border:2.2px solid var(--color-primary); background:#e7f7ff; }
        /* Responsive */
        @media (max-width:600px) {
            html { font-size:15px; }
            .hero, .carousel { padding: 40px 0 30px 0; }
            .project-cta { padding:10px 5px; }
            .admin-panel { padding:10px 8px; }
            .carousel-item img {
                max-height: 250px;
                height: auto;
            }
            .hero img { width: 100px; height:100px; }
            .gallery-item {
                width: 100%;
            }
        }
    </style>
    {% block head_extra %}{% endblock %}
</head>
<body class="{{ 'dark-mode' if session.get('dark_mode') else '' }}">
<nav class="navbar navbar-expand-lg sticky-top">
  <div class="container">
    <a class="navbar-brand" href="{{ url_for('index') }}">{{ site.nom }}</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav">
      <span class="navbar-toggler-icon" style="color:#fff;"></span>
    </button>
    <div class="collapse navbar-collapse" id="mainNav">
      <ul class="navbar-nav ms-auto align-items-center">
        <li class="nav-item"><a class="nav-link {% if request.endpoint=='index' %}active{% endif %}" href="{{ url_for('index') }}">{{ "Accueil" if lang=='fr' else "Home" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if request.endpoint=='services' %}active{% endif %}" href="{{ url_for('services') }}">{{ "Services" if lang=='fr' else "Services" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if request.endpoint=='portfolio' %}active{% endif %}" href="{{ url_for('portfolio') }}">{{ "Portfolio" if lang=='fr' else "Portfolio" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if request.endpoint=='galeries' %}active{% endif %}" href="{{ url_for('galeries') }}">{{ "Galeries" if lang=='fr' else "Galleries" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if request.endpoint=='pourquoi' %}active{% endif %}" href="{{ url_for('pourquoi') }}">{{ "Pourquoi moi ?" if lang=='fr' else "Why me?" }}</a></li>
        <li class="nav-item"><a class="nav-link {% if request.endpoint=='contact' %}active{% endif %}" href="{{ url_for('contact') }}">{{ "Contact / Projets" if lang=='fr' else "Contact / Project" }}</a></li>
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
<!-- Bootstrap JS bundle -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<!-- AOS animations -->
<script src="https://cdn.jsdelivr.net/npm/aos@2.3.4/dist/aos.js"></script>
<script>
  AOS.init({duration: 800, once: true});
  // Drag-drop area (contact form)
  const dropArea = document.getElementById('dragDrop');
  if (dropArea) {
    dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.classList.add('dragover'); });
    dropArea.addEventListener('dragleave', (e) => { dropArea.classList.remove('dragover'); });
    dropArea.addEventListener('drop', (e) => {
      e.preventDefault(); dropArea.classList.remove('dragover');
      let input = document.getElementById('fichiers');
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
    document.getElementById('fichiers').addEventListener('change', function(){
      let list = document.getElementById('fileList'); list.innerHTML = "";
      for (let i = 0; i < this.files.length; i++) {
          let file = this.files[i];
          let li = document.createElement('li'); li.textContent = file.name;
          list.appendChild(li);
      }
    });
  }

  // Initialisation SpriteSpin pour chaque viewer 360°
  document.addEventListener('DOMContentLoaded', function(){
    $('.rotation-viewer').each(function(){
      const $el = $(this);
      let frames = $el.data('images'); // array of image URLs
      if (Array.isArray(frames) && frames.length>0) {
        // Taille du conteneur
        let width = $el.width();
        SpriteSpin.create({
          container: $el,
          source: frames,
          width: width,
          height: width,
          frames: frames.length,
          sense: -1,
          animate: false,
          frameTime: 40,
          module: SpriteSpinModule360
        });
      }
    });
  });
</script>
{% block scripts_extra %}{% endblock %}
</body>
</html>
"""

# Template index.html
index_template = """
{% extends "base.html" %}
{% block content %}
<div class="hero">
  <div class="container" data-aos="fade-in">
    <img src="{{ site.photo }}" alt="Photo profil">
    <h1>{{ site.nom }}</h1>
    <h3>{{ site.slogan[lang] }}</h3>
    <a href="{{ url_for('contact') }}" class="btn btn-contact mt-3">{{ "Contactez-moi" if lang=='fr' else "Contact Me" }}</a>
  </div>
</div>
<div class="container">
  {% if ROTATOR_ITEMS %}
  <div id="homeCarousel" class="carousel slide mt-5" data-bs-ride="carousel" data-aos="fade-up">
    <div class="carousel-inner">
      {% for item in ROTATOR_ITEMS %}
      <div class="carousel-item {% if loop.first %}active{% endif %}">
        {% if item.type=='image' %}
          <img src="{{ url_for('uploaded_file', filename=item.filename) }}" class="d-block w-100" alt="Carousel item" style="max-height:400px; object-fit:cover;">
        {% else %}
          <div class="d-flex justify-content-center align-items-center" style="height:400px; background:#f2f2f2;">
            <i class="bi bi-file-earmark-pdf-fill" style="font-size:3rem;color:var(--color-secondary);"></i>
            <span class="ms-2">{{ item.filename }}</span>
          </div>
        {% endif %}
      </div>
      {% endfor %}
    </div>
    <button class="carousel-control-prev" type="button" data-bs-target="#homeCarousel" data-bs-slide="prev">
      <span class="carousel-control-prev-icon"></span>
      <span class="visually-hidden">Previous</span>
    </button>
    <button class="carousel-control-next" type="button" data-bs-target="#homeCarousel" data-bs-slide="next">
      <span class="carousel-control-next-icon"></span>
      <span class="visually-hidden">Next</span>
    </button>
  </div>
  {% endif %}
  <div class="project-cta text-center" data-aos="fade-up">
    {{ "Prêt à démarrer votre projet ?" if lang=='fr' else "Ready to start your project?" }}
  </div>
</div>
{% endblock %}
"""

# Template services.html
services_template = """
{% extends "base.html" %}
{% block content %}
<h2 class="section-title text-center" data-aos="fade-up">{{ "Services" if lang=='fr' else "Services" }}</h2>
<div class="row">
  {% for serv in SERVICES %}
  <div class="col-md-4" data-aos="fade-up" data-aos-delay="{{ loop.index0*100 }}">
    <div class="service-card">
      <i class="bi {{ serv.icon }}"></i>
      <h5 class="mt-2">{{ serv.titre[lang] }}</h5>
      <p>{{ serv.desc[lang] }}</p>
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
"""

# Template portfolio.html
portfolio_template = """
{% extends "base.html" %}
{% block content %}
<h2 class="section-title text-center" data-aos="fade-up">{{ "Portfolio" if lang=='fr' else "Portfolio" }}</h2>
<div class="row">
  {% for proj in PORTFOLIO %}
  <div class="col-md-4" data-aos="fade-up" data-aos-delay="{{ loop.index0*100 }}">
    <div class="card-portfolio">
      {% if proj.imgs and proj.imgs[0] %}
      <img src="{{ proj.imgs[0] }}" alt="Image Projet" class="portfolio-img">
      {% endif %}
      <div class="p-3">
        <h5>{{ proj.titre[lang] }}</h5>
        <p>{{ proj.desc[lang] }}</p>
        {% if proj.fichiers %}
        <p>
          {% for f in proj.fichiers %}
            <a href="{{ url_for('uploaded_file', filename=f) }}" class="btn btn-sm btn-outline-primary me-1" target="_blank">{{ f }}</a>
          {% endfor %}
        </p>
        {% endif %}
      </div>
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
"""

# Template galleries.html (public) avec gestion rotation
galleries_template = """
{% extends "base.html" %}
{% block content %}
<h2 class="section-title text-center" data-aos="fade-up">{{ "Galeries" if lang=='fr' else "Galleries" }}</h2>
<div class="gallery-container">
  {% for item in GALLERY_ITEMS %}
  <div class="gallery-item" data-aos="fade-up" data-aos-delay="{{ loop.index0*100 }}">
    {% if item.type=='image' %}
      <img src="{{ item.source }}" alt="{{ item.title or 'Image' }}" loading="lazy">
    {% elif item.type=='video' %}
      <video controls muted preload="metadata" poster="" style="max-height:200px; object-fit:cover;" loading="lazy">
        <source src="{{ item.source }}">
        Votre navigateur ne supporte pas la vidéo.
      </video>
    {% elif item.type=='rotation' %}
      <div class="rotation-viewer" data-images='{{ item.frames | tojson }}'></div>
    {% endif %}
    <div class="gallery-caption">
      {% if item.title %}<h5>{{ item.title }}</h5>{% endif %}
      {% if item.description %}<p>{{ item.description }}</p>{% endif %}
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
"""

# Template pourquoi.html
pourquoi_template = """
{% extends "base.html" %}
{% block content %}
<h2 class="section-title text-center" data-aos="fade-up">{{ "Pourquoi moi ?" if lang=='fr' else "Why me?" }}</h2>
<div class="row">
  {% for at in ATOUTS %}
  <div class="col-md-6" data-aos="fade-up" data-aos-delay="{{ loop.index0*100 }}">
    <div class="mb-3 p-3" style="border-left:4px solid var(--color-primary)">
      <p>{{ at[lang] }}</p>
    </div>
  </div>
  {% endfor %}
</div>
{% endblock %}
"""

# Template contact.html
contact_template = """
{% extends "base.html" %}
{% block content %}
<h2 class="section-title text-center" data-aos="fade-up">{{ "Contact / Projets" if lang=='fr' else "Contact / Projects" }}</h2>
<div class="row justify-content-center">
  <div class="col-md-8" data-aos="fade-up">
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="nom" class="form-label">{{ "Nom" if lang=='fr' else "Name" }}</label>
        <input type="text" class="form-control" id="nom" name="nom" required>
      </div>
      <div class="mb-3">
        <label for="email" class="form-label">Email</label>
        <input type="email" class="form-control" id="email" name="email" required>
      </div>
      <div class="mb-3">
        <label for="sujet" class="form-label">{{ "Sujet" if lang=='fr' else "Subject" }}</label>
        <input type="text" class="form-control" id="sujet" name="sujet" required>
      </div>
      <div class="mb-3">
        <label for="message" class="form-label">{{ "Message" if lang=='fr' else "Message" }}</label>
        <textarea class="form-control" id="message" name="message" rows="5" required></textarea>
      </div>
      <div class="mb-3">
        <label class="form-label">{{ "Fichiers (optionnel)" if lang=='fr' else "Files (optional)" }}</label>
        <div id="dragDrop" class="drag-drop-area">
          {{ "Glissez-déposez vos fichiers ici ou cliquez pour sélectionner" if lang=='fr' else "Drag & drop files here or click to select" }}
          <input type="file" id="fichiers" name="fichiers" multiple style="opacity:0; position:absolute; width:100%; height:100%; top:0; left:0; cursor:pointer;">
        </div>
        <ul id="fileList" class="list-unstyled small mt-2"></ul>
      </div>
      <button type="submit" class="btn btn-primary">{{ "Envoyer" if lang=='fr' else "Send" }}</button>
    </form>
  </div>
</div>
{% endblock %}
"""

# Template admin/login.html
admin_login_template = """
{% extends "base.html" %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-4" data-aos="fade-down">
    <div class="card p-4 mt-5">
      <h5 class="card-title text-center mb-3">Admin Login</h5>
      <form method="post">
        <div class="mb-3">
          <label for="username" class="form-label">Username (Email)</label>
          <input type="text" class="form-control" id="username" name="username" required>
        </div>
        <div class="mb-3">
          <label for="password" class="form-label">Password</label>
          <input type="password" class="form-control" id="password" name="password" required>
        </div>
        <button type="submit" class="btn btn-primary w-100">Login</button>
      </form>
    </div>
  </div>
</div>
{% endblock %}
"""

# Template admin/index.html (dashboard)
admin_index_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_services') }}">Services</a> |
  <a href="{{ url_for('admin_portfolio') }}">Portfolio</a> |
  <a href="{{ url_for('admin_atouts') }}">Atouts</a> |
  <a href="{{ url_for('admin_messages') }}">Messages</a> |
  <a href="{{ url_for('admin_carousel') }}">Carousel</a> |
  <a href="{{ url_for('admin_gallery') }}">Galerie</a> |
  <a href="{{ url_for('admin_analytics') }}">Analytics</a> |
  <a href="{{ url_for('admin_settings') }}">Settings</a> |
  <a href="{{ url_for('admin_traffic') }}">Trafic</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Dashboard</h5>
  <div class="row">
    <div class="col-md-3"><div class="p-3 border mb-3"><strong>Messages totaux:</strong> {{ messages_total }}</div></div>
    <div class="col-md-3"><div class="p-3 border mb-3"><strong>Messages non lus:</strong> {{ unread_msgs }}</div></div>
    <div class="col-md-2"><div class="p-3 border mb-3"><strong>Services:</strong> {{ total_services }}</div></div>
    <div class="col-md-2"><div class="p-3 border mb-3"><strong>Portfolio:</strong> {{ total_portfolio }}</div></div>
    <div class="col-md-2"><div class="p-3 border mb-3"><strong>Atouts:</strong> {{ total_atouts }}</div></div>
    <div class="col-md-2"><div class="p-3 border mb-3"><strong>Carousel:</strong> {{ total_rotator }}</div></div>
    <div class="col-md-2"><div class="p-3 border mb-3"><strong>Galerie:</strong> {{ total_gallery }}</div></div>
    <div class="col-md-2"><div class="p-3 border mb-3"><strong>Logs Trafic:</strong> {{ total_traffic }}</div></div>
  </div>
</div>
{% endblock %}
"""

# Template admin/services.html
admin_services_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_services') }}">Services</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Gestion des Services</h5>
  {% if SERVICES %}
  <table class="table table-hover admin-table">
    <thead>
      <tr><th>#</th><th>FR</th><th>EN</th><th>Description FR</th><th>Description EN</th><th>Icon</th><th>Actions</th></tr>
    </thead>
    <tbody>
    {% for serv in SERVICES %}
      <tr>
        <td>{{ loop.index0 }}</td>
        <td>{{ serv.titre['fr'] }}</td>
        <td>{{ serv.titre['en'] }}</td>
        <td>{{ serv.desc['fr'] }}</td>
        <td>{{ serv.desc['en'] }}</td>
        <td><i class="bi {{ serv.icon }}"></i> {{ serv.icon }}</td>
        <td>
          <a href="{{ url_for('admin_services', edit=loop.index0) }}" class="btn btn-sm btn-primary">Éditer</a>
          <a href="{{ url_for('admin_services_delete', idx=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer ce service?');">Suppr.</a>
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
    <div class="col-md-3"><input type="text" name="titre_fr" value="{{ service_to_edit.titre['fr'] if service_to_edit else '' }}" class="form-control" placeholder="Service (FR)" required></div>
    <div class="col-md-3"><input type="text" name="titre_en" value="{{ service_to_edit.titre['en'] if service_to_edit else '' }}" class="form-control" placeholder="Service (EN)" required></div>
    <div class="col-md-3"><input type="text" name="desc_fr" value="{{ service_to_edit.desc['fr'] if service_to_edit else '' }}" class="form-control" placeholder="Description (FR)" required></div>
    <div class="col-md-3"><input type="text" name="desc_en" value="{{ service_to_edit.desc['en'] if service_to_edit else '' }}" class="form-control" placeholder="Description (EN)" required></div>
    <div class="col-md-3"><input type="text" name="icon" value="{{ service_to_edit.icon if service_to_edit else '' }}" class="form-control" placeholder="Icône bi-..." ></div>
    <div class="col-md-2"><button class="btn btn-contact w-100" type="submit">{{ 'Mettre à jour' if service_to_edit else 'Ajouter' }}</button></div>
  </form>
</div>
{% endblock %}
"""

# Template admin/portfolio.html
admin_portfolio_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_portfolio') }}">Portfolio</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Gestion du Portfolio</h5>
  {% if PORTFOLIO %}
  <table class="table table-hover admin-table">
    <thead>
      <tr><th>#</th><th>FR</th><th>EN</th><th>Images (URLs)</th><th>Fichiers joints</th><th>Actions</th></tr>
    </thead>
    <tbody>
    {% for proj in PORTFOLIO %}
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
          <a href="{{ url_for('admin_portfolio_delete', idx=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer cet élément?');">Suppr.</a>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
    <p>Aucun élément dans le portfolio.</p>
  {% endif %}
  <hr>
  <h6>{{ 'Modifier l\'élément' if projet_to_edit else 'Ajouter un nouvel élément' }}</h6>
  <form method="post" enctype="multipart/form-data" class="row g-2">
    <input type="hidden" name="edit_idx" value="{{ request.args.get('edit') if projet_to_edit is not none else '' }}">
    <div class="col-md-3"><input type="text" name="titre_fr" value="{{ projet_to_edit.titre.fr if projet_to_edit else '' }}" class="form-control" placeholder="Titre FR" required></div>
    <div class="col-md-3"><input type="text" name="titre_en" value="{{ projet_to_edit.titre.en if projet_to_edit else '' }}" class="form-control" placeholder="Titre EN" required></div>
    <div class="col-md-3"><input type="text" name="desc_fr" value="{{ projet_to_edit.desc.fr if projet_to_edit else '' }}" class="form-control" placeholder="Description FR" required></div>
    <div class="col-md-3"><input type="text" name="desc_en" value="{{ projet_to_edit.desc.en if projet_to_edit else '' }}" class="form-control" placeholder="Description EN" required></div>
    <div class="col-md-4"><input type="text" name="imgs" value="{{ projet_to_edit.imgs_str if projet_to_edit else '' }}" class="form-control" placeholder="URLs images, séparées par virgule"></div>
    <div class="col-md-4"><input type="file" name="fichiers" class="form-control" multiple></div>
    <div class="col-md-2"><button class="btn btn-contact w-100" type="submit">{{ 'Mettre à jour' if projet_to_edit else 'Ajouter' }}</button></div>
  </form>
  <div class="small mt-1">Pour images, coller des URLs (ex: https://...jpg), séparées par virgule.</div>
</div>
{% endblock %}
"""

# Template admin/atouts.html
admin_atouts_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_atouts') }}">Atouts</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Gestion des Atouts</h5>
  {% if ATOUTS %}
  <table class="table table-hover admin-table">
    <thead>
      <tr><th>#</th><th>FR</th><th>EN</th><th>Actions</th></tr>
    </thead>
    <tbody>
    {% for at in ATOUTS %}
      <tr>
        <td>{{ loop.index0 }}</td>
        <td>{{ at['fr'] }}</td>
        <td>{{ at['en'] }}</td>
        <td>
          <a href="{{ url_for('admin_atouts', edit=loop.index0) }}" class="btn btn-sm btn-primary">Éditer</a>
          <a href="{{ url_for('admin_atouts_delete', idx=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer cet atout?');">Suppr.</a>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  {% else %}
    <p>Aucun atout défini.</p>
  {% endif %}
  <hr>
  <h6>{{ 'Modifier l\'atout' if atout_to_edit else 'Ajouter un nouvel atout' }}</h6>
  <form method="post" class="row g-2">
    <input type="hidden" name="edit_idx" value="{{ request.args.get('edit') if atout_to_edit is not none else '' }}">
    <div class="col-md-5"><input type="text" name="atout_fr" value="{{ atout_to_edit.fr if atout_to_edit }}" class="form-control" placeholder="Atout FR" required></div>
    <div class="col-md-5"><input type="text" name="atout_en" value="{{ atout_to_edit.en if atout_to_edit }}" class="form-control" placeholder="Atout EN" required></div>
    <div class="col-md-2"><button class="btn btn-contact w-100" type="submit">{{ 'Mettre à jour' if atout_to_edit else 'Ajouter' }}</button></div>
  </form>
</div>
{% endblock %}
"""

# Template admin/messages.html
admin_messages_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_messages') }}">Messages</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Gestion des Messages</h5>
  <form method="get" class="row mb-3">
    <div class="col-md-4">
      <input type="text" name="search" value="{{ search_query }}" class="form-control" placeholder="Rechercher...">
    </div>
    <div class="col-md-2">
      <button class="btn btn-primary" type="submit">Search</button>
    </div>
  </form>
  {% if messages %}
  <table class="table table-hover admin-table">
    <thead><tr><th>#</th><th>Nom</th><th>Email</th><th>Sujet</th><th>Status</th><th>Timestamp</th><th>Actions</th></tr></thead>
    <tbody>
    {% for m in messages %}
      <tr>
        <td>{{ loop.index0 + (page-1)*per_page }}</td>
        <td>{{ m.nom }}</td>
        <td>{{ m.email }}</td>
        <td>{{ m.sujet }}</td>
        <td>{{ m.status }}</td>
        <td>{{ m.timestamp }}</td>
        <td>
          <a href="{{ url_for('view_message', idx=loop.index0 + (page-1)*per_page) }}" class="btn btn-sm btn-primary">Voir</a>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <nav>
    <ul class="pagination">
      {% set total_pages = (total_messages // per_page) + (1 if total_messages % per_page else 0) %}
      {% for p in range(1, total_pages+1) %}
      <li class="page-item {% if p==page %}active{% endif %}">
        <a class="page-link" href="{{ url_for('admin_messages', page=p, search=search_query) }}">{{ p }}</a>
      </li>
      {% endfor %}
    </ul>
  </nav>
  {% else %}
    <p>Aucun message.</p>
  {% endif %}
</div>
{% endblock %}
"""

# Template admin/message_view.html
admin_message_view_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_messages') }}">Messages</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Voir Message</h5>
  <p><strong>Nom:</strong> {{ msg.nom }}</p>
  <p><strong>Email:</strong> {{ msg.email }}</p>
  <p><strong>Sujet:</strong> {{ msg.sujet }}</p>
  <p><strong>Message:</strong><br>{{ msg.message }}</p>
  <p><strong>Fichiers:</strong><br>
    {% if msg.fichiers %}
      {% for f in msg.fichiers %}
        <a href="{{ url_for('uploaded_file', filename=f) }}" target="_blank">{{ f }}</a><br>
      {% endfor %}
    {% else %}
      Aucun fichier.
    {% endif %}
  </p>
  <p><strong>Status:</strong> {{ msg.status }}</p>
  <p><strong>Timestamp:</strong> {{ msg.timestamp }}</p>
  <form method="post" class="d-flex gap-2">
    {% if msg.status!='read' %}
      <button name="action" value="mark_read" class="btn btn-success">Marquer comme lu</button>
    {% endif %}
    <button name="action" value="delete" class="btn btn-danger" onclick="return confirm('Supprimer ce message?');">Supprimer</button>
    <a href="{{ url_for('admin_messages') }}" class="btn btn-secondary">Retour</a>
  </form>
</div>
{% endblock %}
"""

# Template admin/carousel.html
admin_carousel_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_carousel') }}">Carousel</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Gestion du Carousel (page d'accueil)</h5>
  <p>Nombre d'items actuels: {{ ROTATOR_ITEMS|length }} / 6</p>
  {% if ROTATOR_ITEMS %}
  <div class="table-responsive">
  <table class="table table-hover admin-table align-middle">
    <thead>
      <tr><th>#</th><th>Aperçu</th><th>Nom du fichier</th><th>Actions</th></tr>
    </thead>
    <tbody>
    {% for item in ROTATOR_ITEMS %}
      <tr>
        <td>{{ loop.index0 }}</td>
        <td>
          {% if item.type=='image' %}
            <img src="{{ url_for('uploaded_file', filename=item.filename) }}" alt="img" style="max-height:80px;">
          {% elif item.type=='pdf' %}
            <i class="bi bi-file-earmark-pdf-fill" style="font-size:2rem;color:var(--color-secondary);"></i>
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
  {% if ROTATOR_ITEMS|length < 6 %}
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
  <div class="alert alert-info">{{ 'Limite atteinte: 6 items. Supprimez-en avant d\'ajouter.' if lang=='fr' else 'Limit reached: 6 items. Remove some before adding.' }}</div>
  {% endif %}
</div>
{% endblock %}
"""

# Template admin/gallery.html
admin_gallery_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_gallery') }}">Galerie</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Gestion de la galerie</h5>
  {% if GALLERY_ITEMS %}
  <div class="table-responsive">
  <table class="table table-hover admin-table align-middle">
    <thead>
      <tr><th>#</th><th>Type</th><th>Source / Frames</th><th>Titre</th><th>Description</th><th>Actions</th></tr>
    </thead>
    <tbody>
    {% for item in GALLERY_ITEMS %}
      <tr>
        <td>{{ loop.index0 }}</td>
        <td>{{ item.type }}</td>
        <td style="max-width:200px; word-break:break-all;">
          {% if item.type=='image' or item.type=='video' %}
            {% if item.source.startswith('http') %}
              <a href="{{ item.source }}" target="_blank">{{ item.source|truncate(30) }}</a>
            {% else %}
              <a href="{{ item.source }}" target="_blank">{{ item.source }}</a>
            {% endif %}
          {% elif item.type=='rotation' %}
            <span>Frames: {{ item.frames|length }}</span><br>
            {% for src in item.frames %}
              {% if src.startswith('http') %}
                <a href="{{ src }}" target="_blank">{{ src|truncate(20) }}</a><br>
              {% else %}
                <a href="{{ src }}" target="_blank">{{ src }}</a><br>
              {% endif %}
            {% endfor %}
          {% endif %}
        </td>
        <td>{{ item.title or '-' }}</td>
        <td>{{ item.description or '-' }}</td>
        <td>
          <a href="{{ url_for('admin_gallery', del=loop.index0) }}" class="btn btn-sm btn-danger" onclick="return confirm('Supprimer cet élément de la galerie?');">Suppr.</a>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  </div>
  {% else %}
    <p>Aucun élément dans la galerie.</p>
  {% endif %}
  <hr>
  <h6>Ajouter un nouvel élément</h6>
  <form method="post" enctype="multipart/form-data" class="row g-3">
    <div class="col-md-4">
      <label for="title" class="form-label">{{ 'Titre (optionnel)' if lang=='fr' else 'Title (optional)' }}</label>
      <input type="text" class="form-control" id="title" name="title" placeholder="{{ 'Titre de l\'élément' if lang=='fr' else 'Item title' }}">
    </div>
    <div class="col-md-4">
      <label for="description" class="form-label">{{ 'Description (optionnel)' if lang=='fr' else 'Description (optional)' }}</label>
      <input type="text" class="form-control" id="description" name="description" placeholder="{{ 'Description brève' if lang=='fr' else 'Brief description' }}">
    </div>
    <div class="col-md-4">
      <label for="url_input" class="form-label">{{ 'URL(s) image/vidéo (séparées par virgule)' if lang=='fr' else 'Image/Video URL(s) (comma-separated)' }}</label>
      <input type="text" class="form-control" id="url_input" name="url_input" placeholder="https://... , https://...">
      <div class="form-text">{{ 'Pour vues tournantes, séparez plusieurs URLs d’images par virgule.' if lang=='fr' else 'For rotation views, separate multiple image URLs by commas.' }}</div>
    </div>
    <div class="col-md-4">
      <label for="files" class="form-label">{{ 'Uploader fichier(s) image (optionnel)' if lang=='fr' else 'Upload image file(s) (optional)' }}</label>
      <input type="file" class="form-control" id="files" name="files" accept=".jpg,.jpeg,.png,.gif" multiple>
      <div class="form-text">{{ 'Pour vues tournantes, upload multiple images.' if lang=='fr' else 'For rotation views, upload multiple images.' }}</div>
    </div>
    <div class="col-md-4 d-flex align-items-end">
      <button type="submit" class="btn btn-contact">{{ 'Ajouter' if lang=='fr' else 'Add' }}</button>
    </div>
  </form>
  <div class="mt-3">
    <p class="small">{{ 'Les images uploadées sont stockées dans uploads/ et resteront disponibles.' if lang=='fr' else 'Uploaded images are stored in uploads/ and remain available.' }}</p>
  </div>
</div>
{% endblock %}
"""

# Template admin/analytics.html
admin_analytics_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_analytics') }}">Analytics</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Analytics du site</h5>
  <p><b>{{ 'Nombre total de messages' if lang=='fr' else 'Total messages' }}:</b> {{ total_msgs }}</p>
  <p><b>{{ 'Messages non lus' if lang=='fr' else 'Unread messages' }}:</b> {{ unread_msgs }}</p>
  <p><b>{{ 'Services proposés' if lang=='fr' else 'Services offered' }}:</b> {{ total_services }}</p>
  <p><b><a href="{{ url_for('admin_portfolio') }}">{{ 'Éléments du portfolio' if lang=='fr' else 'Portfolio items' }}</a>:</b> {{ total_portfolio }}</p>
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
{% endblock %}
"""

# Template admin/settings.html
admin_settings_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_settings') }}">Paramètres</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>{{ 'Paramètres du thème' if lang=='fr' else 'Theme Settings' }}</h5>
  <form method="post" class="row g-3" enctype="multipart/form-data">
    <div class="col-md-4">
      <label for="couleur" class="form-label">{{ 'Couleur principale (hex)' if lang=='fr' else 'Primary color (hex)' }}</label>
      <input type="text" class="form-control" id="couleur" name="couleur" value="{{ site.couleur }}" placeholder="#RRGGBB" required>
    </div>
    <div class="col-md-4">
      <label for="secondary" class="form-label">{{ 'Couleur secondaire (hex)' if lang=='fr' else 'Secondary color (hex)' }}</label>
      <input type="text" class="form-control" id="secondary" name="secondary" value="{{ site.secondary }}" placeholder="#RRGGBB">
    </div>
    <div class="col-md-4">
      <label for="accent" class="form-label">{{ 'Couleur accent (hex)' if lang=='fr' else 'Accent color (hex)' }}</label>
      <input type="text" class="form-control" id="accent" name="accent" value="{{ site.accent }}" placeholder="#RRGGBB">
    </div>
    <div class="col-md-4">
      <label for="font" class="form-label">{{ 'Police (Google Font ou locale)' if lang=='fr' else 'Font (Google Font or local)' }}</label>
      <input type="text" class="form-control" id="font" name="font" value="{{ site.font }}" placeholder="Montserrat">
    </div>
    <div class="col-md-4">
      <label class="form-label">{{ 'Photo de profil actuelle' if lang=='fr' else 'Current profile photo' }}</label><br>
      {% if site.photo %}
        <img src="{{ site.photo }}" alt="Photo profil" style="max-height:100px; border-radius:50%; border:2px solid var(--color-primary);">
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
{% endblock %}
"""

# Template admin/traffic.html
admin_traffic_template = """
{% extends "base.html" %}
{% block content %}
<div class="admin-nav text-center mb-3">
  <a href="{{ url_for('admin_index') }}">Accueil admin</a> |
  <a href="{{ url_for('admin_traffic') }}">Trafic</a> |
  <a href="{{ url_for('admin_logout') }}">Logout</a>
</div>
<div class="admin-panel" data-aos="fade-up">
  <h5>Logs de trafic</h5>
  <form method="get" class="row mb-3">
    <div class="col-md-4">
      <input type="text" name="search" value="{{ search_query }}" class="form-control" placeholder="Rechercher chemin ou IP...">
    </div>
    <div class="col-md-2">
      <button class="btn btn-primary" type="submit">Search</button>
    </div>
  </form>
  {% if logs %}
  <table class="table table-hover admin-table">
    <thead><tr><th>#</th><th>Timestamp</th><th>Path</th><th>Method</th><th>Remote Addr</th></tr></thead>
    <tbody>
    {% for log in logs %}
      <tr>
        <td>{{ loop.index0 + (page-1)*per_page }}</td>
        <td>{{ log.timestamp }}</td>
        <td>{{ log.path }}</td>
        <td>{{ log.method }}</td>
        <td>{{ log.remote_addr }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <nav>
    <ul class="pagination">
      {% set total_pages = (total_logs // per_page) + (1 if total_logs % per_page else 0) %}
      {% for p in range(1, total_pages+1) %}
      <li class="page-item {% if p==page %}active{% endif %}">
        <a class="page-link" href="{{ url_for('admin_traffic', page=p, search=search_query) }}">{{ p }}</a>
      </li>
      {% endfor %}
    </ul>
  </nav>
  {% else %}
    <p>Aucun log.</p>
  {% endif %}
</div>
{% endblock %}
"""

# On crée le DictLoader pour Jinja
template_dict = {
    "base.html": base_template,
    "index.html": index_template,
    "services.html": services_template,
    "portfolio.html": portfolio_template,
    "galleries.html": galleries_template,
    "pourquoi.html": pourquoi_template,
    "contact.html": contact_template,
    "admin/login.html": admin_login_template,
    "admin/index.html": admin_index_template,
    "admin/services.html": admin_services_template,
    "admin/portfolio.html": admin_portfolio_template,
    "admin/atouts.html": admin_atouts_template,
    "admin/messages.html": admin_messages_template,
    "admin/message_view.html": admin_message_view_template,
    "admin/carousel.html": admin_carousel_template,
    "admin/gallery.html": admin_gallery_template,
    "admin/analytics.html": admin_analytics_template,
    "admin/settings.html": admin_settings_template,
    "admin/traffic.html": admin_traffic_template,
}
app.jinja_loader = DictLoader(template_dict)

# ----------------------------------------
# ROUTE ADMIN SETTINGS (après loader)
# ----------------------------------------
@app.route(f'/{ADMIN_SECRET_URL}/settings', methods=['GET', 'POST'])
@admin_login_required
def admin_settings():
    lang = session.get("lang", "fr")
    if request.method == "POST":
        changed = False
        nouvelle_couleur = request.form.get("couleur","").strip()
        nouvelle_secondary = request.form.get("secondary","").strip()
        nouvelle_accent = request.form.get("accent","").strip()
        nouvelle_font = request.form.get("font","").strip()
        nouvelle_photo_url = request.form.get("photo_url","").strip()
        photo_file = request.files.get("photo_file")
        # Couleur principale
        if nouvelle_couleur:
            if nouvelle_couleur.startswith("#") and len(nouvelle_couleur)==7:
                SITE["couleur"] = nouvelle_couleur
                config_theme["couleur"] = nouvelle_couleur
                changed = True
            else:
                flash("Format de couleur invalide. Utilisez #RRGGBB.", "warning")
        # Couleur secondaire
        if nouvelle_secondary:
            if nouvelle_secondary.startswith("#") and len(nouvelle_secondary)==7:
                SITE["secondary"] = nouvelle_secondary
                config_theme["secondary"] = nouvelle_secondary
                changed = True
            else:
                flash("Format de couleur secondaire invalide. Utilisez #RRGGBB.", "warning")
        # Couleur accent
        if nouvelle_accent:
            if nouvelle_accent.startswith("#") and len(nouvelle_accent)==7:
                SITE["accent"] = nouvelle_accent
                config_theme["accent"] = nouvelle_accent
                changed = True
            else:
                flash("Format de couleur accent invalide. Utilisez #RRGGBB.", "warning")
        # Font
        if nouvelle_font:
            SITE["font"] = nouvelle_font
            config_theme["font"] = nouvelle_font
            changed = True
        # Photo
        if photo_file and photo_file.filename:
            ext = photo_file.filename.rsplit('.', 1)[1].lower() if '.' in photo_file.filename else ''
            if ext in IMAGE_EXTENSIONS:
                filename = secure_filename(f"profile_{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo_file.filename}")
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                photo_file.save(save_path)
                photo_path = url_for('uploaded_file', filename=filename)
                SITE["photo"] = photo_path
                config_theme["photo"] = photo_path
                changed = True
            else:
                flash("Fichier de profil non valide. Extensions autorisées: jpg, jpeg, png, gif.", "warning")
        else:
            if nouvelle_photo_url:
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
    return render_template("admin/settings.html", titre_page="Paramètres")

# ----------------------------------------
# LANCEMENT DE L’APPLICATION
# ----------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    debug_env = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
    app.run(host=host, port=port, debug=debug_env)
