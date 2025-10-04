from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from backend.common.auth import auth_required
from backend.common.store import state, save, now_ms, next_id
from backend.common.utils import day_window_ms_for_local_date
from backend.models.schemas import CreateChallengeBody, ChatBody, ConfirmBody, ChallengeInviteBody
from backend.services.store_confirm import add_challenge_confirm
from backend.services.stats import update_stats_for_challenge_today, init_challenge_members
import datetime
from datetime import datetime, timedelta, timezone, date
from backend.services.stats import challenge_update_stats  # statt update_stats_for_challenge_today
from collections import defaultdict
from flask import Response




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
    tz = int(request.args.get("tzOffsetMinutes", "0"))  # aktuell ungenutzt
    uid = request.uid

    # Nur Challenges, bei denen der User in challenge_members steht
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
            # "done" nur, wenn der eingeloggte User heute geloggt hat
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

    # >>> NEU: direkt initialisieren (nur diese Challenge)
    tz = int(request.args.get("tzOffsetMinutes", "0"))
    res = init_challenge_members(cid, tz_offset_minutes=tz)
    if "error" in res:
        # falls gewuenscht: aufraeumen/rollback; hier geben wir klaren Fehler zurueck
        return jsonify({"error": "init_failed", "details": res}), 400

    # optional: Stats direkt nachziehen (wenn init das nicht schon macht)
    try:
        challenge_update_stats(cid, tz_offset_minutes=tz)
    except Exception:
        # nicht fatal; du kannst hier loggen
        pass

    save()
    return jsonify({"id": cid, "initialized": True}), 201

# -------- Detail / Members / Activity --------

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
            "timestamp": l.get("timestamp"),
            "userId": l.get("userId"),
            "name": l.get("name"),
            "vorname": l.get("vorname"),
            "avatar": l.get("avatar"),
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

    # Mitgliedschaft pruefen
    if not any(m for m in st.get("challenge_members", []) if m.get("challengeId") == cid and m.get("userId") == uid):
        return jsonify({"error": "forbidden"}), 403

    # Body validieren
    try:
        body = ConfirmBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    # Timestamp bestimmen
    ts = body.timestamp or now_ms()
    tz = int(request.args.get("tzOffsetMinutes", "0"))

    # User-Daten auslesen
    user = st.get("users", {}).get(str(uid), {})
    user_info = {
        "userId": uid,
        "name": user.get("name"),
        "vorname": user.get("vorname"),
        "avatar": user.get("avatar"),
    }

    # Confirm / Log erstellen
    confirm = add_challenge_confirm(
        challenge_id=cid,
        user_id=uid,
        image_url=body.imageUrl,
        caption=body.caption,
        visibility=body.visibility or "freunde"
    )
    confirm["timestamp"] = int(ts)
    confirm.update(user_info)

    # In challenge_logs speichern/aktualisieren
    logs = st.setdefault("challenge_logs", {}).setdefault(str(cid), [])
    for c in logs:
        if c.get("id") == confirm.get("id"):
            c.update(confirm)
            break

    # --------------------------
    # → Stats direkt aktualisieren
    # --------------------------
    stats_all = st.setdefault("challenge_stats", {}).setdefault(str(cid), {})
    per_user_map = stats_all.setdefault("perUser", {})
    ustat = per_user_map.setdefault(str(uid), {
        "userId": uid,
        "conf_count": 0,
        "fail_count": 0,
        "streak": 0,
        "neg_streak": 0,
        "lastTodayState": "pending"
    })

    # Counter hoch
    ustat["conf_count"] = int(ustat.get("conf_count", 0)) + 1
    ustat["streak"] = int(ustat.get("streak", 0)) + 1
    ustat["neg_streak"] = 0
    ustat["lastTodayState"] = "done"

    # Falls er NICHT pending war (z.B. als fail gewertet), dann failCount korrigieren
    prev_state = ustat.get("lastTodayState")
    if prev_state not in ("pending", "not_pending"):
        ustat["fail_count"] = max(0, int(ustat.get("fail_count", 0)) - 1)

    save()

    # Optional trotzdem globales Recalc triggern (falls du willst)
    challenge_update_stats(cid, tz_offset_minutes=tz)

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
# routes.py (oder wo dein Blueprint definiert ist)


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

    # Challenge-Metadaten fuer Response
    dauer_tage = ch.get("dauerTage") or ch.get("days")
    faellige = ch.get("faelligeWochentage") or []
    erlaubte_fails = ch.get("erlaubteFailsTage")

    # Stats lesen
    stats_all = st.get("challenge_stats", {}).get(str(cid), {})
    per_user_map = stats_all.get("perUser", {})  # { "1": {...}, "2": {...} }

    def norm_challenge_status(val: str | None) -> str:
        v = (val or "").lower()
        if v in ("run",):
            return "run"
        if v in ("blocked", "gesperrt"):
            return "blocked"
        if v in ("done", "completed", "abgeschlossen"):
            return "done"
        return "none"

    # "not_done" soll als "pending" zurueckkommen
    def norm_today_status(val: str | None) -> str:
        v = (val or "").lower()
        if v in ("n_done", "not_done"):
            return "not_done"
        if v in ("done", "erledigt", "success"):
            return "done"
        if v in ("pending"):
            return "pending"
        if v in ("not_pending", "open", "offen"):
            return "not_pending"


    per_user = []
    for uid_key, u in per_user_map.items():
        # userId robust bestimmen
        try:
            uid = int(uid_key)
        except Exception:
            uid = int(u.get("userId", 0)) if isinstance(u, dict) else 0

        # Zaehlwerte robust lesen (unterstuetzt snake_case und camelCase)
        conf_count = int(u.get("conf_count", u.get("confCount", 0)) or 0)
        fail_count = int(u.get("fail_count", u.get("failCount", 0)) or 0)
        streak     = int(u.get("streak", 0) or 0)
        neg_streak = int(u.get("neg_streak", u.get("negStreak", 0)) or 0)

        # Challenge-Status normalisieren
        blocked_raw = u.get("blocked", u.get("challenge_status", "none"))
        challenge_status = norm_challenge_status(blocked_raw)

        # Heutiger Status NUR aus lastTodayState mappen
        last_today_raw = u.get("lastTodayState")
        challenge_today_status = norm_today_status(last_today_raw)

        # Kompatibles "status"-Feld: heutig gespeicherter state (pending/not_pending)
        status_out = norm_today_status(u.get("statex"))

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


# -------- Init Challenges --------


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

