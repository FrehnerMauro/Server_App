from __future__ import annotations

from flask import Blueprint, request, jsonify, Response
from pydantic import ValidationError
from datetime import datetime, timedelta, timezone, date
from collections import defaultdict

from backend.common.auth import auth_required
from backend.common.store import state, save, now_ms, next_id
from backend.models.schemas import (
    CreateChallengeBody,
    ChatBody,
    ConfirmBody,
    ChallengeInviteBody,
)
from backend.services.store_confirm import add_challenge_confirm
from backend.services.stats import (
    challenge_update_stats,
    init_challenge_members,
)

bp = Blueprint("challenges", __name__)

# ------------------------------------------------------------
# Kleine Helper
# ------------------------------------------------------------

def _normalize_weekdays(raw_list):
    """
    Normalisiert z. B. ["Mon", "DI", "dienstag"] → [0,1,2,...]
    Montag=0, Sonntag=6
    """
    mapping = {
        "mo": 0, "mon": 0, "montag": 0,
        "di": 1, "tue": 1, "dienstag": 1,
        "mi": 2, "wed": 2, "mittwoch": 2,
        "do": 3, "thu": 3, "donnerstag": 3,
        "fr": 4, "fri": 4, "freitag": 4,
        "sa": 5, "sat": 5, "samstag": 5,
        "so": 6, "sun": 6, "sonntag": 6
    }
    result = []
    for x in raw_list:
        if isinstance(x, int) and 0 <= x <= 6:
            result.append(x)
        elif isinstance(x, str):
            k = x.strip().lower()[:3]
            if k in mapping:
                result.append(mapping[k])
    return sorted(set(result))

def _to_local_date_from_ts(ts: int, tz_offset_min: int) -> date:
    """Akzeptiert Sekunden oder Millisekunden."""
    if ts > 10**12:  # ms -> s
        ts = ts // 1000
    tz = timezone(timedelta(minutes=tz_offset_min))
    return datetime.fromtimestamp(int(ts), tz).date()

def _is_due_day(day: date, start_date: date, end_date: date, faellige: list[int]) -> bool:
    """Prüft, ob ein Tag innerhalb der Laufzeit und laut faelligeWochentage fällig ist."""
    if day < start_date or day > end_date:
        return False
    if not faellige:
        return True
    return day.weekday() in faellige

def _challenge_name(cid: int) -> str:
    ch = state().get("challenges", {}).get(str(cid)) or {}
    name = (ch.get("name") or "").strip()
    return name if name else f"Challenge #{cid}"

def _display_name(uid: int) -> str:
    u = state().get("users", {}).get(str(uid)) or {}
    vor = (u.get("vorname") or "").strip()
    nam = (u.get("name") or "").strip()
    full = " ".join([p for p in [vor, nam] if p])
    return full if full else (nam if nam else f"User {uid}")

def _notify_challenge_members(
    cid: int,
    actor_uid: int,
    text: str,
    kind: str = "info",
) -> None:
    """
    Schreibt eine Notification an ALLE Mitglieder (außer actor_uid).
    Fügt challengeId/challengeName/type hinzu.
    kind: "chat" | "confirm" | "info"
    """
    st = state()
    members = [
        m.get("userId")
        for m in st.get("challenge_members", [])
        if m.get("challengeId") == cid
    ]
    ch_name = _challenge_name(cid)

    for target_uid in members:
        if target_uid == actor_uid:
            continue
        notif = {
            "id": next_id(st, "notification_id"),
            "userId": int(target_uid),
            "text": text,             # z. B. "[Daily Pushups] Max hat heute bestätigt."
            "read": False,
            "createdAt": now_ms(),
            "challengeId": cid,
            "challengeName": ch_name,
            "fromUserId": actor_uid,
            "type": kind,
        }
        st.setdefault("notifications", []).append(notif)

    save()

# ------------------------------------------------------------
# List / Create
# ------------------------------------------------------------

@bp.get("/challenges/list")
@auth_required
def list_challenges():
    st = state()
    with_today = (request.args.get("withToday") or "").lower() == "true"
    tz = int(request.args.get("tzOffsetMinutes", "0"))  # aktuell ungenutzt
    uid = request.uid

    # Nur Challenges, bei denen der User Mitglied ist
    member_ch_ids = {
        m["challengeId"]
        for m in st.get("challenge_members", [])
        if m.get("userId") == uid
    }

    res = []
    for ch in st.get("challenges", {}).values():
        if ch.get("id") not in member_ch_ids:
            continue

        item = dict(ch)

        if with_today:
            logs = st.get("challenge_logs", {}).get(str(ch["id"]), [])
            status = "done" if any(l.get("userId") == uid for l in logs) else "open"
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
        "startAt": body.startAt or int(datetime.now().timestamp()),
        "dauerTage": body.dauerTage,
        "erlaubteFailsTage": body.erlaubteFailsTage,
        "hinzugefuegtAt": now_ms()
    }
    st["challenges"][str(cid)] = ch
    st.setdefault("challenge_members", []).append(
        {"challengeId": cid, "userId": request.uid}
    )
    st.setdefault("challenge_logs", {})[str(cid)] = []
    st.setdefault("challenge_chat", {})[str(cid)] = []

    # Init nur für diese Challenge
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    res = init_challenge_members(cid, tz_offset_minutes=tz)
    if "error" in res:
        return jsonify({"error": "init_failed", "details": res}), 400

    save()
    return jsonify({"id": cid, "initialized": True}), 201

# ------------------------------------------------------------
# Detail / Members / Activity
# ------------------------------------------------------------

@bp.get("/challenges/<int:cid>")
@auth_required
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
                "id": u["id"],
                "vorname": u.get("vorname"),
                "name": u["name"],
                "avatar": u.get("avatar"),
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
            "timestamp": l.get("timestamp"),
            "userId": l.get("userId"),
            "name": l.get("name"),
            "vorname": l.get("vorname"),
            "avatar": l.get("avatar"),
        })
    return jsonify(res)

# ------------------------------------------------------------
# Chat
# ------------------------------------------------------------

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

    # 🔔 Notification an alle Mitglieder (außer Sender)
    sender = _display_name(request.uid)
    ch_name = _challenge_name(cid)
    preview = (body.text or "").strip()
    if len(preview) > 50:
        preview = preview[:50] + "…"
    _notify_challenge_members(
        cid,
        request.uid,
        f"[{ch_name}] {sender} hat im Challenge-Chat geschrieben: {preview}",
        kind="chat",
    )

    return jsonify(msg), 201

@bp.get("/challenges/<int:cid>/chat")
@auth_required
def list_chat(cid: int):
    st = state()
    return jsonify(st.get("challenge_chat", {}).get(str(cid), []))

# ------------------------------------------------------------
# Confirm
# ------------------------------------------------------------

@bp.post("/challenges/<int:cid>/confirm")
@auth_required
def challenge_confirm(cid: int):
    st = state()
    uid = request.uid
    ch = st["challenges"].get(str(cid))
    if not ch:
        return jsonify({"error": "not_found"}), 404

    # Mitgliedschaft
    if not any(m for m in st.get("challenge_members", [])
               if m.get("challengeId") == cid and m.get("userId") == uid):
        return jsonify({"error": "forbidden"}), 403

    # Body
    try:
        body = ConfirmBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    # Zeit + TZ
    ts = body.timestamp or now_ms()
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    tzinfo = timezone(timedelta(minutes=tz))
    local_day = _to_local_date_from_ts(int(ts), tz)
    today_local = datetime.now(tzinfo).date()

    # Challenge-Metadaten für "faellig heute?"
    start_at = ch.get("startAt")
    dauer    = ch.get("dauerTage") or ch.get("days")
    faellige = _normalize_weekdays(ch.get("faelligeWochentage") or [])
    start_date = _to_local_date_from_ts(int(start_at), tz) if start_at else today_local
    end_date = start_date + timedelta(days=int(dauer) - 1) if dauer else today_local
    due_today = _is_due_day(today_local, start_date, end_date, faellige)

    # User-Daten in Log
    user = st.get("users", {}).get(str(uid), {})
    user_info = {
        "userId": uid,
        "name": user.get("name"),
        "vorname": user.get("vorname"),
        "avatar": user.get("avatar"),
    }

    # Confirm / Log
    confirm = add_challenge_confirm(
        challenge_id=cid,
        user_id=uid,
        image_url=body.imageUrl,
        caption=body.caption,
        visibility=body.visibility or "freunde"
    )
    confirm["timestamp"] = int(ts)
    confirm.update(user_info)

    logs = st.setdefault("challenge_logs", {}).setdefault(str(cid), [])
    for i, c in enumerate(logs):
        if c.get("id") == confirm.get("id"):
            logs[i] = {**c, **confirm}
            break
    else:
        logs.append(confirm)

    # Realtime-Stat nur fuer TODAY
    stats_all = st.setdefault("challenge_stats", {}).setdefault(str(cid), {})
    per_user_map = stats_all.setdefault("perUser", {})
    ustat = per_user_map.setdefault(str(uid), {
        "userId": uid,
        "conf_count": 0,
        "fail_count": 0,
        "streak": 0,
        "neg_streak": 0,
        "blocked": "run",
        "state": "pending",
        "lastTodayState": "not_done",
        "lastComputedDate": None
    })

    prev_last = ustat.get("lastTodayState")

    if local_day == today_local:
        if due_today:
            # Heutiger fälliger Tag
            ustat["conf_count"] = int(ustat.get("conf_count", 0)) + 1
            ustat["streak"] = int(ustat.get("streak", 0)) + 1
            ustat["neg_streak"] = 0
            if prev_last == "not_done":
                ustat["fail_count"] = max(0, int(ustat.get("fail_count", 0)) - 1)

            ustat["lastTodayState"] = "done"
            ustat["state"] = "pending"
            ustat["today"] = {
                "blocked": ustat.get("blocked", "run"),
                "state": "done",
                "pending": False,
                "done": True
            }
        else:
            # Heutiger Tag NICHT fällig → Extra-Live (Fail-Guthaben)
            ustat["conf_count"] = int(ustat.get("conf_count", 0)) + 1
            ustat["fail_count"] = int(ustat.get("fail_count", 0)) - 1
            ustat["lastTodayState"] = "done"
            ustat["state"] = "not_pending"
            ustat["today"] = {
                "blocked": ustat.get("blocked", "run"),
                "state": "not_pending",
                "pending": False,
                "done": True
            }

    ustat["lastComputedAt"] = now_ms()
    per_user_map[str(uid)] = ustat
    save()

    # 🔔 Notification (mit Challenge-Namen)
    sender = _display_name(uid)
    ch_name = _challenge_name(cid)
    _notify_challenge_members(
        cid,
        uid,
        f"[{ch_name}] {sender} hat heute bestätigt.",
        kind="confirm",
    )

    return jsonify({"ok": True, "confirm": confirm}), 201

# ------------------------------------------------------------
# Invites
# ------------------------------------------------------------

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

    cid = inv["challengeId"]
    to_uid = inv["toUserId"]

    # Mitglied idempotent hinzufuegen
    already = any(m for m in st.setdefault("challenge_members", [])
                  if m.get("challengeId") == cid and m.get("userId") == to_uid)
    if not already:
        st["challenge_members"].append({"challengeId": cid, "userId": to_uid})

    inv["status"] = "accepted"
    save()

    # NUR init (kein recalc)
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    res = init_challenge_members(cid, tz_offset_minutes=tz)
    if "error" in res:
        return jsonify({"error": "init_failed", "details": res}), 400

    save()
    return jsonify({"ok": True, "initialized": True})

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

# ------------------------------------------------------------
# Leave
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# Stats: Recalc / Users
# ------------------------------------------------------------

@bp.route("/challenges/<int:cid>/stats/recalc", methods=["POST","GET"])
def challenge_stats_recalc(cid: int):
    """
    Recalc einer einzelnen Challenge.
    Optional: tzOffsetMinutes
    """
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    challenge_update_stats(cid, tz_offset_minutes=tz)
    return Response("recalc ok", mimetype="text/plain", status=200)

@bp.route("/challenges/stats/recalc_all", methods=["POST","GET"])
def challenges_stats_recalc_all():
    """
    Recalc fuer alle Challenges mit Teilnehmern.
    Optional: tzOffsetMinutes
    """
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    st = state()

    challenge_ids = {
        m.get("challengeId")
        for m in st.get("challenge_members", [])
        if m.get("challengeId") is not None
    }

    for cid in challenge_ids:
        try:
            challenge_update_stats(int(cid), tz_offset_minutes=tz)
        except Exception:
            # bewusst still weiter
            pass

    return Response("recalc ok", mimetype="text/plain", status=200)

@bp.get("/challenges/<int:cid>/stats")
def challenge_stats_users(cid: int):
    tz_offset = int(request.args.get("tzOffsetMinutes", "0"))
    st = state()

    ch = st.get("challenges", {}).get(str(cid)) or {}
    if not ch:
        return jsonify({"error": "not_found"}), 404

    dauer_tage = ch.get("dauerTage") or ch.get("days")
    faellige = ch.get("faelligeWochentage") or []
    erlaubte_fails = ch.get("erlaubteFailsTage")

    stats_all = st.get("challenge_stats", {}).get(str(cid), {})
    per_user_map = stats_all.get("perUser", {})

    def norm_challenge_status(val: str | None) -> str:
        v = (val or "").lower()
        if v in ("run",):
            return "run"
        if v in ("blocked", "gesperrt"):
            return "blocked"
        if v in ("done", "completed", "abgeschlossen"):
            return "done"
        return "none"

    def norm_today_status(val: str | None) -> str:
        v = (val or "").lower()
        if v in ("n_done", "not_done"):
            return "not_done"
        if v in ("done", "erledigt", "success"):
            return "done"
        if v in ("pending",):
            return "pending"
        if v in ("not_pending", "open", "offen"):
            return "not_pending"
        return "not_pending"

    per_user = []
    for uid_key, u in per_user_map.items():
        try:
            uid = int(uid_key)
        except Exception:
            uid = int(u.get("userId", 0)) if isinstance(u, dict) else 0

        conf_count = int(u.get("conf_count", u.get("confCount", 0)) or 0)
        fail_count = int(u.get("fail_count", u.get("failCount", 0)) or 0)
        streak     = int(u.get("streak", 0) or 0)
        neg_streak = int(u.get("neg_streak", u.get("negStreak", 0)) or 0)

        blocked_raw = u.get("blocked", u.get("challenge_status", "none"))
        challenge_status = norm_challenge_status(blocked_raw)

        last_today_raw = u.get("lastTodayState")
        challenge_today_status = norm_today_status(last_today_raw)

        status_out = norm_today_status(u.get("state"))

        per_user.append({
            "userId": uid,
            "confCount": conf_count,
            "failCount": fail_count,
            "streak": streak,
            "negStreak": neg_streak,
            "challenge_status": challenge_status,              # "none" | "run" | "blocked" | "done"
            "challenge_today_status": challenge_today_status,  # aus lastTodayState gemappt
            "status": status_out
        })

    resp = {
        "challengeId": cid,
        "dauerTage": dauer_tage,
        "erlaubteFailsTage": erlaubte_fails,
        "faelligeWochentage": faellige,
        "perUser": per_user,
    }
    return jsonify(resp)

# ------------------------------------------------------------
# Init
# ------------------------------------------------------------

@bp.post("/challenges/<int:cid>/init")
def challenge_init(cid: int):
    """
    Setzt alle Member der Challenge auf Anfang und stellt heute pending/not_pending korrekt.
    """
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    res = init_challenge_members(cid, tz_offset_minutes=tz)
    if "error" in res:
        code = 404 if res["error"] == "challenge_not_found" else 400
        return jsonify(res), code
    return jsonify({"status": "initialized", "challengeId": cid})

@bp.post("/challenges/init_all")
def challenges_init_all():
    """
    Initialisiert alle Challenges, die mind. einen Teilnehmer haben.
    """
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    st = state()

    challenge_ids = {
        m.get("challengeId")
        for m in st.get("challenge_members", [])
        if m.get("challengeId") is not None
    }

    ok = 0
    for cid in challenge_ids:
        res = init_challenge_members(int(cid), tz_offset_minutes=tz)
        if "error" not in res:
            ok += 1

    return jsonify({"status": "initialized", "count": ok})