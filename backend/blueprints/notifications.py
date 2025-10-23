from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms

bp = Blueprint("notifications", __name__)
db = Database("state.db")


@bp.get("/notifications")
@auth_required
def list_notifications():
    uid = request.uid
    rows = db.query("""
        SELECT 
            id,
            user_id,
            message,
            type,
            read,
            created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (uid,))
    return jsonify(rows)


@bp.post("/notifications/mark_read/<int:notification_id>")
@auth_required
def mark_read(notification_id: int):
    notif = db.find("notifications", id=notification_id)
    if not notif or notif["user_id"] != request.uid:
        return jsonify({"error": "not_found"}), 404

    db.update("notifications", {"read": 1}, "id=?", (notification_id,))
    return jsonify({"ok": True})


@bp.delete("/notifications/clear")
@auth_required
def clear_notifications():
    db.delete("notifications", "user_id=?", (request.uid,))
    return jsonify({"ok": True})


@bp.post("/notifications/create")
def create_notification():
    """Hilfsroute für Tests – erstellt eine Notification."""
    data = request.get_json(silent=True) or {}
    uid = data.get("user_id")
    msg = data.get("message") or "Neue Benachrichtigung"
    ntype = data.get("type") or "info"

    if not uid:
        return jsonify({"error": "user_id_required"}), 400

    db.insert("notifications", {
        "user_id": uid,
        "message": msg,
        "type": ntype,
        "created_at": now_ms(),
        "read": 0
    })
    return jsonify({"ok": True})