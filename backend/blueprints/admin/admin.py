from flask import Blueprint, request, jsonify
import base64, hashlib
from functools import wraps
from backend.common.store import Database, now_ms

bp = Blueprint("admin", __name__, url_prefix="/admin")
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

# ============================================================
# HELPER
# ============================================================

def _hash(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _parse_basic_auth():
    """Parst den Basic-Auth-Header (email:password)."""
    auth = (request.headers.get("Authorization") or "").strip()
    if not auth.lower().startswith("basic "):
        return None, None
    try:
        raw = base64.b64decode(auth.split(" ", 1)[1].strip()).decode("utf-8")
        email, pw = raw.split(":", 1)
        return (email or "").strip().lower(), pw
    except Exception:
        return None, None


def _check_admin_credentials(email: str, password: str) -> dict | None:
    """Validiert Admin-Zugangsdaten gegen DB."""
    if not email or not password:
        return None
    user = db.query_one("SELECT * FROM users WHERE email=%s LIMIT 1", (email,))
    if not user or user.get("password") != _hash(password) or not user.get("is_admin"):
        return None
    return user


def admin_required(fn):
    """Decorator für Basic-Auth-geschützte Admin-Endpunkte."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        email, pw = _parse_basic_auth()
        user = _check_admin_credentials(email, pw)
        if not user:
            resp = jsonify({"error": "unauthorized", "message": "basic auth required"})
            resp.status_code = 401
            resp.headers["WWW-Authenticate"] = 'Basic realm="admin", charset="UTF-8"'
            return resp
        request.admin_user = user
        return fn(*args, **kwargs)
    return wrapper


# ============================================================
# AUTH / INFO
# ============================================================

@bp.post("/login")
def admin_login():
    """Stateless Login via JSON oder Basic Auth."""
    email = password = None
    if request.is_json:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
    if not email:
        email, password = _parse_basic_auth()

    user = _check_admin_credentials(email, password)
    if not user:
        return jsonify({"error": "invalid_credentials"}), 401

    return jsonify({
        "ok": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "is_admin": bool(user["is_admin"]),
        }
    })


@bp.get("/info")
@admin_required
def admin_info():
    admin = request.admin_user
    return jsonify({
        "admin": {"email": admin["email"], "id": admin["id"]},
        "status": "ok",
        "tables": db.list_tables()
    })


# ============================================================
# USER MANAGEMENT
# ============================================================

@bp.post("/users/create")
@admin_required
def create_user():
    data = request.get_json(force=True)
    required = ["email", "username", "display_name", "password"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    email = data["email"].strip().lower()
    existing = db.query_one("SELECT id FROM users WHERE email=%s", (email,))
    if existing:
        return jsonify({"error": "email_exists"}), 400

    pw_hash = _hash(data["password"])
    uid = db.insert("users", {
        "username": data["username"],
        "display_name": data["display_name"],
        "email": email,
        "avatar_url": data.get("avatar_url"),
        "is_admin": int(bool(data.get("is_admin", False))),
        "password": pw_hash,
        "created_at": now_ms(),
        "updated_at": now_ms(),
    })
    user = db.query_one("SELECT * FROM users WHERE id=%s", (uid,))
    return jsonify({"ok": True, "user": user}), 201


@bp.get("/users")
@admin_required
def list_users():
    return jsonify({"users": db.get_all("users")})


@bp.get("/users/<int:user_id>")
@admin_required
def get_user(user_id):
    user = db.query_one("SELECT * FROM users WHERE id=%s", (user_id,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404
    return jsonify(user)


@bp.post("/users/<int:user_id>/update")
@admin_required
def update_user(user_id):
    data = request.get_json(force=True)
    data["updated_at"] = now_ms()
    db.update("users", data, "id=%s", (user_id,))
    return jsonify({"ok": True, "user_id": user_id, "updated_fields": list(data.keys())})


@bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    user = db.query_one("SELECT * FROM users WHERE id=%s", (user_id,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404
    if user.get("is_admin"):
        return jsonify({"error": "cannot_delete_admin"}), 403
    db.delete("users", "id=%s", (user_id,))
    return jsonify({"ok": True, "deleted_user_id": user_id})


@bp.post("/users/<int:user_id>/promote")
@admin_required
def promote_user(user_id):
    db.update("users", {"is_admin": 1, "updated_at": now_ms()}, "id=%s", (user_id,))
    return jsonify({"ok": True, "message": f"User {user_id} promoted to admin."})


@bp.post("/users/<int:user_id>/demote")
@admin_required
def demote_user(user_id):
    db.update("users", {"is_admin": 0, "updated_at": now_ms()}, "id=%s", (user_id,))
    return jsonify({"ok": True, "message": f"User {user_id} demoted."})


# ============================================================
# CHALLENGES MANAGEMENT
# ============================================================

@bp.get("/challenges")
@admin_required
def list_challenges():
    return jsonify({"challenges": db.get_all("challenges")})


@bp.get("/challenges/<int:cid>")
@admin_required
def challenge_details(cid):
    ch = db.query_one("SELECT * FROM challenges WHERE id=%s", (cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404
    members = db.query("SELECT * FROM challenge_members WHERE challenge_id=%s", (cid,))
    stats = db.query("SELECT * FROM challenge_stats WHERE challenge_id=%s", (cid,))
    chat = db.query("SELECT * FROM challenge_chat WHERE challenge_id=%s", (cid,))
    return jsonify({
        "challenge": ch,
        "members": members,
        "stats": stats,
        "chat": chat
    })


@bp.delete("/challenges/<int:cid>")
@admin_required
def delete_challenge(cid):
    db.delete("challenges", "id=%s", (cid,))
    return jsonify({"ok": True, "deleted_challenge_id": cid})


@bp.post("/challenges/<int:cid>/add_member")
@admin_required
def add_member_to_challenge(cid):
    data = request.get_json(force=True)
    uid = data.get("user_id")
    if not uid:
        return jsonify({"error": "missing_user_id"}), 400

    challenge = db.query_one("SELECT * FROM challenges WHERE id=%s", (cid,))
    if not challenge:
        return jsonify({"error": "challenge_not_found"}), 404

    user = db.query_one("SELECT * FROM users WHERE id=%s", (uid,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    exists = db.query_one(
        "SELECT 1 FROM challenge_members WHERE challenge_id=%s AND user_id=%s LIMIT 1",
        (cid, uid)
    )
    if exists:
        return jsonify({"error": "already_member"}), 400

    now = now_ms()
    db.insert("challenge_members", {"challenge_id": cid, "user_id": uid, "joined_at": now})
    db.insert("challenge_stats", {
        "challenge_id": cid, "user_id": uid,
        "conf_count": 0, "fail_count": 0,
        "streak": 0, "neg_streak": 0, "blocked": "run",
        "last_computed": None, "created_at": now, "updated_at": now
    })
    return jsonify({
        "ok": True,
        "message": f"User {uid} wurde zu Challenge {cid} hinzugefügt.",
        "challenge_id": cid,
        "user_id": uid
    }), 201


@bp.delete("/challenges/<int:cid>/remove_member/<int:uid>")
@admin_required
def remove_member_from_challenge(cid, uid):
    challenge = db.query_one("SELECT * FROM challenges WHERE id=%s", (cid,))
    if not challenge:
        return jsonify({"error": "challenge_not_found"}), 404

    user = db.query_one("SELECT * FROM users WHERE id=%s", (uid,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    member = db.query_one(
        "SELECT * FROM challenge_members WHERE challenge_id=%s AND user_id=%s",
        (cid, uid)
    )
    if not member:
        return jsonify({"error": "not_member"}), 400

    db.delete("challenge_members", "challenge_id=%s AND user_id=%s", (cid, uid))
    db.delete("challenge_stats", "challenge_id=%s AND user_id=%s", (cid, uid))
    db.delete("challenge_logs", "challenge_id=%s AND user_id=%s", (cid, uid))
    return jsonify({
        "ok": True,
        "message": f"User {uid} wurde aus Challenge {cid} entfernt.",
        "challenge_id": cid,
        "user_id": uid
    })


# ============================================================
# FEED MANAGEMENT
# ============================================================

@bp.get("/feed/posts")
@admin_required
def list_posts():
    posts = db.query("""
        SELECT 
            p.id, p.user_id, u.display_name, p.content, p.image_url,
            p.created_at, p.updated_at,
            COALESCE(lc.like_count, 0) AS like_count,
            COALESCE(cc.comment_count, 0) AS comment_count
        FROM feed_posts p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS like_count
            FROM feed_likes GROUP BY post_id
        ) lc ON lc.post_id = p.id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS comment_count
            FROM feed_comments GROUP BY post_id
        ) cc ON cc.post_id = p.id
        ORDER BY p.created_at DESC
    """)
    return jsonify({"posts": posts})


@bp.get("/feed/comments")
@admin_required
def list_comments():
    return jsonify({"comments": db.get_all("feed_comments")})


@bp.delete("/feed/posts/<int:pid>")
@admin_required
def delete_post(pid):
    db.delete("feed_posts", "id=%s", (pid,))
    return jsonify({"ok": True, "deleted_post_id": pid})


@bp.delete("/feed/comments/<int:cid>")
@admin_required
def delete_comment(cid):
    db.delete("feed_comments", "id=%s", (cid,))
    return jsonify({"ok": True, "deleted_comment_id": cid})


# ============================================================
# FEED ADS MANAGEMENT
# ============================================================

@bp.get("/ads")
@admin_required
def list_ads():
    ads = db.query("""
        SELECT id, image_url, click_url, headline, body, cta_label, status,
               start_at, end_at, weight, audience_filter, impressions, clicks,
               created_at, updated_at
        FROM feed_ads
        ORDER BY created_at DESC
    """)
    return jsonify({"ads": ads})


@bp.post("/ads")
@admin_required
def create_ad():
    payload = request.get_json(force=True) or {}
    image_url = (payload.get("image_url") or "").strip()
    if not image_url:
        return jsonify({"error": "image_url_required"}), 400

    now = now_ms()
    aid = db.insert("feed_ads", {
        "image_url": image_url,
        "click_url": (payload.get("click_url") or "").strip() or None,
        "headline": (payload.get("headline") or "").strip() or None,
        "body": (payload.get("body") or "").strip() or None,
        "cta_label": (payload.get("cta_label") or "").strip() or None,
        "status": (payload.get("status") or "draft").strip().lower(),
        "start_at": payload.get("start_at"),
        "end_at": payload.get("end_at"),
        "weight": payload.get("weight") or 1,
        "audience_filter": payload.get("audience_filter"),
        "created_at": now,
        "updated_at": now,
    })
    return jsonify({"ok": True, "ad_id": aid}), 201


@bp.patch("/ads/<int:aid>")
@admin_required
def update_ad(aid: int):
    payload = request.get_json(force=True) or {}
    allowed = {"image_url", "click_url", "headline", "body", "cta_label",
               "status", "start_at", "end_at", "weight", "audience_filter"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no_fields"}), 400
    updates["updated_at"] = now_ms()
    db.update("feed_ads", updates, "id=%s", (aid,))
    return jsonify({"ok": True, "ad_id": aid})


@bp.post("/ads/<int:aid>/activate")
@admin_required
def activate_ad(aid: int):
    db.update("feed_ads", {"status": "active", "updated_at": now_ms()}, "id=%s", (aid,))
    return jsonify({"ok": True, "ad_id": aid, "status": "active"})


@bp.post("/ads/<int:aid>/pause")
@admin_required
def pause_ad(aid: int):
    db.update("feed_ads", {"status": "paused", "updated_at": now_ms()}, "id=%s", (aid,))
    return jsonify({"ok": True, "ad_id": aid, "status": "paused"})


@bp.post("/ads/upload")
@admin_required
def upload_ad_image():
    """
    Simple Ad-Bild-Upload. Speichert Bild lokal und gibt URL zurück.
    Frontend kann das Bild dann in create_ad verwenden.
    """
    import os
    from werkzeug.utils import secure_filename
    
    if "file" not in request.files:
        return jsonify({"error": "no_file"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty_filename"}), 400
    
    # Erlaubte Extensions
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"}
    ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        return jsonify({"error": "invalid_extension", "allowed": list(allowed_extensions)}), 400
    
    # Sicherer Dateiname
    filename = secure_filename(file.filename)
    timestamp = now_ms()
    unique_name = f"ad_{timestamp}_{filename}"
    
    # Upload-Verzeichnis
    upload_dir = os.path.join(os.getcwd(), "static", "ads")
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)
    
    # URL für Frontend
    image_url = f"/static/ads/{unique_name}"
    
    return jsonify({
        "ok": True,
        "image_url": image_url,
        "filename": unique_name
    }), 201


# ============================================================
# REPORT MANAGEMENT
# ============================================================

@bp.get("/reports")
@admin_required
def list_reports():
    reports = db.query("""
        SELECT
            r.id, r.from_user_id, fu.display_name AS from_user_name,
            r.user_id, uu.display_name AS reported_user_name,
            r.challenge_id, c.title AS challenge_title,
            r.message_id, r.comment_id, r.post_id,
            r.reason, r.created_at
        FROM reports r
        LEFT JOIN users fu ON fu.id = r.from_user_id
        LEFT JOIN users uu ON uu.id = r.user_id
        LEFT JOIN challenges c ON c.id = r.challenge_id
        ORDER BY r.created_at DESC
    """)
    return jsonify({"reports": reports})


@bp.get("/reports/<int:rid>")
@admin_required
def get_report(rid: int):
    r = db.query_one("""
        SELECT r.*, fu.display_name AS reporter_name
        FROM reports r
        LEFT JOIN users fu ON fu.id = r.from_user_id
        WHERE r.id = %s
    """, (rid,))
    if not r:
        return jsonify({"error": "not_found"}), 404

    detail = None
    target_type = None

    if r.get("user_id"):
        target_type = "user"
        detail = db.query_one("SELECT id, display_name, email, avatar_url, created_at FROM users WHERE id=%s", (r["user_id"],))
    elif r.get("challenge_id"):
        target_type = "challenge"
        detail = db.query_one("SELECT id, title, description, creator_id FROM challenges WHERE id=%s", (r["challenge_id"],))
    elif r.get("comment_id"):
        target_type = "comment"
        detail = db.query_one("SELECT id, user_id, content, created_at, post_id FROM feed_comments WHERE id=%s", (r["comment_id"],))
    elif r.get("message_id"):
        target_type = "message"
        detail = db.query_one("SELECT id, sender_id, receiver_id, message, created_at FROM messages WHERE id=%s", (r["message_id"],))
    elif r.get("post_id"):
        target_type = "post"
        detail = db.query_one("SELECT id, user_id, content, image_url, created_at FROM feed_posts WHERE id=%s", (r["post_id"],))

    if not detail:
        r["target_type"] = "unknown"
        r["note"] = "⚠️ Kein Zielobjekt gefunden oder gelöscht."
    else:
        r["target_type"] = target_type
        r["target_detail"] = detail

    return jsonify(r)


@bp.delete("/reports/<int:rid>")
@admin_required
def delete_report(rid: int):
    db.delete("reports", "id=%s", (rid,))
    return jsonify({"ok": True, "deleted_report_id": rid})


@bp.delete("/reports/clear")
@admin_required
def clear_reports():
    db.query("DELETE FROM reports")
    return jsonify({"ok": True, "message": "All reports deleted."})


# ============================================================
# CHALLENGE STATS MANAGEMENT (add this block)
# ============================================================

@bp.get("/challenges/<int:cid>/stats")
@admin_required
def admin_get_challenge_stats(cid: int):
    """Alle Stats einer Challenge inkl. Userinfos."""
    rows = db.query("""
        SELECT 
            s.challenge_id,
            s.user_id,
            u.display_name,
            u.avatar_url,
            s.conf_count,
            s.fail_count,
            s.streak,
            s.neg_streak,
            s.blocked,
            s.today_done,
            s.today_pending,
            s.created_at,
            s.updated_at
        FROM challenge_stats s
        JOIN users u ON u.id = s.user_id
        WHERE s.challenge_id = %s
        ORDER BY u.display_name
    """, (cid,))
    return jsonify({"challenge_id": cid, "stats": rows})


@bp.get("/challenges/<int:cid>/stats/<int:uid>")
@admin_required
def admin_get_challenge_stat(cid: int, uid: int):
    """Einzelne Stats eines Users in einer Challenge."""
    row = db.query_one("""
        SELECT 
            s.challenge_id,
            s.user_id,
            u.display_name,
            u.avatar_url,
            s.conf_count,
            s.fail_count,
            s.streak,
            s.neg_streak,
            s.blocked,
            s.today_done,
            s.today_pending,
            s.created_at,
            s.updated_at
        FROM challenge_stats s
        JOIN users u ON u.id = s.user_id
        WHERE s.challenge_id = %s AND s.user_id = %s
    """, (cid, uid))
    if not row:
        return jsonify({"error": "not_found"}), 404
    return jsonify(row)


@bp.post("/challenges/<int:cid>/stats/<int:uid>/update")
@admin_required
def admin_update_challenge_stat(cid: int, uid: int):
    """
    Aendert einzelne Statistikfelder.
    Achtung: today_done / today_pending sind BIGINT -> 0/1 setzen, keine TRUE/FALSE.
    """
    data = request.get_json(force=True) or {}

    allowed = [
        "conf_count", "fail_count", "streak",
        "neg_streak", "blocked",
        "today_done", "today_pending"
    ]

    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no_valid_fields", "allowed": allowed}), 400

    # Normiere boolean-artige Felder auf 0/1 (int), weil Spalten BIGINT sind
    for k in ("today_done", "today_pending"):
        if k in updates:
            v = updates[k]
            # akzeptiere True/False, "true"/"false", 1/0
            if isinstance(v, str):
                v = v.strip().lower() in ("1", "true", "yes", "y")
            updates[k] = 1 if bool(v) else 0

    updates["updated_at"] = now_ms()

    exists = db.query_one("""
        SELECT id FROM challenge_stats
        WHERE challenge_id=%s AND user_id=%s
    """, (cid, uid))
    if not exists:
        return jsonify({"error": "not_found"}), 404

    db.update("challenge_stats", updates, "challenge_id=%s AND user_id=%s", (cid, uid))

    updated = db.query_one("""
        SELECT 
            s.challenge_id,
            s.user_id,
            u.display_name,
            u.avatar_url,
            s.conf_count,
            s.fail_count,
            s.streak,
            s.neg_streak,
            s.blocked,
            s.today_done,
            s.today_pending,
            s.updated_at
        FROM challenge_stats s
        JOIN users u ON u.id = s.user_id
        WHERE s.challenge_id=%s AND s.user_id=%s
    """, (cid, uid))

    return jsonify({"ok": True, "updated": updated})