"""
SocialHabit API - Modernized Flask Application.
Production-ready Backend mit sauberer Architektur.
"""
from flask import Flask, jsonify
from flask_cors import CORS

from backend.core.config import get_settings
from backend.core.logging import setup_logging, get_logger
from backend.core.database import init_database_pool, close_database_pool
from backend.api.middleware import setup_all_middleware

# API Routes (neue V2-Architektur)
from backend.api.routes import (
    auth_routes,
    user_routes,
    challenge_routes,
    friend_routes,
    notification_routes,
)

# Legacy Routes (alte Frontend-Kompatibilität)
from backend.blueprints.user import (
    auth_routes as legacy_auth_routes,
    challenges as legacy_challenges,
    feed as legacy_feed,
    friends as legacy_friends,
    users as legacy_users,
    notifications as legacy_notifications,
    settings as legacy_settings,
    stats as legacy_stats,
)

logger = get_logger(__name__)


def create_app() -> Flask:
    """
    Factory-Funktion zur Erstellung der Flask-App.
    
    Returns:
        Konfigurierte Flask-App Instanz
    """
    # Lade Settings
    settings = get_settings()
    
    # Setup Logging
    setup_logging()
    
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info("=" * 60)
    
    # Erstelle Flask App
    app = Flask(__name__)
    
    # App Config
    app.config["DEBUG"] = settings.debug
    app.config["TESTING"] = False
    app.config["SECRET_KEY"] = settings.secret_key
    
    # CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": settings.cors_origins}},
        supports_credentials=settings.cors_allow_credentials,
        allow_headers=settings.cors_allow_headers,
        methods=settings.cors_allow_methods
    )
    
    logger.info("CORS configured")
    
    # Middleware
    setup_all_middleware(app)
    
    # Database Pool initialisieren
    init_database_pool()
    logger.info("Database pool initialized")
    
    # Register NEW V2 Blueprints (under /api/v2)
    app.register_blueprint(auth_routes.bp, url_prefix="/api/v2/auth")
    app.register_blueprint(user_routes.bp, url_prefix="/api/v2/users")
    app.register_blueprint(challenge_routes.bp, url_prefix="/api/v2/challenges")
    app.register_blueprint(friend_routes.bp, url_prefix="/api/v2/friends")
    app.register_blueprint(notification_routes.bp, url_prefix="/api/v2/notifications")
    
    # Register LEGACY Blueprints (they already have their own prefixes like /feed, /challenges, etc.)
    app.register_blueprint(legacy_auth_routes.bp, name="legacy_auth")
    app.register_blueprint(legacy_challenges.bp, name="legacy_challenges")
    app.register_blueprint(legacy_feed.bp, name="legacy_feed")
    app.register_blueprint(legacy_friends.bp, name="legacy_friends")
    app.register_blueprint(legacy_users.bp, name="legacy_users")
    app.register_blueprint(legacy_notifications.bp, name="legacy_notifications")
    app.register_blueprint(legacy_settings.bp, name="legacy_settings")
    app.register_blueprint(legacy_stats.bp, name="legacy_stats")
    
    logger.info("All blueprints registered (V2 + Legacy)")
    
    # Health Check Endpoint
    @app.get("/health")
    def health_check():
        """
        Health Check Endpoint für Monitoring.
        
        Returns:
            200: {status: "ok", version: str, environment: str}
        """
        return jsonify({
            "status": "ok",
            "version": settings.app_version,
            "environment": settings.environment,
            "app_name": settings.app_name
        }), 200
    
    @app.get("/")
    def root():
        """
        Root Endpoint mit API-Info.
        
        Returns:
            200: API Information
        """
        return jsonify({
            "message": f"Welcome to {settings.app_name}",
            "version": settings.app_version,
            "environment": settings.environment,
            "docs": "/api/docs (coming soon)",
            "health": "/health"
        }), 200
    
    # Shutdown Handler
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Cleanup bei App-Shutdown."""
        if exception:
            logger.error(f"Teardown exception: {exception}")
    
    # App-Shutdown Hook
    import atexit
    
    def cleanup():
        """Cleanup-Funktion beim Beenden."""
        logger.info("Shutting down application...")
        close_database_pool()
        logger.info("Database pool closed")
    
    atexit.register(cleanup)
    
    logger.info("Application initialized successfully")
    logger.info(f"Server will run on http://{settings.host}:{settings.port}")
    
    return app


def run_development_server():
    """
    Startet Development Server.
    Nur für lokale Entwicklung verwenden!
    """
    settings = get_settings()
    
    app = create_app()
    
    logger.warning("=" * 60)
    logger.warning("DEVELOPMENT SERVER - DO NOT USE IN PRODUCTION!")
    logger.warning("=" * 60)
    
    app.run(
        host=settings.host,
        port=settings.port,
        debug=settings.debug,
        use_reloader=settings.is_development
    )


if __name__ == "__main__":
    run_development_server()
