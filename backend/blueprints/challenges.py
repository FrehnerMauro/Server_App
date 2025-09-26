from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.common.auth import auth_required
from backend.common.store import state, save, now_ms, next_id
from backend.common.utils import day_window_ms_for_local_date
from backend.models.schemas import CreateChallengeBody, ChatBody, ConfirmBody, ChallengeInviteBody
from backend.services.store_confirm import add_challenge_confirm
from backend.services.stats import update_stats_for_challenge_today

bp = Blueprint("challenges", __name__)

# -------- List --------

@bp.get("/challenges")
@auth_required
def list_challenges():
    st = state()
    with_today = (request.args.get("withToday") or "").lower() == "true"
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    res = []
    for ch in st["challenges"].values():
        item = dict(ch)
        if with_today:
            logs = st.get("challenge_logs", {}).get(str(ch["id"]), [])
            status = "done" if logs else "open"
            item["today"] = {"status": status, "pending": status == "open"}
        res.append(item)
    return jsonify(res)

@bp.post("/challenges")
@auth_required
def create_challenge():
    try:
        body = CreateChallengeBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    st = state()
    cid = next_id(st, "challenge_id")
    ch = {
        "id": cid,
        "name": body.name,
        "beschreibung": body.beschreibung,
        "ownerId": request.uid,
        "faelligeWochentage": body.faelligeWochentage,
        "hinzugefuegtAt": now_ms()
    }
    st["challenges"][str(cid)] = ch
    st.setdefault("challenge_members", []).append({"challengeId": cid, "userId": request.uid})
    st.setdefault("challenge_logs", {})[str(cid)] = []
    st.setdefault("challenge_chat", {})[str(cid)] = []
    save()
    return jsonify({"id": cid}), 201

# -------- Detail / Members / Activity --------

@bp.get("/challenges/<int:cid>")
@auth_required
def challenge_detail(cid: int):
    ch = state()["challenges"].get(str(cid))
    if not ch:
        return jsonify({"error": "not_found"}), 404
    return jsonify(ch)

@bp.get("/challenges/<int:cid>/members")
def bad_route():
    # absichtlich: damit Tippfehler schnell auffaellt
    return jsonify({"error": "typo"}), 404

@bp.get("/challenges/<int:cid>/members")
@auth_required
def challenge_members(cid: int):
    st = state()
    mems = [m for m in st["challenge_members"] if m["challengeId"] == cid]
    users = st["users"]
    res = []
    for m in mems:
        u = users.get(str(m["userId"]))
        if u:
            res.append({
                "id": u["id"], "vorname": u.get("vorname"), "name": u["name"], "avatar": u.get("avatar")
            })
    return jsonify(res)

@bp.get("/challenges/<int:cid>/activity")
@auth_required
def challenge_activity(cid: int):
    st = state()
    logs = st.get("challenge_logs", {}).get(str(cid), [])
    res = []
    for l in logs:
        res.append({
            "id": l["id"],
            "action": l["action"],
            "evidence": l.get("evidence"),
            "timestamp": l.get("timestamp")
        })
    return jsonify(res)

# -------- Chat --------

@bp.post("/challenges/<int:cid>/chat")
@auth_required
def post_chat(cid: int):
    try:
        body = ChatBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400
    st = state()
    if str(cid) not in st["challenge_chat"]:
        st["challenge_chat"][str(cid)] = []
    msg = {
        "id": next_id(st, "chat_msg_id"),
        "userId": request.uid,
        "text": body.text,
        "createdAt": now_ms()
    }
    st["challenge_chat"][str(cid)].append(msg)
    save()
    return jsonify(msg), 201

@bp.get("/challenges/<int:cid>/chat")
@auth_required
def list_chat(cid: int):
    st = state()
    return jsonify(st.get("challenge_chat", {}).get(str(cid), []))

# -------- Confirm --------

@bp.post("/challenges/<int:cid>/confirm")
@auth_required
def challenge_confirm(cid: int):
    st = state()
    uid = request.uid
    ch = st["challenges"].get(str(cid))
    if not ch:
        return jsonify({"error": "not_found"}), 404

    if not any(m for m in st["challenge_members"] if m["challengeId"] == cid and m["userId"] == uid):
        return jsonify({"error": "forbidden"}), 403

    try:
        body = ConfirmBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    # optionale Konsistenzpruefung
    if body.user_id is not None and body.user_id != uid:
        return jsonify({"error": "bad_request", "details": "user_id mismatch"}), 400
    if body.challenge_id is not None and body.challenge_id != cid:
        return jsonify({"error": "bad_request", "details": "challenge_id mismatch"}), 400

    # Timestamp bestimmen
    ts = body.timestamp
    if ts is None:
        ymd = request.args.get("date")
        tz = int(request.args.get("tzOffsetMinutes", "0"))
        if ymd:
            try:
                y, m, d = map(int, ymd.split("-"))
            except Exception:
                return jsonify({"error": "bad_request", "details": "date must be YYYY-MM-DD"}), 400
            _, end_ms = day_window_ms_for_local_date(tz, y, m, d)
            ts = end_ms - 1
        else:
            ts = now_ms()

    # Log/Confirm anlegen -> inkl. Feed-Eintrag (das macht add_challenge_confirm)
    confirm = add_challenge_confirm(
        challenge_id=cid,
        user_id=uid,
        image_url=body.imageUrl,
        caption=body.caption,
        visibility=body.visibility or "freunde"
    )
    confirm["timestamp"] = int(ts)
    for c in st["challenge_logs"].get(str(cid), []):
        if c["id"] == confirm["id"]:
            c["timestamp"] = int(ts)
            break

    save()

    tz = int(request.args.get("tzOffsetMinutes", "0"))
    update_stats_for_challenge_today(cid, tz)
    return jsonify({"ok": True, "confirm": confirm}), 201

# -------- Invites --------

@bp.get("/challenges/invites")
@auth_required
def list_invites():
    direction = (request.args.get("direction") or "").lower()
    st = state()
    uid = request.uid
    inv = st["challenge_invites"]
    if direction == "incoming":
        data = [i for i in inv if i["toUserId"] == uid and i["status"] == "pending"]
    elif direction == "outgoing":
        data = [i for i in inv if i["fromUserId"] == uid and i["status"] == "pending"]
    else:
        data = inv
    return jsonify(data)

@bp.post("/challenges/<int:cid>/invites")
@auth_required
def send_invite(cid: int):
    try:
        body = ChallengeInviteBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    st = state()
    iid = next_id(st, "challenge_invite_id")
    inv = {
        "id": iid,
        "challengeId": cid,
        "fromUserId": request.uid,
        "toUserId": body.toUserId,
        "message": body.message,
        "status": "pending",
        "createdAt": now_ms()
    }
    st["challenge_invites"].append(inv)
    save()
    return jsonify(inv), 201

@bp.post("/challenges/invites/<int:rid>/accept")
@auth_required
def accept_invite(rid: int):
    st = state()
    inv = next((i for i in st["challenge_invites"] if i["id"] == rid), None)
    if not inv:
        return jsonify({"error": "not_found"}), 404
    inv["status"] = "accepted"
    st["challenge_members"].append({"challengeId": inv["challengeId"], "userId": inv["toUserId"]})
    save()
    return jsonify({"ok": True})

@bp.post("/challenges/invites/<int:rid>/decline")
@auth_required
def decline_invite(rid: int):
    st = state()
    inv = next((i for i in st["challenge_invites"] if i["id"] == rid), None)
    if not inv:
        return jsonify({"error": "not_found"}), 404
    inv["status"] = "declined"
    save()
    return jsonify({"ok": True})

# -------- Leave --------

@bp.post("/challenges/<int:cid>/leave")
@auth_required
def leave_challenge(cid: int):
    st = state()
    uid = request.uid
    st["challenge_members"] = [
        m for m in st["challenge_members"]
        if not (m["challengeId"] == cid and m["userId"] == uid)
    ]
    save()
    return jsonify({"ok": True})

# -------- Stats / Blocked / Today-Status / Fail-Logs --------

@bp.get("/challenges/<int:cid>/stats")
@auth_required
def challenge_stats(cid: int):
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    st = state()
    today = st.get("challenge_stats", {}).get(str(cid), {}).get("today", {"status": "open", "pending": True})
    resp = {
        "challengeId": cid,
        "today": today,
        "totals": {"confirms": len(st.get("challenge_logs", {}).get(str(cid), []))}
    }
    return jsonify(resp)

@bp.post("/challenges/<int:cid>/stats/recalc")
@auth_required
def challenge_stats_recalc(cid: int):
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    update_stats_for_challenge_today(cid, tz)
    return jsonify({"ok": True})

@bp.get("/challenges/<int:cid>/blocked")
@auth_required
def challenge_blocked(cid: int):
    st = state()
    return jsonify({"challengeId": cid, "blocked": st.get("blocked", {}).get(str(cid), [])})

@bp.get("/challenges/<int:cid>/today-status")
@auth_required
def challenge_today_status(cid: int):
    st = state()
    today = st.get("challenge_stats", {}).get(str(cid), {}).get("today", {"status": "open", "pending": True})
    return jsonify({"challengeId": cid, "today": today})

@bp.get("/challenges/<int:cid>/logs/fails")
@auth_required
def challenge_fail_logs(cid: int):
    return jsonify({"challengeId": cid, "fails": []})