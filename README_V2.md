# SocialHabit API v2.0

Modernized, production-ready backend with clean architecture and separation of concerns.

## 🏗️ Architecture

```
backend/
├── api/              # HTTP Layer (Routes, Middleware, Decorators)
├── core/             # Core Infrastructure (Config, Database, DI Container)
├── domain/           # Domain Models (Business Entities)
├── repositories/     # Data Access Layer (Database Operations)
├── schemas/          # DTOs (Request/Response Models)
└── services/         # Business Logic Layer
```

## ✨ Features

- **Clean Architecture**: Separation of Concerns mit klarer Layer-Struktur
- **Repository Pattern**: Abstrahierte Datenbankzugriffe
- **Service Layer**: Komplette Business-Logik getrennt von HTTP
- **Dependency Injection**: Container-basiertes Service-Management
- **Type Safety**: Pydantic V2 für Validierung und DTOs
- **Connection Pooling**: Optimierte Datenbank-Performance
- **Structured Logging**: Request-IDs, strukturierte Logs
- **Error Handling**: Globale Exception-Handler mit sauberen API-Responses
- **Security Headers**: Production-ready Security
- **CORS**: Konfigurierbare Cross-Origin Resource Sharing
- **Environment-based Config**: Pydantic Settings mit .env Support
- **Health Checks**: Monitoring-Endpoints
- **Production-ready**: Gunicorn Configuration

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Kopiere .env.example nach .env
cp .env.example .env

# Passe .env an (Database URL, Secret Key, etc.)
nano .env
```

### 2. Install Dependencies

```bash
# Erstelle Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oder
.venv\Scripts\activate  # Windows

# Installiere Dependencies
pip install -r backend/requirements_v2.txt
```

### 3. Run Development Server

```bash
# Mit Flask Development Server
python backend/app_v2.py

# Oder mit Gunicorn (Production-like)
gunicorn -c gunicorn.conf.py "backend.app_v2:create_app()"
```

## 📝 API Endpoints

### Authentication
- `POST /api/auth/register` - Registrierung
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Aktueller User
- `POST /api/auth/refresh` - Token erneuern

### Users
- `GET /api/users/me` - Eigenes Profil
- `GET /api/users/<id>` - User laden
- `PATCH /api/users/me` - Profil aktualisieren
- `GET /api/users/search?q=<query>` - User suchen
- `GET /api/users` - User auflisten (paginiert)

### Challenges
- `POST /api/challenges` - Challenge erstellen
- `GET /api/challenges` - Eigene Challenges
- `GET /api/challenges/<id>` - Challenge-Details
- `POST /api/challenges/<id>/confirm` - Challenge bestätigen
- `GET /api/challenges/<id>/chat` - Chat laden
- `POST /api/challenges/<id>/chat` - Chat-Message posten
- `GET /api/challenges/<id>/members` - Mitglieder

### Friends
- `GET /api/friends` - Freundesliste
- `POST /api/friends/requests` - Freundschaftsanfrage senden
- `GET /api/friends/requests/incoming` - Eingehende Anfragen
- `GET /api/friends/requests/outgoing` - Ausgehende Anfragen
- `POST /api/friends/requests/<id>/accept` - Anfrage akzeptieren
- `POST /api/friends/requests/<id>/decline` - Anfrage ablehnen
- `DELETE /api/friends/<id>` - Freund entfernen

### Notifications
- `GET /api/notifications` - Benachrichtigungen laden
- `GET /api/notifications/unread-count` - Anzahl ungelesener
- `POST /api/notifications/<id>/read` - Als gelesen markieren
- `POST /api/notifications/mark-all-read` - Alle als gelesen
- `DELETE /api/notifications/<id>` - Löschen

### Health
- `GET /health` - Health Check
- `GET /` - API Info

## 🔐 Authentication

Alle geschützten Endpoints benötigen einen Bearer Token im Authorization-Header:

```
Authorization: Bearer <token>
```

## 🏭 Production Deployment

### Mit Gunicorn

```bash
# Starte mit Gunicorn
gunicorn -c gunicorn.conf.py "backend.app_v2:create_app()"

# Mit Custom Worker Count
WORKERS=8 gunicorn -c gunicorn.conf.py "backend.app_v2:create_app()"
```

### Environment Variables

Wichtige Production-Einstellungen in `.env`:

```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-secure-key>
DATABASE_URL=postgresql://user:pass@host:5432/db
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=WARNING
```

### Systemd Service (Linux)

```bash
# Erstelle /etc/systemd/system/socialhabit.service
[Unit]
Description=SocialHabit API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/Server_App
Environment="PATH=/path/to/Server_App/.venv/bin"
ExecStart=/path/to/Server_App/.venv/bin/gunicorn -c gunicorn.conf.py "backend.app_v2:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target

# Aktiviere Service
sudo systemctl enable socialhabit
sudo systemctl start socialhabit
```

## 🧪 Testing

```bash
# Run alle Tests
pytest

# Mit Coverage
pytest --cov=backend --cov-report=html

# Nur Unit Tests
pytest tests/unit/

# Nur Integration Tests
pytest tests/integration/
```

## 📊 Code Quality

```bash
# Formatierung mit Black
black backend/

# Import Sortierung
isort backend/

# Linting mit Flake8
flake8 backend/

# Type Checking mit Mypy
mypy backend/
```

## 🐛 Debugging

### Logs ansehen

```bash
# Development
tail -f logs/app.log

# Production (Systemd)
journalctl -u socialhabit -f
```

### Request IDs

Jeder Request erhält eine eindeutige ID:

```
X-Request-ID: <uuid>
```

Diese ID ist in allen Logs und Error-Responses enthalten.

## 📈 Performance

- **Connection Pooling**: 20 Connections per Default (konfigurierbar)
- **Worker Processes**: Auto-detect (CPU-count * 2 + 1)
- **Request Timeouts**: 30s per Default
- **Keep-Alive**: 2s

## 🔧 Configuration

Alle Settings in `backend/core/config.py` sind über Environment Variables konfigurierbar.

Siehe `.env.example` für vollständige Liste.

## 📝 Migration vom alten Code

Das alte Backend liegt noch unter:
- `backend/app.py` (alt)
- `backend/blueprints/` (alt)

Das neue Backend:
- `backend/app_v2.py` (neu)
- `backend/api/routes/` (neu)

Beide können parallel laufen (verschiedene Ports).

## 🆘 Troubleshooting

### Database Connection Errors

```bash
# Prüfe PostgreSQL Status
sudo systemctl status postgresql

# Teste Connection
psql postgresql://mauro:1234@localhost:5432/socialhabit
```

### Import Errors

```bash
# Prüfe Python Path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Worker Timeouts

```bash
# Erhöhe Timeout in gunicorn.conf.py
timeout = 60
```

## 📚 Documentation

- `/health` - Health Check Endpoint
- `/` - API Info
- [Swagger/OpenAPI - Coming Soon]

## 👥 Contributing

1. Code-Style: Black + Flake8
2. Tests: Pytest
3. Type Hints: Alle Public Functions
4. Docstrings: Google Style

## 📄 License

Proprietary - Alle Rechte vorbehalten
