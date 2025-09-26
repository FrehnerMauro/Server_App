from flask import Blueprint, jsonify
from backend.common.auth import auth_required
from backend.common.store import state

bp = Blueprint("notifications", __name__)

@bp.get("/notifications")
@auth_required
def list_notifications():
    st = state()
    uid = getattr(__import__("flask").request, "uid")
    res = [n for n in st.get("notifications", []) if n["userId"] == uid]
    return jsonify(res)

@bp.post("/notifications/<int:nid>/read")
@auth_required
def mark_read(nid: int):
    st = state()
    for n in st.get("notifications", []):
        if n["id"] == nid:
            n["read"] = True
            from common.store import save
            save()
            return jsonify({"ok": True})
    return jsonify({"error": "not_found"}), 404