from flask import Blueprint, jsonify, request
from backend.common.auth import auth_required
from backend.common.store import Database

bp = Blueprint("users", __name__)
db = Database("state.db")

# ============================================================
# Alle Benutzer abrufen
# ============================================================

@bp.get("/users")
@auth_required
def list_users():
    users = db.query("""
        SELECT id, vorname, name, email, avatar, is_admin
        FROM users
        ORDER BY id ASC
    """)
    return jsonify(users)

# ============================================================
# Mehrere Benutzer (Bulk) abrufen
# ============================================================

@bp.get("/users/bulk")
@auth_required
def users_bulk():
    ids_raw = (request.args.get("ids") or "").strip()
    if not ids_raw:
        return jsonify([])
    try:
        ids = [int(x) for x in ids_raw.split(",") if x.strip().isdigit()]
    except ValueError:
        return jsonify({"error": "invalid_ids"}), 400

    placeholders = ",".join(["?"] * len(ids))
    users = db.query(f"""
        SELECT id, vorname, name, email, avatar, is_admin
        FROM users
        WHERE id IN ({placeholders})
    """, tuple(ids))

    return jsonify(users)

# ============================================================
# Einzelnen Benutzer abrufen
# ============================================================

@bp.get("/users/<int:uid>")
@auth_required
def get_user(uid: int):
    user = db.query_one("""
        SELECT id, vorname, name, email, avatar, is_admin
        FROM users
        WHERE id=?
    """, (uid,))
    if not user:
        return jsonify({"error": "not_found"}), 404
    return jsonify(user)