from functools import wraps
from flask import request, jsonify
from backend.common.store import Database

# Globale DB-Instanz
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

def auth_required(fn):
    """
    Decorator, der prüft, ob der Request ein gültiges Token enthält.
    Erwartet Header: Authorization: Bearer <token>
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing_token"}), 401

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"error": "empty_token"}), 401

        row = db.query_one("SELECT user_id FROM auth_tokens WHERE token= %s", (token,))
        if not row:
            return jsonify({"error": "invalid_token"}), 401

        request.uid = row["user_id"]
        return fn(*args, **kwargs)

    return wrapper

