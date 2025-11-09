from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.models.schemas import RegisterBody, LoginBody
from backend.common.store import Database, now_ms
from backend.common.auth import auth_required
import hashlib, base64

bp = Blueprint("auth", __name__)
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

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
        data = request.get_json(force=True) or {}
        print("[register] body:", data)  # Debug-Ausgabe
        
        body = RegisterBody(**data)
    except ValidationError as e:
        print("[register] validation error:", e.errors())
        return jsonify({"error": "validation", "details": e.errors()}), 400

    # Prüfen, ob Email existiert
    user = db.query_one("SELECT * FROM users WHERE LOWER(email)=LOWER(%s) LIMIT 1", (body.email,))
    if user:
        return jsonify({"error": "email_exists"}), 400

    # Sicherstellen, dass Nutzungsbedingungen akzeptiert wurden
    nb_state = getattr(body, "nb_state", None)
    print(f"[register] nb_state={nb_state}")  # Debug-Ausgabe
    if nb_state != "accepted":
        return jsonify({
            "error": "nb_not_accepted",
            "message": "Nutzungsbedingungen müssen akzeptiert werden."
        }), 400

    # Benutzer eintragen
    uid = db.insert("users", {
        "username": f"{body.vorname.lower()}.{body.name.lower()}",
        "display_name": f"{body.vorname} {body.name}",
        "email": body.email,
        "avatar_url": body.avatar,
        "password": _hash(body.password),
        "is_admin": 0,
        "nb_state": nb_state,
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

    # Benutzer abrufen
    user = db.query_one("SELECT * FROM users WHERE id=%s", (uid,))
    return jsonify({"token": token, "user": _strip_user(user)}), 201

# ------------------------------------------------------------
# Login
# ------------------------------------------------------------

@bp.post("/login")
def login():
    """Erlaubt Multi-Device-Login – speichert Device-Token bei jedem Login."""
    print("\n==================== 📥 LOGIN REQUEST ====================")

    try:
        raw_body = request.get_json(force=True) or {}
        print("📨 Request-Body:", raw_body)
        body = LoginBody(**raw_body)
    except Exception as e:
        print("❌ Fehler beim Body-Parsing:", e)
        return jsonify({"error": "invalid_request", "details": str(e)}), 400

    # ------------------------------------------------------------
    # Benutzerprüfung
    # ------------------------------------------------------------
    print(f"🔍 Suche User mit E-Mail: {body.email}")
    user = db.query_one("SELECT * FROM users WHERE LOWER(email)=LOWER(%s) LIMIT 1", (body.email,))
    if not user:
        print("❌ Kein User gefunden")
        return jsonify({"error": "login_failed"}), 401

    if user.get("password") != _hash(body.password):
        print("❌ Passwort falsch für:", body.email)
        return jsonify({"error": "login_failed"}), 401

    print(f"✅ User gefunden: ID={user['id']}, Name={user['display_name'] if 'display_name' in user else '?'}")

    # ------------------------------------------------------------
    # Auth-Token finden oder neu erzeugen
    # ------------------------------------------------------------
    existing = db.query_one(
        "SELECT token FROM auth_tokens WHERE user_id=%s ORDER BY created_at DESC LIMIT 1",
        (user["id"],)
    )

    if existing:
        token = existing["token"]
        print("🔁 Bestehendes Token wiederverwendet:", token)
    else:
        token = f"token-{user['id']}-{now_ms()}"
        db.insert("auth_tokens", {
            "user_id": user["id"],
            "token": token,
            "created_at": now_ms()
        })
        print("🆕 Neues Token erzeugt:", token)

    # ------------------------------------------------------------
    # Device-Token speichern (falls vorhanden)
    # ------------------------------------------------------------
    try:
        device_token = raw_body.get("device_token")
        if not device_token:
            print("⚠️ Kein device_token im Request vorhanden.")
        else:
            print("📱 Empfangenes Device-Token:", device_token)

            exists = db.query_one(
                "SELECT id, user_id FROM user_devices WHERE device_token=%s",
                (device_token,)
            )

            if not exists:
                print("🆕 Neues Device-Token wird gespeichert …")
                db.insert("user_devices", {
                    "user_id": user["id"],
                    "device_token": device_token,
                    "created_at": now_ms()
                })
            else:
                # Wenn das Token schon existiert, aber zu anderem User gehört → aktualisieren
                if exists["user_id"] != user["id"]:
                    print(f"🔄 Device-Token gehörte zu anderem User (user_id={exists['user_id']}), aktualisiere …")
                    db.update(
                        "user_devices",
                        {"user_id": user["id"], "created_at": now_ms()},
                        "device_token=%s",
                        (device_token,)
                    )
                else:
                    print("✅ Device-Token bereits für diesen User gespeichert.")
    except Exception as e:
        print("⚠️ Fehler beim Speichern des Device-Tokens:", e)

    # ------------------------------------------------------------
    # Antwort
    # ------------------------------------------------------------
    print(f"✅ LOGIN ERFOLGREICH → user.id={user['id']} | token={token}")
    print("============================================================\n")

    return jsonify({"token": token, "user": _strip_user(user)})

# ------------------------------------------------------------
# Eigene Profildaten abrufen
# ------------------------------------------------------------

@bp.get("/me")
@auth_required
def me():
    user = db.query_one("SELECT * FROM users WHERE id=%s", (request.uid,))
    if not user:
        return jsonify({"error": "not_found"}), 404
    return jsonify(_strip_user(user))


# ------------------------------------------------------------
# Benutzerprofil aktualisieren
# ------------------------------------------------------------

@bp.patch("/me")
@auth_required
def update_me():
    user = db.query_one("SELECT * FROM users WHERE id=%s", (request.uid,))
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

    if "password" in data:
        pw = data["password"].strip()
        if len(pw) < 4:
            return jsonify({"error": "validation", "field": "password", "message": "too_short"}), 400
        updates["password"] = _hash(pw)

    if updates:
        updates["updated_at"] = now_ms()
        db.update("users", updates, "id=%s", (request.uid,))

    user = db.query_one("SELECT * FROM users WHERE id=%s", (request.uid,))
    return jsonify(_strip_user(user))


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

    db.update("users", {"avatar_url": data_url, "updated_at": now_ms()}, "id=%s", (request.uid,))
    user = db.query_one("SELECT * FROM users WHERE id=%s", (request.uid,))
    return jsonify({"ok": True, "user": _strip_user(user)})


@bp.delete("/me/avatar")
@auth_required
def delete_avatar_me():
    db.update("users", {"avatar_url": None, "updated_at": now_ms()}, "id=%s", (request.uid,))
    user = db.query_one("SELECT * FROM users WHERE id=%s", (request.uid,))
    return jsonify({"ok": True, "user": _strip_user(user)})