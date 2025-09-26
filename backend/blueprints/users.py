from flask import Blueprint, jsonify, request
from backend.common.auth import auth_required
from backend.common.store import state

bp = Blueprint("users", __name__)

@bp.get("/users")
@auth_required
def list_users():
    return jsonify(list(state()["users"].values()))

@bp.get("/users/bulk")
@auth_required
def users_bulk():
    ids = (request.args.get("ids") or "").split(",")
    ids = [s.strip() for s in ids if s.strip()]
    all_users = state()["users"]
    res = [all_users[k] for k in ids if k in all_users or k.isdigit() and str(int(k)) in all_users]
    # fallback: durch numeric
    res = []
    for s in ids:
        key = s if s in all_users else str(int(s)) if s.isdigit() else None
        if key and key in all_users:
            res.append(all_users[key])
    return jsonify(res)

@bp.get("/users/<int:uid>")
@auth_required
def get_user(uid: int):
    u = state()["users"].get(str(uid))
    if not u:
        return jsonify({"error": "not_found"}), 404
    return jsonify(u)