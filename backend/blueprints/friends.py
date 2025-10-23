from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms

bp = Blueprint("friends", __name__)
db = Database("state.db")

# ============================================================
# FRIEND REQUESTS (Pending)
# ============================================================

@bp.get("/friends/requests")
@auth_required
def list_friend_requests():
    """Zeigt alle offenen Freundschaftsanfragen, die an den eingeloggten User gerichtet sind."""
    uid = request.uid
    rows = db.query("""
        SELECT 
            f.id,
            f.user_id AS from_user_id,
            f.friend_id AS to_user_id,
            f.status,
            f.created_at,
            u.display_name,
            u.avatar_url
        FROM user_friends f
        JOIN users u ON u.id = f.user_id
        WHERE f.friend_id = ? AND f.status = 'pending'
        ORDER BY f.created_at DESC
    """, (uid,))
    return jsonify(rows)

# ============================================================
# SEND REQUEST
# ============================================================

@bp.post("/friends/request/<int:to_user_id>")
@auth_required
def send_friend_request(to_user_id: int):
    """Sende eine Freundschaftsanfrage."""
    uid = request.uid
    if uid == to_user_id:
        return jsonify({"error": "cannot_add_self"}), 400

    # Prüfen ob bestehende Freundschaft oder Anfrage
    existing = db.query_one("""
        SELECT * FROM user_friends
        WHERE 
            (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)
    """, (uid, to_user_id, to_user_id, uid))

    if existing:
        match existing["status"]:
            case "pending":  return jsonify({"error": "already_requested"}), 400
            case "accepted": return jsonify({"error": "already_friends"}), 400
            case "blocked":  return jsonify({"error": "blocked"}), 403

    db.insert("user_friends", {
        "user_id": uid,
        "friend_id": to_user_id,
        "status": "pending",
        "created_at": now_ms(),
        "updated_at": now_ms()
    })
    return jsonify({"ok": True, "message": "request_sent"})

# ============================================================
# ACCEPT REQUEST
# ============================================================

@bp.post("/friends/accept/<int:request_id>")
@auth_required
def accept_friend_request(request_id: int):
    """Akzeptiere eine eingehende Freundschaftsanfrage."""
    req = db.query_one("SELECT * FROM user_friends WHERE id=?", (request_id,))
    if not req:
        return jsonify({"error": "not_found"}), 404
    if req["friend_id"] != request.uid:
        return jsonify({"error": "forbidden"}), 403

    db.update(
        "user_friends",
        {"status": "accepted", "updated_at": now_ms()},
        "id=?",
        (request_id,)
    )
    return jsonify({"ok": True, "message": "request_accepted"})

# ============================================================
# DECLINE REQUEST
# ============================================================

@bp.post("/friends/decline/<int:request_id>")
@auth_required
def decline_friend_request(request_id: int):
    """Lehne eine eingehende Freundschaftsanfrage ab."""
    req = db.query_one("SELECT * FROM user_friends WHERE id=?", (request_id,))
    if not req:
        return jsonify({"error": "not_found"}), 404
    if req["friend_id"] != request.uid:
        return jsonify({"error": "forbidden"}), 403

    db.update(
        "user_friends",
        {"status": "declined", "updated_at": now_ms()},
        "id=?",
        (request_id,)
    )
    return jsonify({"ok": True, "message": "request_declined"})

# ============================================================
# FRIEND LIST (Accepted)
# ============================================================

@bp.get("/friends/list")
@auth_required
def list_friends():
    """Zeigt alle bestätigten Freunde des eingeloggten Users."""
    uid = request.uid
    rows = db.query("""
        SELECT 
            CASE 
                WHEN f.user_id = ? THEN f.friend_id
                ELSE f.user_id
            END AS friend_id,
            u.display_name,
            u.avatar_url,
            u.email
        FROM user_friends f
        JOIN users u ON u.id = CASE 
            WHEN f.user_id = ? THEN f.friend_id
            ELSE f.user_id
        END
        WHERE (f.user_id = ? OR f.friend_id = ?)
          AND f.status = 'accepted'
        ORDER BY u.display_name
    """, (uid, uid, uid, uid))
    return jsonify(rows)