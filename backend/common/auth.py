# common/auth.py
from functools import wraps
from flask import request, jsonify
from backend.common.store import state

def auth_required(fn):
    """
    Prueft auf Authorization: Bearer <token>.
    Legt bei Erfolg request.uid (int) fuer den aktuellen User.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "").strip()
        token = None
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

        tokens = state().get("auth", {}).get("tokens", {})
        if not token or token not in tokens:
            return jsonify({"error": "unauthorized"}), 401

        request.uid = tokens[token]
        return fn(*args, **kwargs)
    return wrapper