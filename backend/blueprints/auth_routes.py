from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.models.schemas import RegisterBody, LoginBody
from backend.common.store import Database, now_ms
from backend.common.auth import auth_required
import hashlib, base64

bp = Blueprint("auth", __name__)
db = Database("state.db")

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def _hash(s: str) -> str:
    """SHA256-Hash eines Passworts (oder leeren Strings)."""
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _strip_user(user: dict) -> dict:
    """Entfernt sicherheitsrelevante Felder aus Userdaten."""
    if not user:
        return user
    u = dict(user)
    u.pop("password", None)
    return u


# ------------------------------------------------------------
# Registrierung
# ------------------------------------------------------------

@bp.post("/register")
def register():
    try:
        body = RegisterBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    # Prüfen, ob Email existiert
    user = db.query_one("SELECT * FROM users WHERE LOWER(email)=LOWER(?) LIMIT 1", (body.email,))
    if user:
        return jsonify({"error": "email_exists"}), 400

    # Benutzer eintragen
    uid = db.insert("users", {
        "username": f"{body.vorname.lower()}.{body.name.lower()}",
        "display_name": f"{body.vorname} {body.name}",
        "email": body.email,
        "avatar_url": body.avatar,
        "password": _hash(body.password),  # Passwort gehasht speichern
        "is_admin": 0,
        "created_at": now_ms(),
        "updated_at": now_ms()
    })

    # Neues Token erzeugen
    token = f"token-{uid}-{now_ms()}"
    db.insert("auth_tokens", {
        "user_id": uid,
        "token": token,
        "created_at": now_ms()
    })

    user = db.find("users", id=uid)
    return jsonify({"token": token, "user": _strip_user(user)}), 201


# ------------------------------------------------------------
# Login
# ------------------------------------------------------------

@bp.post("/login")
def login():
    try:
        body = LoginBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    user = db.query_one("SELECT * FROM users WHERE LOWER(email)=LOWER(?) LIMIT 1", (body.email,))
    if not user:
        return jsonify({"error": "login_failed"}), 401

    # Passwortprüfung (Hash-Vergleich)
    if user.get("password") != _hash(body.password):
        return jsonify({"error": "login_failed"}), 401

    # Alte Tokens löschen
    db.delete("auth_tokens", "user_id=?", (user["id"],))

    # Neues Token erstellen
    token = f"token-{user['id']}-{now_ms()}"
    db.insert("auth_tokens", {
        "user_id": user["id"],
        "token": token,
        "created_at": now_ms()
    })

    return jsonify({"token": token, "user": _strip_user(user)})


# ------------------------------------------------------------
# Eigene Profildaten abrufen
# ------------------------------------------------------------

@bp.get("/me")
@auth_required
def me():
    user = db.find("users", id=request.uid)
    if not user:
        return jsonify({"error": "not_found"}), 404
    return jsonify(_strip_user(user))


# ------------------------------------------------------------
# Benutzerprofil aktualisieren
# ------------------------------------------------------------

@bp.patch("/me")
@auth_required
def update_me():
    user = db.find("users", id=request.uid)
    if not user:
        return jsonify({"error": "not_found"}), 404

    data = request.get_json(silent=True) or {}
    updates = {}

    if "vorname" in data:
        vor = data["vorname"].strip()
        alt_name = (user.get("display_name") or "").split(" ")
        nach = alt_name[-1] if len(alt_name) > 1 else ""
        updates["display_name"] = f"{vor} {nach}"

    if "name" in data:
        nach = data["name"].strip()
        alt_name = (user.get("display_name") or "").split(" ")
        vor = alt_name[0] if alt_name else ""
        updates["display_name"] = f"{vor} {nach}"

    if "avatar" in data:
        a = (data["avatar"] or "").strip()
        if a and not (a.startswith("data:image/") or a.startswith("http")):
            return jsonify({"error": "validation", "field": "avatar", "message": "invalid format"}), 400
        updates["avatar_url"] = a or None

    # Passwort ändern (wenn gewünscht)
    if "password" in data:
        pw = data["password"].strip()
        if len(pw) < 4:
            return jsonify({"error": "validation", "field": "password", "message": "too_short"}), 400
        updates["password"] = _hash(pw)

    if updates:
        updates["updated_at"] = now_ms()
        db.update("users", updates, "id=?", (request.uid,))

    return jsonify(_strip_user(db.find("users", id=request.uid)))


# ------------------------------------------------------------
# Avatar-Upload & Löschen
# ------------------------------------------------------------

@bp.post("/me/avatar")
@auth_required
def upload_avatar_me():
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

    db.update("users", {"avatar_url": data_url, "updated_at": now_ms()}, "id=?", (request.uid,))
    return jsonify({"ok": True, "user": _strip_user(db.find("users", id=request.uid))})


@bp.delete("/me/avatar")
@auth_required
def delete_avatar_me():
    db.update("users", {"avatar_url": None, "updated_at": now_ms()}, "id=?", (request.uid,))
    return jsonify({"ok": True, "user": _strip_user(db.find("users", id=request.uid))})