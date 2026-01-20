"""
WSGI Entry Point für Production Deployment.
"""
import os
import sys

# Füge Project Root zum Python Path hinzu
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from backend.app_v2 import create_app

# Erstelle App-Instanz
application = create_app()

# Für Gunicorn
app = application

if __name__ == "__main__":
    # Fallback für direkte Ausführung
    from backend.app_v2 import run_development_server
    run_development_server()
