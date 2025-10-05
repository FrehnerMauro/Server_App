# wsgi.py
from backend.app import create_app  # oder: from app import app
app = create_app()                  # falls Factory; sonst einfach: app = app
