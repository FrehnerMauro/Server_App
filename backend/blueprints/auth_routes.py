from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.models.schemas import RegisterBody, LoginBody
from backend.common.store import state, save, next_id
from backend.common.auth import auth_required


bp = Blueprint("auth", __name__)

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
        "avatar": body.avatar
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
    # Demo: passwort wird nicht gehasht/gespeichert; akzeptiere jede Kombi, wenn email existiert
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