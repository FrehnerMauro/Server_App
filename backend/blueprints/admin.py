from flask import Blueprint, request, jsonify
import base64, hashlib
from functools import wraps
from backend.common.store import Database, now_ms

bp = Blueprint("admin", __name__, url_prefix="/admin")
db = Database("state.db")

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
    user = db.query_one("SELECT * FROM users WHERE email=? LIMIT 1", (email,))
    if not user:
        return None
    if user.get("password") != _hash(password):
        return None
    if not user.get("is_admin"):
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
    """Erstellt einen neuen Benutzer (auch Admin möglich)."""
    data = request.get_json(force=True)

    required = ["email", "username", "display_name", "password"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    email = data["email"].strip().lower()
    existing = db.query_one("SELECT id FROM users WHERE email=?", (email,))
    if existing:
        return jsonify({"error": "email_exists"}), 400

    # Passwort-Hash erzeugen
    pw_hash = hashlib.sha256(data["password"].encode("utf-8")).hexdigest()

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

    user = db.query_one("SELECT * FROM users WHERE id=?", (uid,))
    return jsonify({"ok": True, "user": user}), 201


@bp.get("/users")
@admin_required
def list_users():
    users = db.get_all("users")
    return jsonify({"users": users})


@bp.get("/users/<int:user_id>")
@admin_required
def get_user(user_id):
    user = db.query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404
    return jsonify(user)


@bp.post("/users/<int:user_id>/update")
@admin_required
def update_user(user_id):
    data = request.get_json(force=True)
    data["updated_at"] = now_ms()
    db.update("users", data, "id=?", (user_id,))
    return jsonify({"ok": True, "user_id": user_id, "updated_fields": list(data.keys())})


@bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    user = db.query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404
    if user.get("is_admin"):
        return jsonify({"error": "cannot_delete_admin"}), 403
    db.delete("users", "id=?", (user_id,))
    return jsonify({"ok": True, "deleted_user_id": user_id})


@bp.post("/users/<int:user_id>/promote")
@admin_required
def promote_user(user_id):
    db.update("users", {"is_admin": 1, "updated_at": now_ms()}, "id=?", (user_id,))
    return jsonify({"ok": True, "message": f"User {user_id} promoted to admin."})


@bp.post("/users/<int:user_id>/demote")
@admin_required
def demote_user(user_id):
    db.update("users", {"is_admin": 0, "updated_at": now_ms()}, "id=?", (user_id,))
    return jsonify({"ok": True, "message": f"User {user_id} demoted."})


# ============================================================
# CHALLENGES MANAGEMENT
# ============================================================

@bp.get("/challenges")
@admin_required
def list_challenges():
    data = db.get_all("challenges")
    return jsonify({"challenges": data})


@bp.get("/challenges/<int:cid>")
@admin_required
def challenge_details(cid):
    ch = db.query_one("SELECT * FROM challenges WHERE id=?", (cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404
    members = db.query("SELECT * FROM challenge_members WHERE challenge_id=?", (cid,))
    stats = db.query("SELECT * FROM challenge_stats WHERE challenge_id=?", (cid,))
    chat = db.query("SELECT * FROM challenge_chat WHERE challenge_id=?", (cid,))
    return jsonify({
        "challenge": ch,
        "members": members,
        "stats": stats,
        "chat": chat
    })


@bp.delete("/challenges/<int:cid>")
@admin_required
def delete_challenge(cid):
    db.delete("challenges", "id=?", (cid,))
    return jsonify({"ok": True, "deleted_challenge_id": cid})


# ============================================================
# CHALLENGE MEMBERS MANAGEMENT
# ============================================================

@bp.post("/challenges/<int:cid>/add_member")
@admin_required
def add_member_to_challenge(cid):
    """Fügt einem bestehenden Challenge einen User hinzu."""
    data = request.get_json(force=True)
    uid = data.get("user_id")

    if not uid:
        return jsonify({"error": "missing_user_id"}), 400

    # Challenge prüfen
    challenge = db.query_one("SELECT * FROM challenges WHERE id=?", (cid,))
    if not challenge:
        return jsonify({"error": "challenge_not_found"}), 404

    # User prüfen
    user = db.query_one("SELECT * FROM users WHERE id=?", (uid,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    # Doppelte Mitgliedschaft verhindern
    exists = db.query_one(
        "SELECT 1 FROM challenge_members WHERE challenge_id=? AND user_id=? LIMIT 1",
        (cid, uid)
    )
    if exists:
        return jsonify({"error": "already_member"}), 400

    now = now_ms()

    # Mitglied einfügen
    db.insert("challenge_members", {
        "challenge_id": cid,
        "user_id": uid,
        "joined_at": now
    })

    # Statistik initialisieren
    db.insert("challenge_stats", {
        "challenge_id": cid,
        "user_id": uid,
        "conf_count": 0,
        "fail_count": 0,
        "streak": 0,
        "neg_streak": 0,
        "blocked": "run",
        "last_computed": None,
        "created_at": now,
        "updated_at": now
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
    """Entfernt ein Mitglied vollständig aus einer Challenge (inkl. Stats & Logs)."""

    # Challenge prüfen
    challenge = db.query_one("SELECT * FROM challenges WHERE id=?", (cid,))
    if not challenge:
        return jsonify({"error": "challenge_not_found"}), 404

    # User prüfen
    user = db.query_one("SELECT * FROM users WHERE id=?", (uid,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    # Mitgliedschaft prüfen
    member = db.query_one(
        "SELECT * FROM challenge_members WHERE challenge_id=? AND user_id=?",
        (cid, uid)
    )
    if not member:
        return jsonify({"error": "not_member"}), 400

    # Entfernen (inkl. Stats + Logs)
    db.delete("challenge_members", "challenge_id=? AND user_id=?", (cid, uid))
    db.delete("challenge_stats", "challenge_id=? AND user_id=?", (cid, uid))
    db.delete("challenge_logs", "challenge_id=? AND user_id=?", (cid, uid))

    return jsonify({
        "ok": True,
        "message": f"User {uid} wurde aus Challenge {cid} entfernt.",
        "challenge_id": cid,
        "user_id": uid
    }), 200
    
    
    
# ============================================================
# CHALLENGE CREATION
# ============================================================

@bp.post("/challenges/create")
@admin_required
def create_challenge():
    """Erstellt eine neue Challenge über das Admin-Panel."""
    data = request.get_json(force=True)

    required = ["creator_id", "title", "start_at", "duration_days"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    # Existiert Creator?
    creator = db.query_one("SELECT * FROM users WHERE id=?", (data["creator_id"],))
    if not creator:
        return jsonify({"error": "invalid_creator", "message": "Benutzer-ID existiert nicht"}), 400

    cid = db.insert("challenges", {
        "creator_id": data["creator_id"],
        "title": data["title"].strip(),
        "description": (data.get("description") or "").strip(),
        "start_at": int(data["start_at"]),
        "duration_days": int(data["duration_days"]),
        "allowed_fails": int(data.get("allowed_fails", 0)),
        "due_weekdays": data.get("due_weekdays"),
        "created_at": now_ms(),
        "updated_at": now_ms(),
    })

    challenge = db.query_one("SELECT * FROM challenges WHERE id=?", (cid,))
    return jsonify({"ok": True, "challenge": challenge}), 201
# ============================================================
# FEED MANAGEMENT
# ============================================================

@bp.get("/feed/posts")
@admin_required
def list_posts():
    posts = db.get_all("feed_posts")
    return jsonify({"posts": posts})


@bp.get("/feed/comments")
@admin_required
def list_comments():
    comments = db.get_all("feed_comments")
    return jsonify({"comments": comments})


@bp.get("/feed/reports")
@admin_required
def list_reports():
    reports = db.query("""
        SELECT r.*, 
               u.email AS reporter_email,
               p.email AS profile_email
        FROM feed_reports r
        LEFT JOIN users u ON r.reporter_id = u.id
        LEFT JOIN users p ON r.profile_id = p.id
        ORDER BY r.created_at DESC
    """)
    return jsonify({"reports": reports})


@bp.post("/feed/reports/<int:rid>/status")
@admin_required
def update_report_status(rid):
    data = request.get_json(force=True)
    status = (data.get("status") or "").lower()
    if status not in ("pending", "reviewed", "dismissed"):
        return jsonify({"error": "invalid_status"}), 400
    db.update("feed_reports", {"status": status, "updated_at": now_ms()}, "id=?", (rid,))
    return jsonify({"ok": True, "report_id": rid, "status": status})


@bp.delete("/feed/posts/<int:pid>")
@admin_required
def delete_post(pid):
    db.delete("feed_posts", "id=?", (pid,))
    return jsonify({"ok": True, "deleted_post_id": pid})


@bp.delete("/feed/comments/<int:cid>")
@admin_required
def delete_comment(cid):
    db.delete("feed_comments", "id=?", (cid,))
    return jsonify({"ok": True, "deleted_comment_id": cid})


# ============================================================
# NOTIFICATIONS
# ============================================================

@bp.get("/notifications")
@admin_required
def list_notifications():
    data = db.get_all("notifications")
    return jsonify({"notifications": data})


@bp.delete("/notifications/<int:nid>")
@admin_required
def delete_notification(nid):
    db.delete("notifications", "id=?", (nid,))
    return jsonify({"ok": True, "deleted_notification_id": nid})


# ============================================================
# RAW DATABASE ACCESS
# ============================================================

@bp.post("/query")
@admin_required
def raw_query():
    """Erlaubt Admin, eigene SQL-Statements auszuführen."""
    data = request.get_json(force=True)
    sql = (data.get("sql") or "").strip()
    params = data.get("params") or []
    if not sql:
        return jsonify({"error": "missing_sql"}), 400

    try:
        if sql.lower().startswith("select"):
            res = db.query(sql, tuple(params))
            return jsonify({"ok": True, "rows": res})
        else:
            db.raw(sql, tuple(params))  # Korrektur: db.execute → db.raw (deine DB hat keine execute)
            return jsonify({"ok": True, "message": "query_executed"})
    except Exception as e:
        return jsonify({"error": "query_failed", "details": str(e)}), 400
    
    
    # ============================================================
# CHALLENGE STATS MANAGEMENT
# ============================================================

# ============================================================
# ALLE STATS EINER CHALLENGE
# ============================================================
@bp.get("/challenges/<int:cid>/stats")
@admin_required
def get_challenge_stats(cid: int):
    """Zeigt alle Stats einer Challenge inkl. Userinfos."""
    stats = db.query("""
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
        WHERE s.challenge_id = ?
        ORDER BY u.display_name
    """, (cid,))
    return jsonify({"challenge_id": cid, "stats": stats})


# ============================================================
# EINZELNE STATS EINES USERS
# ============================================================
@bp.get("/challenges/<int:cid>/stats/<int:uid>")
@admin_required
def get_challenge_stat(cid: int, uid: int):
    """Liest die Stats eines einzelnen Users in einer Challenge."""
    stat = db.query_one("""
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
        WHERE s.challenge_id = ? AND s.user_id = ?
    """, (cid, uid))
    if not stat:
        return jsonify({"error": "not_found"}), 404
    return jsonify(stat)


# ============================================================
# UPDATE EINZELNER STATISTIKFELDER
# ============================================================
@bp.post("/challenges/<int:cid>/stats/<int:uid>/update")
@admin_required
def update_challenge_stat(cid: int, uid: int):
    """Ändert einzelne Statistikfelder eines Mitglieds."""
    data = request.get_json(force=True) or {}

    # Zulässige Felder erweitern um die neuen Spalten
    allowed = [
        "conf_count", "fail_count", "streak",
        "neg_streak", "blocked",
        "today_done", "today_pending"
    ]

    # Nur erlaubte Felder übernehmen
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no_valid_fields", "allowed": allowed}), 400

    updates["updated_at"] = now_ms()

    # Prüfen, ob Datensatz existiert
    exists = db.query_one("""
        SELECT id FROM challenge_stats
        WHERE challenge_id=? AND user_id=?
    """, (cid, uid))
    if not exists:
        return jsonify({"error": "not_found"}), 404

    # Update ausführen
    db.update("challenge_stats", updates, "challenge_id=? AND user_id=?", (cid, uid))

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
        WHERE s.challenge_id=? AND s.user_id=?
    """, (cid, uid))

    return jsonify({"ok": True, "updated": updated})