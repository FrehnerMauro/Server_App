from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.models.schemas import RegisterBody, LoginBody
from backend.common.store import state, save, next_id
from backend.common.auth import auth_required

import base64

bp = Blueprint("auth", __name__)

# ------------------------------
# Registrierung / Login / Me
# ------------------------------

@bp.post("/register")
def register():
    try:
        body = RegisterBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    st = state()
    # email uniq?
    if any(u for u in st["users"].values() if u["email"].lower() == body.email.lower()):
        return jsonify({"error": "email_exists"}), 400

    uid = next_id(st, "user_id")
    user = {
        "id": uid,
        "vorname": body.vorname,
        "name": body.name,
        "email": body.email,
        "avatar": body.avatar  # optional data-url / http-url
    }
    st["users"][str(uid)] = user
    save()

    # token ausgeben
    token = f"token-{uid}"
    st["auth"]["tokens"][token] = uid
    save()
    return jsonify({"token": token, "user": user}), 201


@bp.post("/login")
def login():
    try:
        body = LoginBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    st = state()
    # Demo: Passwort wird nicht validiert; akzeptiere jede Kombi, wenn email existiert
    usr = next((u for u in st["users"].values() if u["email"].lower() == body.email.lower()), None)
    if not usr:
        return jsonify({"error": "login_failed"}), 401

    token = f"token-{usr['id']}"
    st["auth"]["tokens"][token] = usr["id"]
    save()
    return jsonify({"token": token, "user": usr})


@bp.get("/me")
def me():
    @auth_required
    def inner():
        st = state()
        uid = request.uid
        return jsonify(st["users"].get(str(uid)))
    return inner()

# ------------------------------
# Profil-Änderungen (eingeloggter User)
# ------------------------------

@bp.patch("/me")
def update_me():
    """
    JSON-Body (alle Felder optional):
    {
      "vorname": "Mauro",
      "name": "Frehner",
      "avatar": "data:image/png;base64,..." | "https://..."  (optional)
    }
    """
    @auth_required
    def inner():
        st = state()
        uid = str(request.uid)
        user = st["users"].get(uid)
        if not user:
            return jsonify({"error": "not_found"}), 404

        data = request.get_json(silent=True) or {}
        # sanitize & apply
        if "vorname" in data:
            v = (data.get("vorname") or "").strip()
            user["vorname"] = v or None

        if "name" in data:
            n = (data.get("name") or "").strip()
            if not n:
                return jsonify({"error": "validation", "field": "name", "message": "name required"}), 400
            if len(n) > 100:
                return jsonify({"error": "validation", "field": "name", "message": "too long"}), 400
            user["name"] = n

        if "avatar" in data:
            a = (data.get("avatar") or "").strip()
            # Optional: minimale Validierung
            if a and not (a.startswith("data:image/") or a.startswith("http://") or a.startswith("https://")):
                return jsonify({"error": "validation", "field": "avatar", "message": "must be data-url or http(s) url"}), 400
            user["avatar"] = a or None

        st["users"][uid] = user
        save()
        return jsonify(user)

    return inner()


@bp.post("/me/avatar")
def upload_avatar_me():
    """
    Multipart Upload:
      Content-Type: multipart/form-data
      Feld: file (image/*)

    Speichert das Bild als data-url (base64) in user.avatar und gibt den User zurück.
    Größenlimit: 5 MB
    """
    @auth_required
    def inner():
        if "file" not in request.files:
            return jsonify({"error": "no_file"}), 400

        f = request.files["file"]
        mime = (f.mimetype or "").lower()

        if not mime.startswith("image/"):
            return jsonify({"error": "invalid_type", "message": "image/* required"}), 400

        content = f.read()
        max_bytes = 5 * 1024 * 1024  # 5 MB
        if len(content) > max_bytes:
            return jsonify({"error": "too_large", "message": "max 5MB"}), 400

        # data-url bauen
        b64 = base64.b64encode(content).decode("ascii")
        data_url = f"data:{mime};base64,{b64}"

        st = state()
        uid = str(request.uid)
        user = st["users"].get(uid)
        if not user:
            return jsonify({"error": "not_found"}), 404

        user["avatar"] = data_url
        st["users"][uid] = user
        save()
        return jsonify({"ok": True, "user": user})

    return inner()


@bp.delete("/me/avatar")
def delete_avatar_me():
    """
    Löscht den Avatar (setzt user.avatar = None).
    """
    @auth_required
    def inner():
        st = state()
        uid = str(request.uid)
        user = st["users"].get(uid)
        if not user:
            return jsonify({"error": "not_found"}), 404

        user["avatar"] = None
        st["users"][uid] = user
        save()
        return jsonify({"ok": True, "user": user})

    return inner()