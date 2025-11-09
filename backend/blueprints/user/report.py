from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms

bp = Blueprint("report", __name__)
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

# ============================================================
# CREATE REPORT
# ============================================================

@bp.post("/report")
@auth_required
def create_report():
    """
    Meldet einen Benutzer, Kommentar, Challenge, Nachricht oder Beitrag (Post).
    """
    data = request.get_json(silent=True) or {}
    from_user_id = request.uid

    # Erlaubte Felder
    user_id = data.get("user_id")
    challenge_id = data.get("challenge_id")
    message_id = data.get("message_id")
    comment_id = data.get("comment_id")
    post_id = data.get("post_id")
    reason = (data.get("reason") or "").strip()

    # Sicherstellen, dass mindestens ein Ziel gesetzt ist
    if not any([user_id, challenge_id, message_id, comment_id, post_id]):
        return jsonify({"error": "missing_target"}), 400

    # Leerer Grund nicht erlaubt (bessere Moderation)
    if not reason:
        return jsonify({"error": "missing_reason"}), 400

    # In DB speichern
    db.insert("reports", {
        "from_user_id": from_user_id,
        "user_id": user_id,
        "challenge_id": challenge_id,
        "message_id": message_id,
        "comment_id": comment_id,
        "post_id": post_id,
        "reason": reason,
        "created_at": now_ms()
    })

    return jsonify({"ok": True, "message": "report_submitted"})