from backend.blueprints.admin import admin
from flask import Flask
from flask_cors import CORS

# Blueprints
from backend.blueprints.user import (
    auth_routes,
    users,
    friends,
    challenges,
    feed,
    notifications,
    report,
    settings,
    stats
)

def create_app():
    """Erzeugt die Flask-App-Instanz."""
    app = Flask(__name__)
    app.config['DEBUG'] = True

    # ----------------------------------------------------
    # CORS aktivieren (für Frontend-Kommunikation)
    # ----------------------------------------------------
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # ----------------------------------------------------
    # Blueprints registrieren
    # ----------------------------------------------------
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(friends.bp)
    app.register_blueprint(challenges.bp)
    app.register_blueprint(feed.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(report.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(stats.bp)



    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)