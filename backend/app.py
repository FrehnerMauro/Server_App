from flask import Flask
from backend.common.store import load
from backend.blueprints import auth_routes, users, friends, challenges, feed, notifications, admin, ai_chat

def create_app():
    app = Flask(__name__)
    load()

    # Blueprints registrieren
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(friends.bp)
    app.register_blueprint(challenges.bp)
    app.register_blueprint(feed.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(ai_chat.bp)  # <--- Neu

    # Ollama lokal auf dem gleichen iMac
    app.config["OLLAMA_BASE_URL"] = "http://localhost:11434"



    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)