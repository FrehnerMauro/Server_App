from __future__ import annotations
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from datetime import datetime, timedelta, timezone, date

from backend.common.auth import auth_required
from backend.common.store import Database, now_ms, next_id
from backend.models.schemas import (
    CreateChallengeBody,
    ChatBody,
    ConfirmBody,
    ChallengeInviteBody,
)
from backend.services.stats import init_challenge_members
from backend.services.store_confirm import add_challenge_confirm

bp = Blueprint("challenges", __name__)
db = Database("state.db")

# ============================================================
# Helper
# ============================================================

def _normalize_weekdays(raw_list):
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
    if ts > 10**12:
        ts = ts // 1000
    tz = timezone(timedelta(minutes=tz_offset_min))
    return datetime.fromtimestamp(int(ts), tz).date()

# ============================================================
# Challenge Listing
# ============================================================
"""
@bp.get("/challenges/list")
@auth_required
def list_challenges():
    uid = request.uid
    with_today = (request.args.get("withToday") or "").lower() == "true"

    challenges = db.query("""

""", (uid,))

    if not with_today:
        return jsonify(challenges)

    # optional: Status für "heute"
    logs_today = db.query("""

""", (uid,))
    done_ids = {l["challenge_id"] for l in logs_today}

    for ch in challenges:
        ch_id = ch["id"]
        status = "done" if ch_id in done_ids else "open"
        ch["today"] = {"status": status, "pending": status == "open"}

    return jsonify(challenges)
    
    """


# ============================================================
# Challenge-Erstellung
# ============================================================

@bp.post("/challenges")
@auth_required
def create_challenge():
    try:
        body = CreateChallengeBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    now = now_ms()

    # 1️⃣ Challenge anlegen
    cid = db.insert("challenges", {
        "title": body.name,
        "description": body.beschreibung,
        "creator_id": request.uid,
        "due_weekdays": ",".join(map(str, body.faelligeWochentage or [])),
        "start_at": body.startAt or int(datetime.now().timestamp()),
        "duration_days": body.dauerTage,
        "allowed_fails": body.erlaubteFailsTage,
        "created_at": now,
    })

    # 2️⃣ Creator wird Mitglied
    db.insert("challenge_members", {
        "challenge_id": cid,
        "user_id": request.uid,
        "joined_at": now
    })

    # 3️⃣ Stats initialisieren
    db.insert("challenge_stats", {
        "challenge_id": cid,
        "user_id": request.uid,
        "conf_count": 0,
        "fail_count": 0,
        "streak": 0,
        "neg_streak": 0,
        "blocked": "run",
        "last_computed": None,
        "created_at": now,
        "updated_at": now
    })

    # 4️⃣ Chat vorbereiten
    db.insert("challenge_chat", {
        "challenge_id": cid,
        "user_id": request.uid,
        "message": "Challenge erstellt 🎯",
        "image_url": None,
        "created_at": now
    })

    # 5️⃣ Erfolgsmeldung
    return jsonify({"id": cid, "initialized": True}), 201

# ============================================================
# Details / Mitglieder / Aktivität
# ============================================================

@bp.get("/challenges/<int:cid>")
@auth_required
def challenge_detail(cid: int):
    ch = db.find("challenges", where="id=?", params=(cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404
    return jsonify(ch)


@bp.get("/challenges/<int:cid>/members")
@auth_required
def challenge_members(cid: int):
    res = db.query("""
        SELECT u.id, u.vorname, u.name, u.avatar
        FROM challenge_members m
        JOIN users u ON u.id = m.user_id
        WHERE m.challenge_id = ?
    """, (cid,))
    return jsonify(res)


@bp.get("/challenges/<int:cid>/activity")
@auth_required
def challenge_activity(cid: int):
    logs = db.query("SELECT * FROM challenge_logs WHERE challenge_id=?", (cid,))
    return jsonify(logs)

# ============================================================
# Chat
# ============================================================

@bp.post("/challenges/<int:cid>/chat")
@auth_required
def post_chat(cid: int):
    try:
        body = ChatBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    msg = {
        "challenge_id": cid,
        "user_id": request.uid,
        "text": body.text,
        "created_at": now_ms(),
    }
    db.insert("challenge_chat", msg)

    return jsonify(msg), 201


@bp.get("/challenges/<int:cid>/chat")
@auth_required
def list_chat(cid: int):
    msgs = db.query("SELECT * FROM challenge_chat WHERE challenge_id=?", (cid,))
    return jsonify(msgs)

# ============================================================
# Confirm
# ============================================================

@bp.post("/challenges/<int:cid>/confirm")
@auth_required
def challenge_confirm(cid: int):
    ch = db.find("challenges", where="id=?", params=(cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404

    try:
        body = ConfirmBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    confirm = add_challenge_confirm(
        challenge_id=cid,
        user_id=request.uid,
        image_url=body.imageUrl,
        caption=body.caption,
        visibility=body.visibility or "freunde",
    )

    db.insert("challenge_logs", {
        "challenge_id": cid,
        "user_id": request.uid,
        "data_json": str(confirm),
        "created_at": now_ms(),
    })

    return jsonify({"ok": True, "confirm": confirm}), 201

# ============================================================
# Invites
# ============================================================

@bp.get("/challenges/invites")
@auth_required
def list_invites():
    direction = (request.args.get("direction") or "").lower()
    uid = request.uid

    if direction == "incoming":
        data = db.query("SELECT * FROM challenge_invites WHERE to_user_id=? AND status='pending'", (uid,))
    elif direction == "outgoing":
        data = db.query("SELECT * FROM challenge_invites WHERE from_user_id=? AND status='pending'", (uid,))
    else:
        data = db.query("SELECT * FROM challenge_invites")

    return jsonify(data)


@bp.post("/challenges/<int:cid>/invites")
@auth_required
def send_invite(cid: int):
    try:
        body = ChallengeInviteBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    iid = db.insert("challenge_invites", {
        "challenge_id": cid,
        "from_user_id": request.uid,
        "to_user_id": body.toUserId,
        "message": body.message,
        "status": "pending",
        "created_at": now_ms()
    })

    return jsonify({"id": iid, "status": "pending"}), 201


@bp.post("/challenges/invites/<int:rid>/accept")
@auth_required
def accept_invite(rid: int):
    inv = db.find("challenge_invites", where="id=?", params=(rid,))
    if not inv:
        return jsonify({"error": "not_found"}), 404

    cid = inv["challenge_id"]
    to_uid = inv["to_user_id"]

    exists = db.find("challenge_members", where="challenge_id=? AND user_id=?", params=(cid, to_uid))
    if not exists:
        db.insert("challenge_members", {"challenge_id": cid, "user_id": to_uid})

    db.update("challenge_invites", {"status": "accepted"}, where="id=?", params=(rid,))

    tz = int(request.args.get("tzOffsetMinutes", "0"))
    res = init_challenge_members(cid, tz_offset_minutes=tz)
    if "error" in res:
        return jsonify({"error": "init_failed", "details": res}), 400

    return jsonify({"ok": True})


@bp.post("/challenges/invites/<int:rid>/decline")
@auth_required
def decline_invite(rid: int):
    inv = db.find("challenge_invites", where="id=?", params=(rid,))
    if not inv:
        return jsonify({"error": "not_found"}), 404
    db.update("challenge_invites", {"status": "declined"}, where="id=?", params=(rid,))
    return jsonify({"ok": True})

# ============================================================
# Leave Challenge
# ============================================================

@bp.post("/challenges/<int:cid>/leave")
@auth_required
def leave_challenge(cid: int):
    db.delete("challenge_members", where="challenge_id=? AND user_id=?", params=(cid, request.uid))
    return jsonify({"ok": True})


# ============================================================
# User Challe# ============================================================
# User Challenge Overview – automatisch via Token-User
# ============================================================
@bp.get("/challenges/user/overview")
@auth_required
def user_challenge_overview():
    """Gibt alle Challenges zurück, an denen der eingeloggte User teilnimmt, inkl. Members mit Stats & Avatar."""

    uid = request.uid  # 👈 User aus Token nehmen

    # 1️⃣ Alle Challenges, an denen der eingeloggte User teilnimmt
    challenges = db.query("""
        SELECT 
            c.id AS ch_id,
            c.title AS name,
            c.duration_days AS dauerTage,
            c.allowed_fails AS erlaubteFailsTage,
            c.start_at,
            (SELECT blocked FROM challenge_stats WHERE challenge_id=c.id AND user_id=?) AS status
        FROM challenges c
        JOIN challenge_members m ON c.id = m.challenge_id
        WHERE m.user_id = ?
    """, (uid, uid))

    result = []

    # 2️⃣ Für jede Challenge alle Mitglieder mit Stats, Avatar, heute-Status etc.
    for ch in challenges:
        cid = ch["ch_id"]

        members = db.query("""
            SELECT 
                u.id AS user_id,
                u.display_name,
                u.avatar_url,
                s.conf_count AS done_days,
                s.fail_count AS fail_days,
                s.streak,
                s.neg_streak,
                s.blocked AS status,
                s.today_done,
                s.today_pending
            FROM challenge_members m
            JOIN users u ON u.id = m.user_id
            LEFT JOIN challenge_stats s 
                ON s.user_id = u.id AND s.challenge_id = m.challenge_id
            WHERE m.challenge_id = ?
        """, (cid,))

        result.append({
            "challenge": ch,
            "members": members
        })

    return jsonify(result)