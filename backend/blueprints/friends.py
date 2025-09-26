from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import state, next_id, now_ms, save
from backend.models.schemas import FriendReqBody
from pydantic import ValidationError

bp = Blueprint("friends", __name__)

@bp.get("/friends")
@auth_required
def list_friends():
    st = state()
    uid = request.uid
    # accepted beidseitig
    accepted = [fr for fr in st["friends"] if (fr["fromUserId"] == uid or fr["toUserId"] == uid)]
    # map to users
    user_ids = set()
    for fr in accepted:
        user_ids.add(fr["fromUserId"])
        user_ids.add(fr["toUserId"])
    user_ids.discard(uid)
    res = [st["users"].get(str(i)) for i in user_ids]
    return jsonify([u for u in res if u])

@bp.get("/friends/requests")
@auth_required
def list_friend_requests():
    direction = (request.args.get("direction") or "").lower()
    st = state()
    uid = request.uid
    reqs = st["friend_requests"]
    if direction == "incoming":
        data = [r for r in reqs if r["toUserId"] == uid and r["status"] == "pending"]
    elif direction == "outgoing":
        data = [r for r in reqs if r["fromUserId"] == uid and r["status"] == "pending"]
    else:
        data = reqs
    return jsonify(data)

@bp.post("/friends/requests")
@auth_required
def send_friend_request():
    try:
        body = FriendReqBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    st = state()
    uid = request.uid
    rid = next_id(st, "friend_req_id")
    req = {
        "id": rid,
        "fromUserId": uid,
        "toUserId": body.toUserId,
        "message": body.message,
        "status": "pending",
        "createdAt": now_ms()
    }
    st["friend_requests"].append(req)
    save()
    return jsonify(req), 201

@bp.post("/friends/requests/<int:rid>/accept")
@auth_required
def accept_friend_request(rid: int):
    st = state()
    req = next((r for r in st["friend_requests"] if r["id"] == rid), None)
    if not req:
        return jsonify({"error": "not_found"}), 404
    req["status"] = "accepted"
    st["friends"].append({
        "id": next_id(st, "friend_id"),
        "fromUserId": req["fromUserId"],
        "toUserId": req["toUserId"],
        "since": now_ms()
    })
    save()
    return jsonify({"ok": True})

@bp.post("/friends/requests/<int:rid>/decline")
@auth_required
def decline_friend_request(rid: int):
    st = state()
    req = next((r for r in st["friend_requests"] if r["id"] == rid), None)
    if not req:
        return jsonify({"error": "not_found"}), 404
    req["status"] = "declined"
    save()
    return jsonify({"ok": True})