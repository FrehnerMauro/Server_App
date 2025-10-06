# backend/routes/notifications.py
from flask import Blueprint, jsonify, request
from backend.common.auth import auth_required
from backend.common.store import state, save

bp = Blueprint("notifications", __name__)

@bp.get("/notifications")
@auth_required
def list_notifications():
    st = state()
    uid = request.uid
    res = [n for n in st.get("notifications", []) if n.get("userId") == uid]
    # optional: neueste zuerst
    res.sort(key=lambda x: x.get("createdAt", 0), reverse=True)
    return jsonify(res)

@bp.post("/notifications/<int:nid>/read")
@auth_required
def mark_read(nid: int):
    st = state()
    uid = request.uid
    for n in st.get("notifications", []):
        # nur eigene Notifications lesen/ändern
        if n.get("id") == nid and n.get("userId") == uid:
            n["read"] = True
            save()
            return jsonify({"ok": True})
    return jsonify({"error": "not_found"}), 404