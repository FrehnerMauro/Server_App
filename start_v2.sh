#!/bin/bash

# ==============================================================================
# SocialHabit API - Production Start Script
# ==============================================================================

set -e

echo "======================================"
echo "🚀 Starting SocialHabit API"
echo "======================================"

# Aktiviere Virtual Environment
if [ -d ".venv" ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv .venv"
    exit 1
fi

# Prüfe ob .env existiert
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "Copying .env.example to .env..."
    cp .env.example .env
    echo "⚠️  Please configure .env before continuing!"
    exit 1
fi

# Lade Environment Variables (sicher, ignoriert Kommentare und leere Zeilen)
set -a
source .env
set +a

# Setze PYTHONPATH auf das Projekt-Root-Verzeichnis
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

# Prüfe Dependencies
echo "📚 Checking dependencies..."
pip install -q -r backend/requirements_v2.txt

# Erstelle Logs-Verzeichnis
mkdir -p logs

# Starte Server
echo "🌐 Starting server..."
echo "Environment: ${ENVIRONMENT:-development}"
echo "Host: ${HOST:-0.0.0.0}"
echo "Port: ${PORT:-8000}"
echo "======================================"

# Starte mit Gunicorn (Production) oder Flask (Development)
if [ "${ENVIRONMENT}" = "production" ]; then
    echo "Starting with Gunicorn (Production)..."
    exec gunicorn -c gunicorn.conf.py "backend.app_v2:create_app()"
else
    echo "Starting with Flask Development Server..."
    exec python backend/app_v2.py
fi
