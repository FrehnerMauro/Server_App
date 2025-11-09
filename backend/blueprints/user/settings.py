from flask import Blueprint, jsonify, request
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms
import hashlib, base64

bp = Blueprint("settings", __name__, url_prefix="/settings")
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

# ============================================================
# Hilfsfunktionen
# ============================================================

def _hash(s: str) -> str:
    """SHA256-Hash eines Passworts."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _strip_user(user: dict) -> dict:
    """Entfernt sicherheitsrelevante Felder."""
    if not user:
        return user
    u = dict(user)
    u.pop("password", None)
    return u


# ============================================================
# 🧑‍💻 Benutzerverwaltung
# ============================================================

@bp.patch("/me")
@auth_required
def update_user_settings():
    """
    PATCH /settings/me
    - Name ändern
    - Passwort ändern
    """
    uid = request.uid
    data = request.get_json(force=True) or {}
    updates = {}

    print(f"[DEBUG] PATCH /settings/me – Daten empfangen: {data}")

    if "display_name" in data:
        updates["display_name"] = data["display_name"].strip()

    if "password" in data:
        pw = data["password"].strip()
        if len(pw) < 6:
            return jsonify({"error": "password_too_short"}), 400
        updates["password"] = _hash(pw)

    if updates:
        updates["updated_at"] = now_ms()
        db.update("users", updates, "id=%s", (uid,))
        user = db.query_one("SELECT * FROM users WHERE id=%s", (uid,))
        print(f"[DEBUG] Benutzer {uid} erfolgreich aktualisiert.")
        return jsonify({"ok": True, "user": _strip_user(user)})

    return jsonify({"error": "no_changes"}), 400


# ============================================================
# 📸 Avatar hochladen / löschen
# ============================================================

@bp.post("/me/avatar")
@auth_required
def upload_avatar():
    if "file" not in request.files:
        return jsonify({"error": "no_file"}), 400

    f = request.files["file"]
    mime = (f.mimetype or "").lower()
    if not mime.startswith("image/"):
        return jsonify({"error": "invalid_type"}), 400

    data = f.read()
    if len(data) > 5 * 1024 * 1024:
        return jsonify({"error": "too_large"}), 400

    b64 = base64.b64encode(data).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    db.update("users", {"avatar_url": data_url, "updated_at": now_ms()}, "id=%s", (request.uid,))
    user = db.query_one("SELECT * FROM users WHERE id=%s", (request.uid,))
    print(f"[DEBUG] Avatar für User {request.uid} erfolgreich aktualisiert.")
    return jsonify({"ok": True, "user": _strip_user(user)})


@bp.delete("/me/avatar")
@auth_required
def delete_avatar():
    db.update("users", {"avatar_url": None, "updated_at": now_ms()}, "id=%s", (request.uid,))
    user = db.query_one("SELECT * FROM users WHERE id=%s", (request.uid,))
    print(f"[DEBUG] Avatar für User {request.uid} gelöscht.")
    return jsonify({"ok": True, "user": _strip_user(user)})


# ============================================================
# 🔑 Abmelden & Profil löschen
# ============================================================

@bp.post("/logout")
@auth_required
def logout():
    """Löscht aktuelles Token."""
    db.delete("auth_tokens", "user_id=%s", (request.uid,))
    print(f"[DEBUG] Token von User {request.uid} gelöscht.")
    return jsonify({"ok": True})


@bp.delete("/me")
@auth_required
def delete_profile():
    """Löscht Benutzer + abhängige Daten."""
    uid = request.uid
    print(f"[DEBUG] Lösche Profil und zugehörige Daten von User {uid}...")
    db.delete("auth_tokens", "user_id=%s", (uid,))
    db.delete("feed_likes", "user_id=%s", (uid,))
    db.delete("feed_comments", "user_id=%s", (uid,))
    db.delete("feed_posts", "user_id=%s", (uid,))
    db.delete("user_friends", "user_id=%s OR friend_id=%s", (uid, uid))
    db.delete("users", "id=%s", (uid,))
    print(f"[DEBUG] Benutzer {uid} vollständig gelöscht.")
    return jsonify({"ok": True, "deleted_user": uid})


# ============================================================
# 🚫 Freunde blockieren / entblocken
# ============================================================

@bp.get("/blocked")
@auth_required
def list_blocked_users():
    rows = db.query("""
        SELECT b.blocked_user_id AS user_id, u.display_name, u.avatar_url
        FROM user_blocks b
        JOIN users u ON u.id = b.blocked_user_id
        WHERE b.user_id = %s
    """, (request.uid,))
    return jsonify(rows)


@bp.post("/block/<int:blocked_id>")
@auth_required
def block_user(blocked_id):
    if blocked_id == request.uid:
        return jsonify({"error": "cannot_block_self"}), 400
    db.insert("user_blocks", {
        "user_id": request.uid,
        "blocked_user_id": blocked_id,
        "created_at": now_ms()
    })
    print(f"[DEBUG] User {request.uid} blockiert {blocked_id}")
    return jsonify({"ok": True, "blocked": blocked_id})


@bp.delete("/block/<int:blocked_id>")
@auth_required
def unblock_user(blocked_id):
    db.delete("user_blocks", "user_id=%s AND blocked_user_id=%s", (request.uid, blocked_id))
    print(f"[DEBUG] User {request.uid} entblockiert {blocked_id}")
    return jsonify({"ok": True, "unblocked": blocked_id})


# ============================================================
# 🔔 Benachrichtigungen (Dummy)
# ============================================================

@bp.get("/notifications")
@auth_required
def dummy_notifications():
    return jsonify({
        "push_enabled": True,
        "challenge_reminders": True,
        "email_notifications": False
    })


# ============================================================
# 🔒 Datenschutz (Dummy)
# ============================================================

@bp.get("/privacy")
def dummy_privacy():
    return jsonify({
        "privacy_policy": "https://socialhabit.org/privacy.html",
        "is_private": False,
        "default_visibility": "freunde"
    })


# ============================================================
# 📄 AGB (Dummy)
# ============================================================

@bp.get("/terms")
def dummy_terms():
    return jsonify({
        "terms_url": "https://socialhabit.org/terms",
        "version": "1.0.0",
        "last_updated": "2025-10-29"
    })