# Plan Revit BIM - Professional Portfolio Website

A modern, bilingual (French/English) portfolio website for a Civil Engineer and BIM Specialist. This Flask-based application showcases services, portfolio projects, and provides a contact form for potential clients.

## 🌟 Features

- **Bilingual Support**: Full French and English language support
- **Responsive Design**: Mobile-friendly Bootstrap 5 interface
- **Dark Mode**: Toggle between light and dark themes
- **Dynamic Content**: 
  - Services showcase
  - Portfolio gallery with image carousel
  - 360° rotation viewer for project models
  - Contact form with file uploads
- **Admin Dashboard**:
  - Manage services, portfolio items, and content
  - View and respond to contact messages
  - Traffic analytics
  - Theme customization
  - Carousel management

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/issou2025/plan-revit-bim.git
cd plan-revit-bim
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Create a `.env` file for configuration:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run the application:
```bash
python app.py
```

5. Access the website at `http://localhost:5000`

## 🔧 Configuration

The application can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `UPLOAD_FOLDER` | Directory for uploaded files | `uploads` |
| `ADMIN_USER` | Admin username | `bacseried@gmail.com` |
| `ADMIN_PASS` | Admin password | `mx23fy` |
| `ADMIN_SECRET_URL` | Secret URL path for admin access | `issoufouachraf_2025` |
| `SECRET_KEY` | Flask secret key for sessions | `super_secret_key_2024` |
| `PORT` | Server port | `5000` |
| `DEBUG` | Debug mode | `False` |

**⚠️ Security Note**: Always change the default credentials and secret key in production!

## 📁 Project Structure

```
plan-revit-bim/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── uploads/           # Uploaded files and data (created automatically)
├── .env.example       # Example environment configuration
└── README.md          # This file
```

## 🎨 Admin Panel

Access the admin panel at `http://localhost:5000/{ADMIN_SECRET_URL}/login`

Default credentials (⚠️ CHANGE IN PRODUCTION):
- Username: `bacseried@gmail.com`
- Password: `mx23fy`

Features:
- Content management (services, portfolio, advantages)
- Message inbox
- Image carousel management
- Gallery with 360° rotation views
- Theme customization (colors, fonts, profile photo)
- Traffic analytics

## 🛠️ Tech Stack

- **Backend**: Flask 2.2+
- **Frontend**: Bootstrap 5, AOS animations, Bootstrap Icons
- **Image Processing**: SpriteSpin for 360° views
- **Storage**: JSON-based data persistence

## 📄 License

This project is private. All rights reserved.

## 👤 Author

**Issoufou Abdou Chefou**
- Civil Engineer & BIM Specialist
- Email: entreprise2rc@gmail.com
- Phone: +227 96 38 08 77
- LinkedIn: [Abdou Chefou Issoufou](https://www.linkedin.com/in/abdou-chefou-issoufou-99555684)

## 🤝 Support

For support or inquiries, please contact via:
- Email: entreprise2rc@gmail.com
- WhatsApp: +227 96 38 08 77
