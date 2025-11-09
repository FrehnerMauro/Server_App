"""
WSGI entrypoint for production and development.
Use this file when running with Gunicorn or another WSGI server.
"""

import sys, os

print("🔍 PYTHON EXEC:", sys.executable)
print("🔍 sys.path:")
for p in sys.path:
    print("   ", p)
print("🔍 CWD:", os.getcwd())

from backend.app import create_app

# Die Flask-App über Factory erstellen
app = create_app()

# Optionaler Einstiegspunkt für direktes Ausführen
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)