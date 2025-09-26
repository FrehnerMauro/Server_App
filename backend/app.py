from flask import Flask
from backend.common.store import load
from backend.blueprints import auth_routes, users, friends, challenges, feed, notifications, admin

def create_app():
    app = Flask(__name__)
    load()  # state.json laden oder Defaults setzen

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(friends.bp)
    app.register_blueprint(challenges.bp)
    app.register_blueprint(feed.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(admin.bp)

    @app.get("/")
    def root():
        return {"ok": True, "service": "social-habit-backend"}

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)