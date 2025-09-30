from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.common.auth import auth_required
from backend.common.store import state, save, now_ms, next_id
from backend.common.utils import day_window_ms_for_local_date
from backend.models.schemas import CreateChallengeBody, ChatBody, ConfirmBody, ChallengeInviteBody
from backend.services.store_confirm import add_challenge_confirm
from backend.services.stats import update_stats_for_challenge_today
import datetime
from datetime import datetime, timedelta, timezone
from backend.services.stats import challenge_update_stats  # statt update_stats_for_challenge_today
from collections import defaultdict



bp = Blueprint("challenges", __name__)

# -------- List --------
def _to_local_date_from_ts(ts: int, tz_offset_min: int) -> datetime.date:
    """Akzeptiert Sekunden oder Millisekunden."""
    if ts > 10**12:  # ms -> s
        ts = ts // 1000
    tz = timezone(timedelta(minutes=tz_offset_min))
    return datetime.fromtimestamp(int(ts), tz).date()

def _daterange(d0: datetime.date, d1: datetime.date):
    cur = d0
    while cur <= d1:
        yield cur
        cur = cur + timedelta(days=1)
def _to_local_date(ts_any: int | str, tz_offset_min: int) -> datetime.date:
    """
    Akzeptiert Sekunden oder Millisekunden.
    """
    tz = timezone(timedelta(minutes=tz_offset_min))

    ts = int(ts_any)
    # Wenn Millisekunden: auf Sekunden runterteilen
    # 10**12 ist ~2001-09-09 in ms; alles darueber ist ziemlich sicher ms.
    if ts > 10**12:
        ts = ts // 1000

    return datetime.fromtimestamp(ts, tz).date()

def _daterange(d0: datetime.date, d1: datetime.date):
    cur = d0
    while cur <= d1:
        yield cur
        cur = cur + timedelta(days=1)


@bp.get("/challenges/list")
@auth_required
def list_challenges():
    st = state()
    with_today = (request.args.get("withToday") or "").lower() == "true"
    tz = int(request.args.get("tzOffsetMinutes", "0"))  # falls spaeter nuetzlich
    uid = request.uid

    # alle Challenge-IDs, bei denen der User Mitglied ist
    member_ch_ids = {
        m["challengeId"]
        for m in st.get("challenge_members", [])
        if m.get("userId") == uid
    }

    res = []
    for ch in st.get("challenges", {}).values():
        # nur Challenges behalten, wo User Mitglied ist (oder Owner, wenn du das willst)
        if ch.get("id") not in member_ch_ids and ch.get("ownerId") != uid:
            continue

        item = dict(ch)

        if with_today:
            logs = st.get("challenge_logs", {}).get(str(ch["id"]), [])
            # Minimal: "done", wenn es irgendeinen Log gibt; sonst "open".
            # (Wenn du es pro-User willst: any(l.get("userId")==uid for l in logs))
            status = "done" if any(l.get("userId") == uid for l in logs) else "open"
            item["today"] = {
                "status": status,
                "pending": status == "open"
            }

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
        "startAt": body.startAt or int(datetime.now().timestamp()),   # 👈 hier
        "dauerTage": body.dauerTage,                                 # 👈 hier
        "erlaubteFailsTage": body.erlaubteFailsTage,                 # optional
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
#@auth_required
def challenge_detail(cid: int):
    ch = state()["challenges"].get(str(cid))
    if not ch:
        return jsonify({"error": "not_found"}), 404
    return jsonify(ch)


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
@bp.route("/challenges/<int:cid>/stats/recalc", methods=["POST","GET"])
def challenge_stats_recalc(cid: int):
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    result = challenge_update_stats(cid, tz_offset_minutes=tz)
    return jsonify(result)




@bp.get("/challenges/<int:cid>/stats")
def challenge_stats_users(cid: int):
    tz_offset = int(request.args.get("tzOffsetMinutes", "0"))
    st = state()

    ch = st.get("challenges", {}).get(str(cid)) or {}
    if not ch:
        return jsonify({"error": "not_found"}), 404

    # Challenge-Metadaten (nur zur Info im Response)
    start_at = ch.get("startAt")
    dauer_tage = ch.get("dauerTage") or ch.get("days")
    faellige = ch.get("faelligeWochentage") or []
    erlaubte_fails = ch.get("erlaubteFailsTage")
    steak = ch.get("streak")  # bleibt "steak", wenn dein iOS das so mapped

    # ---- Stats aus dem Speicher lesen ----
    stats_all = st.get("challenge_stats", {}).get(str(cid), {})
    per_user_map = stats_all.get("perUser", {})  # { "1": {...}, "2": {...} }
    today_global = stats_all.get("today") or {"status": "not_pending", "pending": False}

    def map_today_for_user(u: dict) -> dict:
        """Baut dein gewünschtes Today-Objekt pro User:
           status:  'offen' | 'gesperrt' | 'Abgeschlossen'
           pending: Bool
           erledigt: Bool
        """
        blocked = str(u.get("blocked", "none"))
        last_today = str(u.get("lastTodayState", "nicht_pending"))

        if blocked == "completed":
            return {"status": "Abgeschlossen", "pending": False, "erledigt": True}
        if blocked == "gesperrt":
            return {"status": "gesperrt", "pending": False, "erledigt": False}

        # offen
        return {
            "status": "offen",
            "pending": last_today == "pending",
            "erledigt": last_today == "erledigt",
        }

    # Array aus dem dict bauen (praktisch für iOS)
    per_user = []
    for uid_str, u in per_user_map.items():
        try:
            uid = int(uid_str)
        except Exception:
            # Falls Key bereits int ist (sehr selten), fallback:
            uid = int(u.get("userId", 0)) if isinstance(uid_str, dict) else 0

        per_user.append({
            "userId": uid,
            "confCount": int(u.get("conf_count", 0)),
            "failCount": int(u.get("fail_count", 0)),
            "streak": int(u.get("streak", 0)),
            "negStreak": int(u.get("neg_streak", 0)),
            "challenge_status": u.get("blocked", "none"),       # "none" | "gesperrt" | "completed"
            "status": u.get("state", "nicht_pending"),  # Zustand für den nächsten Tag
        })

    # Range grob auffüllen (falls startAt fehlt, lasse es leer)
    tz = timezone(timedelta(minutes=tz_offset))
    today_local = datetime.now(tz).date()
    def _to_local_date_from_ts(ts: int) -> str | None:
        if not ts:
            return None
        if ts > 10**12:  # ms -> s
            ts = ts // 1000
        return datetime.fromtimestamp(int(ts), tz).date().isoformat()

    resp = {
        "challengeId": cid,
        "dauerTage": dauer_tage,
        "faelligeWochentage": faellige,
        "erlaubteFailsTage": erlaubte_fails,
        "perUser": per_user,
    }
    return jsonify(resp)