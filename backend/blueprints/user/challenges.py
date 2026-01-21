from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from datetime import datetime, timedelta, timezone, date
import time
from backend.common.apns import send_apns

from backend.common.auth import auth_required
from backend.common.store import Database, now_ms  # kein next_id mehr!
from backend.models.schemas import (
    CreateChallengeBody,
    ChatBody,
    ConfirmBody,
    ChallengeInviteBody,
)
from backend.blueprints.user.stats import init_challenge_members

bp = Blueprint("challenges", __name__)
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")
DEBUG_INVITES = True  # ⬅️ True = Debug aktiv, False = Debug aus
DEBUG_CHAT = True  # ⬅️ True = Debug für Chat aktiv
DEBUG_CONFIRM = True  # ⬅️ True = Debug für Confirmations aktiv
DEBUG_OVERVIEW = True  # ⬅️ True = Debug für Overview aktiv


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

    # 1) Challenge
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

    # 2) Creator als Mitglied (status='creator')
    db.insert("challenge_members", {
        "challenge_id": cid,
        "user_id": request.uid,
        "joined_at": now,
        "status": "creator"
    })

    # 3) Chat-Start
    db.insert("challenge_chat", {
        "challenge_id": cid,
        "user_id": request.uid,
        "message": "Challenge erstellt 🎯",
        "image_url": None,
        "created_at": now
    })

    # 4) Stats initialisieren (setzt blocked basierend auf Startdatum)
    from backend.blueprints.user.stats import init_challenge_members
    init_challenge_members(cid)

    return jsonify({"id": cid, "initialized": True}), 201


# ============================================================
# Details / Mitglieder
# ============================================================

@bp.get("/challenges/<int:cid>")
@auth_required
def challenge_detail(cid: int):
    ch = db.find("challenges", where="id=%s", params=(cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404
    return jsonify(ch)


@bp.get("/challenges/<int:cid>/members")
@auth_required
def challenge_members(cid: int):
    res = db.query("""
        SELECT 
            u.id, 
            u.vorname, 
            u.name, 
            u.avatar,
            m.status,
            cs.blocked,
            cs.conf_count,
            cs.fail_count,
            cs.streak,
            cs.neg_streak,
            cs.today_pending,
            cs.today_done
        FROM challenge_members m
        JOIN users u ON u.id = m.user_id
        LEFT JOIN challenge_stats cs ON cs.challenge_id = %s AND cs.user_id = m.user_id
        WHERE m.challenge_id = %s
    """, (cid, cid))
    return jsonify(res)


# ============================================================
# Invites
# ============================================================





@bp.post("/challenges/<int:cid>/invites")
@auth_required
def send_invite(cid: int):
    """Fügt den eingeladenen Benutzer direkt in challenge_members mit Status 'pending' ein
       und legt sofort den passenden Eintrag in challenge_stats an (blocked='pending').
       Sendet zusätzlich eine APNs-Benachrichtigung an den eingeladenen User
       und erstellt eine Notification in der Datenbank.
    """
    if DEBUG_INVITES:
        print("\n[DEBUG] ▶ send_invite() gestartet")
        print(f"[DEBUG] challenge_id = {cid}")
        print(f"[DEBUG] request.uid = {request.uid}")
        print(f"[DEBUG] Raw JSON body = {request.get_data(as_text=True)}")

    # --- 1️⃣ Body validieren ---
    try:
        body = ChallengeInviteBody(**(request.get_json(force=True) or {}))
        to_user = body.toUserId
        message = body.message
    except ValidationError as e:
        if DEBUG_INVITES:
            print("[DEBUG] ❌ ValidationError:", e.errors())
        return jsonify({"error": "validation", "details": e.errors()}), 400

    # --- 2️⃣ Prüfen, ob der User bereits Mitglied ist ---
    existing = db.query_one(
        "SELECT * FROM challenge_members WHERE challenge_id=%s AND user_id=%s",
        (cid, to_user)
    )
    if existing:
        if DEBUG_INVITES:
            print(f"[DEBUG] ⚠️ User {to_user} ist bereits Mitglied (status={existing['status']})")
        return jsonify({
            "error": "already_member",
            "status": existing["status"]
        }), 400

    # --- 3️⃣ Insert in challenge_members vorbereiten ---
    insert_data = {
        "challenge_id": cid,
        "user_id": to_user,
        "status": "pending",
        "joined_at": now_ms()
    }

    try:
        db.query("SELECT invited_by FROM challenge_members LIMIT 1")
        insert_data["invited_by"] = request.uid
    except Exception:
        pass  # Spalte existiert nicht

    if DEBUG_INVITES:
        print("[DEBUG] ➡️ Insert Data für challenge_members:", insert_data)

    # --- 4️⃣ Insert ausführen ---
    try:
        new_id = db.insert("challenge_members", insert_data)
        if DEBUG_INVITES:
            print(f"[DEBUG] ✅ Neuer Eintrag in challenge_members erstellt: id={new_id}")
    except Exception as e:
        if DEBUG_INVITES:
            print("[DEBUG] ❌ DB-Fehler bei challenge_members:", e)
        return jsonify({"error": "db_insert_failed", "details": str(e)}), 500

    # --- 5️⃣ Sofort passenden Eintrag in challenge_stats anlegen ---
    now = now_ms()
    stats_data = {
        "challenge_id": cid,
        "user_id": to_user,
        "conf_count": 0,
        "fail_count": 0,
        "streak": 0,
        "neg_streak": 0,
        "blocked": "pending",
        "today_done": 0,
        "today_pending": 0,
        "last_computed": None,
        "created_at": now,
        "updated_at": now
    }

    try:
        sid = db.insert("challenge_stats", stats_data)
        if DEBUG_INVITES:
            print(f"[DEBUG] ✅ Neuer Eintrag in challenge_stats erstellt: id={sid}, blocked='pending'")
    except Exception as e:
        if DEBUG_INVITES:
            print(f"[DEBUG] ⚠️ Konnte challenge_stats nicht anlegen (vermutlich schon vorhanden): {e}")
        db.update(
            "challenge_stats",
            {"blocked": "pending", "updated_at": now},
            "challenge_id=%s AND user_id=%s",
            (cid, to_user),
        )
        if DEBUG_INVITES:
            print("[DEBUG] 🔁 Stattdessen UPDATE in challenge_stats durchgeführt")

    # --- 🧩 6️⃣ APNs Push + Notification speichern ---
    try:
        inviter = db.query_one("SELECT display_name FROM users WHERE id=%s", (request.uid,))
        challenge = db.query_one("SELECT title FROM challenges WHERE id=%s", (cid,))
        inviter_name = inviter["display_name"] if inviter else "Jemand"
        challenge_name = challenge["title"] if challenge else "eine Challenge"

        # Nachrichtentext
        push_message = f"{inviter_name} hat dich zur Challenge {challenge_name} eingeladen."

        # 🔹 ➕ Notification in DB speichern
        db.insert("notifications", {
            "user_id": to_user,
            "message": push_message,
            "type": "challenge_invite",
            "target_type": "challenge",
            "target_id": cid,
            "created_at": now_ms(),
            "read": 0
        })
        print(f"🗄️ Notification gespeichert für user_id={to_user}")

        # 🔹 ➕ APNs senden
        tokens = db.query("SELECT device_token FROM user_devices WHERE user_id=%s", (to_user,))
        if not tokens:
            print(f"⚠️ Kein Device-Token für user_id={to_user}")
        else:
            for t in tokens:
                token = t["device_token"]
                success = send_apns(token, title="Challenge Einladung", body=push_message)
                if success:
                    print(f"📤 APNs Push erfolgreich an {token[:12]}… (user={to_user})")
                else:
                    print(f"❌ APNs Push fehlgeschlagen für {token[:12]}… (user={to_user})")

    except Exception as e:
        print(f"⚠️ Fehler beim APNs-/Notification-Versand: {e}")

    # --- 7️⃣ Antwort zurückgeben ---
    return jsonify({
        "id": new_id,
        "challenge_id": cid,
        "user_id": to_user,
        "status": "pending",
        "message": message or None
    }), 201
        
        

@bp.post("/challenges/invites/<int:cid>/accept")
@auth_required
def accept_invite(cid: int):
    """Akzeptiert eine Challenge-Einladung, aktualisiert Status und Notifications."""
    uid = request.uid
    now = now_ms()

    # 1️⃣ Pending-Mitglied finden
    member = db.query_one(
        "SELECT * FROM challenge_members WHERE challenge_id=%s AND user_id=%s AND status='pending'",
        (cid, uid)
    )
    if not member:
        return jsonify({"error": "not_found"}), 404

    # 2️⃣ Status auf 'accepted' setzen
    db.update("challenge_members", {"status": "accepted"}, "id=%s", (member["id"],))

    # 3️⃣ Challenge-Start prüfen
    challenge = db.query_one("SELECT start_at, title FROM challenges WHERE id=%s", (cid,))
    start_at = challenge.get("start_at") if challenge else None
    challenge_name = challenge["title"] if challenge else "eine Challenge"

    if start_at and start_at <= now:
        blocked_state = "run"
    else:
        blocked_state = "not_started"

    # 4️⃣ challenge_stats aktualisieren oder erstellen
    stats = db.query_one(
        "SELECT id FROM challenge_stats WHERE challenge_id=%s AND user_id=%s",
        (cid, uid)
    )
    stats_data = {
        "blocked": blocked_state,
        "updated_at": now
    }

    if stats:
        db.update("challenge_stats", stats_data, "id=%s", (stats["id"],))
    else:
        stats_data.update({
            "challenge_id": cid,
            "user_id": uid,
            "conf_count": 0,
            "fail_count": 0,
            "streak": 0,
            "neg_streak": 0,
            "today_done": 0,
            "today_pending": 0,
            "created_at": now
        })
        db.insert("challenge_stats", stats_data)

    # 5️⃣ Notification (die Einladung selbst) als 'read' markieren
    db.update(
        "notifications",
        {"read": 1},
        "user_id=%s AND target_id=%s AND type=%s",
        (uid, cid, "challenge_invite")
    )

    # 6️⃣ Notification an den Einladenden
    inviter_id = member.get("invited_by")
    if inviter_id:
        user_name = db.scalar("SELECT display_name FROM users WHERE id=%s", (uid,)) or "Ein Nutzer"
        message = f"{user_name} hat deine Einladung zur Challenge '{challenge_name}' angenommen 🎉"

        db.insert("notifications", {
            "user_id": inviter_id,
            "message": message,
            "type": "challenge_invite_accept",
            "target_type": "challenge",
            "target_id": cid,
            "created_at": now,
            "read": 0
        })

    return jsonify({"ok": True, "blocked": blocked_state})

@bp.post("/challenges/invites/<int:cid>/decline")
@auth_required
def decline_invite(cid: int):
    """Lehnt eine Challenge-Einladung ab (löscht Mitglied & Stats)."""
    uid = request.uid
    now = now_ms()

    # 1️⃣ Pending-Mitglied finden
    member = db.query_one(
        "SELECT * FROM challenge_members WHERE challenge_id=%s AND user_id=%s AND status='pending'",
        (cid, uid)
    )
    if not member:
        return jsonify({"error": "not_found"}), 404

    inviter_id = member.get("invited_by")

    # 2️⃣ challenge_members-Eintrag löschen
    db.delete("challenge_members", "challenge_id=%s AND user_id=%s", (cid, uid))

    # 3️⃣ challenge_stats-Eintrag löschen (falls existiert)
    db.delete("challenge_stats", "challenge_id=%s AND user_id=%s", (cid, uid))

    # 4️⃣ Notification an den Einladenden
    if inviter_id:
        challenge = db.query_one("SELECT title FROM challenges WHERE id=%s", (cid,))
        challenge_name = challenge["title"] if challenge else "eine Challenge"
        user_name = db.scalar("SELECT display_name FROM users WHERE id=%s", (uid,)) or "Ein Nutzer"

        message = f"{user_name} hat deine Einladung zur Challenge '{challenge_name}' abgelehnt ❌"

        db.insert("notifications", {
            "user_id": inviter_id,
            "message": message,
            "type": "challenge_invite_decline",
            "target_type": "challenge",
            "target_id": cid,
            "created_at": now,
            "read": 0
        })

    # 5️⃣ Ursprüngliche Einladung-Notification als gelesen markieren
    db.update(
        "notifications",
        {"read": 1},
        "user_id=%s AND target_id=%s AND type=%s",
        (uid, cid, "challenge_invite")
    )

    return jsonify({"ok": True})



# ============================================================
# Leave Challenge
# ============================================================

@bp.post("/challenges/<int:cid>/leave")
@auth_required
def leave_challenge(cid: int):
    # Challenge-Daten holen
    challenge = db.query_one("SELECT start_at FROM challenges WHERE id=%s", (cid,))
    if not challenge:
        return jsonify({"error": "not_found", "message": "Challenge nicht gefunden."}), 404

    start_at = challenge["start_at"]
    now_ms = int(time.time() * 1000)

    # Prüfen, ob Challenge schon gestartet ist
    if start_at is not None and start_at <= now_ms:
        return jsonify({
            "error": "already_started",
            "message": "Challenge hat bereits begonnen und kann nicht mehr verlassen werden."
        }), 400

    # Mitglied entfernen
    db.delete(
        "challenge_members",
        where="challenge_id=%s AND user_id=%s",
        params=(cid, request.uid)
    )

    return jsonify({"ok": True})


# ============================================================
# User Challenge Overview (ueber Token)
# ============================================================

@bp.get("/challenges/user/overview")
@auth_required
def user_challenge_overview():
    uid = request.uid

    if DEBUG_OVERVIEW:
        print(f"\n🔵 [DEBUG] /challenges/user/overview aufgerufen von User {uid}")

    challenges = db.query("""
        SELECT 
            c.id AS ch_id,
            c.title AS name,
            c.duration_days AS dauerTage,
            c.allowed_fails AS erlaubteFailsTage,
            c.start_at,
            (
                SELECT blocked
                FROM challenge_stats
                WHERE id = (
                    SELECT MAX(id)
                    FROM challenge_stats
                    WHERE challenge_id=c.id AND user_id=%s
                )
            ) AS status
        FROM challenges c
        JOIN challenge_members m ON c.id = m.challenge_id
        WHERE m.user_id = %s
    """, (uid, uid))

    result = []
    for ch in challenges:
        cid = ch["ch_id"]

        # Alle Mitglieder abrufen
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
            WHERE m.challenge_id = %s
        """, (cid,))

        # Generiere fehlende Avatare
        from backend.utils.avatar_generator import get_or_create_avatar
        for member in members:
            if not member.get("avatar_url"):
                # Generiere Avatar wenn nicht vorhanden
                member["avatar_url"] = get_or_create_avatar(member.get("display_name"))

        # 🔄 Aktuellen User immer an den Anfang stellen
        members.sort(key=lambda x: 0 if x["user_id"] == uid else 1)

        result.append({
            "challenge": ch,
            "members": members
        })

    return jsonify(result)

# ============================================================
# Challenge Info
# ============================================================

@bp.get("/challenges/<int:cid>/info")
@auth_required
def get_challenge_info(cid: int):
    ch_id = cid

    # Challenge abrufen
    challenge = db.query_one("SELECT * FROM challenges WHERE id = %s", (ch_id,))
    if not challenge:
        return jsonify({"error": "not_found"}), 404

    # Mitglieder abrufen
    members = db.query("""
        SELECT 
            u.id AS user_id,
            u.display_name,
            u.avatar_url,
            m.joined_at
        FROM challenge_members m
        JOIN users u ON u.id = m.user_id
        WHERE m.challenge_id = %s
        ORDER BY m.joined_at ASC
    """, (ch_id,))

    result = {
        "challenge": {
            "id": challenge["id"],
            "title": challenge["title"],
            "description": challenge["description"],
            "creator_id": challenge["creator_id"],
            "start_at": challenge["start_at"],
            "duration_days": challenge["duration_days"],
            "allowed_fails": challenge["allowed_fails"],
            "due_weekdays": challenge["due_weekdays"],
            "created_at": challenge["created_at"],
            "updated_at": challenge.get("updated_at"),
        },
        "members": members
    }

    return jsonify(result)

# ============================================================
# Chat: Full
# ============================================================


@bp.get("/challenges/<int:cid>/chat/full")
@auth_required
def get_challenge_chat_full(cid: int):
    uid = request.uid

    if DEBUG_CHAT:
        print(f"\n💬 [DEBUG] /challenges/{cid}/chat/full aufgerufen von User {uid}")

    ch = db.query_one("SELECT * FROM challenges WHERE id=%s", (cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404
    if not ch:
        return jsonify({"error": "not_found"}), 404

    members = db.query("""
        SELECT 
            u.id AS user_id,
            u.display_name,
            u.avatar_url
        FROM challenge_members m
        JOIN users u ON u.id = m.user_id
        WHERE m.challenge_id = %s
        ORDER BY m.joined_at ASC
    """, (cid,))

    chat = db.query("""
        SELECT 
            c.id,
            c.challenge_id,
            c.user_id,
            c.message AS text,
            c.image_url,
            c.created_at
        FROM challenge_chat c
        WHERE c.challenge_id = %s
        ORDER BY c.created_at ASC
    """, (cid,))

    if DEBUG_CHAT:
        print(f"[DEBUG] Challenge gefunden: {ch.get('title') if ch else 'None'}")
        print(f"[DEBUG] Mitglieder: {len(members)}")
        for m in members:
            print(f"  - {m}")
        print(f"[DEBUG] Chat-Messages: {len(chat)}")
        for msg in chat:
            print(f"  - {msg}")

    response_data = {
        "challenge_id": cid,
        "current_user_id": uid,
        "members": members,
        "chat": chat
    }
    
    if DEBUG_CHAT:
        print(f"[DEBUG] Sende Response mit {len(response_data['members'])} members, {len(response_data['chat'])} messages")

    return jsonify(response_data)


# ============================================================
# Chat: Textnachricht
# ============================================================
@bp.post("/challenges/<int:cid>/chat/message")
@auth_required
def post_challenge_message(cid: int):
    data = request.get_json(force=True) or {}
    message = (data.get("message") or data.get("text") or "").strip()

    if DEBUG_CHAT:
        print(f"\n💬 [DEBUG] /challenges/{cid}/chat/message von User {request.uid}")
        print(f"[DEBUG] message: {message}")

    # Challenge prüfen
    ch = db.query_one("SELECT id, title FROM challenges WHERE id=%s", (cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404

    now = now_ms()

    # Leeres message erlauben (z.B. Bildbestätigung ohne Text)
    msg_id = db.insert("challenge_chat", {
        "challenge_id": cid,
        "user_id": request.uid,
        "message": message if message != "" else None,
        "image_url": None,
        "created_at": now
    })

    # ============================================================
    # 🧩 Notification in DB eintragen + APNs Push an andere Mitglieder
    # ============================================================
    try:
        # Namen & Challenge-Titel holen
        user = db.query_one("SELECT display_name FROM users WHERE id=%s", (request.uid,))
        username = user["display_name"] if user else "Jemand"
        challenge_title = ch["title"] or "eine Challenge"

        notif_message = (
            f"{username} hat in '{challenge_title}' "
            f"{'eine Nachricht gesendet' if message else 'ein Update geteilt'}."
        )

        # Alle anderen Mitglieder holen
        members = db.query(
            "SELECT user_id FROM challenge_members WHERE challenge_id=%s AND user_id != %s",
            (cid, request.uid)
        )

        for m in members:
            to_user = m["user_id"]

            # 📬 Notification in DB speichern
            nid = db.insert("notifications", {
                "user_id": to_user,
                "message": notif_message,
                "type": "challenge_message",
                "target_type": "challenge",
                "target_id": cid,
                "created_at": now,
                "read": 0
            })
            print(f"🔔 Notification erstellt (id={nid}, user={to_user}, challenge={cid})")

            # 📱 Push an alle Geräte des Users
            tokens = db.query("SELECT device_token FROM user_devices WHERE user_id=%s", (to_user,))
            if not tokens:
                print(f"⚠️ Kein Device-Token für user_id={to_user}")
                continue

            for t in tokens:
                token = t["device_token"]
                success = send_apns(token, title="Challenge-Nachricht", body=notif_message)
                if success:
                    print(f"📤 APNs Push erfolgreich an {token[:12]}… (user={to_user})")
                else:
                    print(f"❌ APNs Push fehlgeschlagen für {token[:12]}… (user={to_user})")

    except Exception as e:
        print(f"⚠️ Fehler beim Erstellen der Notification oder beim APNs-Versand: {e}")

    # ============================================================
    # ✅ Antwort zurückgeben
    # ============================================================
    return jsonify({
        "id": msg_id,
        "challenge_id": cid,
        "user_id": request.uid,
        "text": message if message != "" else None,
        "image_url": None,
        "created_at": now
    }), 201
    
    
# ============================================================
# Chat: Bild
# ============================================================

@bp.post("/challenges/<int:cid>/chat/image")
@auth_required
def post_challenge_image(cid: int):
    data = request.get_json(force=True) or {}
    image_url = (data.get("image_url") or "").strip()
    caption = (data.get("caption") or data.get("text") or "").strip()

    if not image_url:
        return jsonify({"error": "missing_image_url"}), 400

    ch = db.find("challenges", where="id=%s", params=(cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404

    now = now_ms()
    msg_id = db.insert("challenge_chat", {
        "challenge_id": cid,
        "user_id": request.uid,
        "message": caption or None,
        "image_url": image_url,
        "created_at": now
    })

    return jsonify({
        "id": msg_id,
        "challenge_id": cid,
        "user_id": request.uid,
        "text": caption or None,
        "image_url": image_url,
        "created_at": now
    }), 201


@bp.post("/challenges/<int:cid>/confirm")
@auth_required
def challenge_confirm(cid: int):
    """
    Fuegt eine Challenge-Bestaetigung hinzu und informiert andere Mitglieder via APNs + Notification-Eintrag.
    Verhindert doppelte Bestaetigungen am selben Tag.
    """
    if DEBUG_CONFIRM:
        print(f"\n✅ [DEBUG] /challenges/{cid}/confirm von User {request.uid}")

    ch = db.query_one("SELECT id, title, duration_days FROM challenges WHERE id=%s", (cid,))
    if not ch:
        return jsonify({"error": "not_found"}), 404

    try:
        body = ConfirmBody(**(request.get_json(force=True) or {}))
    except ValidationError as e:
        return jsonify({"error": "validation", "details": e.errors()}), 400

    uid = request.uid
    now = now_ms()
    duration_days = ch.get("duration_days") or 1
    def _normalize_visibility(vis: str) -> str:
        v = (vis or "friends").lower()
        if v in ("freunde", "friends"):
            return "friends"
        if v in ("privat", "private"):
            return "private"
        return "friends"
    body_visibility = _normalize_visibility(body.visibility)

    # 🔍 Prüfen, ob heute schon ein Confirm gemacht wurde
    today_stat = db.query_one("""
        SELECT today_done, updated_at
        FROM challenge_stats
        WHERE challenge_id=%s AND user_id=%s
    """, (cid, uid))

    if today_stat and today_stat["today_done"] == 1:
        print(f"⚠️ User {uid} hat heute schon bestätigt (challenge={cid})")
        return jsonify({
            "ok": False,
            "error": "already_confirmed_today",
            "message": "Du hast heute schon eine Bestaetigung gepostet 🕒"
        }), 400

    con, cur = db.begin_transaction()
    try:
        # 1️⃣ Mitgliedschaft sicherstellen
        cur.execute("""
            INSERT INTO challenge_members (challenge_id, user_id, status, joined_at)
            VALUES (%s, %s, 'accepted', %s)
            ON CONFLICT (challenge_id, user_id) DO NOTHING
        """, (cid, uid, now))

        # 2️⃣ Stats abrufen (mit Sperre)
        cur.execute("""
            SELECT id, conf_count FROM challenge_stats
            WHERE challenge_id=%s AND user_id=%s
            FOR UPDATE
        """, (cid, uid))
        stat = cur.fetchone()

        conf_count = (stat["conf_count"] + 1) if stat else 1
        progress = int((conf_count / duration_days) * 100)

        # 3️⃣ Feed-Post speichern
        cur.execute("""
            INSERT INTO feed_posts (user_id, challenge_id, content, image_url, visibility, progress, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (uid, cid, body.caption or "", body.imageUrl, body_visibility, progress, now, now))
        post_id = cur.fetchone()["id"]

        # 4️⃣ Stats aktualisieren oder neu anlegen
        if stat:
            cur.execute("""
                UPDATE challenge_stats
                SET conf_count = conf_count + 1,
                    streak = streak + 1,
                    today_done = 1,
                    updated_at = %s
                WHERE id = %s
            """, (now, stat["id"]))
        else:
            cur.execute("""
                INSERT INTO challenge_stats
                    (challenge_id, user_id, conf_count, fail_count, streak, neg_streak,
                     blocked, created_at, updated_at, today_done)
                VALUES (%s, %s, %s, 0, 1, 0, 'run', %s, %s, 1)
            """, (cid, uid, 1, now, now))

        # 5️⃣ Chat-Message speichern
        cur.execute("""
            INSERT INTO challenge_chat (challenge_id, user_id, message, image_url, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (cid, uid, body.caption or "", body.imageUrl, now))

        db.commit(con)

    except Exception as e:
        db.rollback(con)
        print(f"[ERROR] Confirm transaction failed: {e}")
        return jsonify({"error": "db_error", "message": str(e)}), 500

    # ============================================================
    # 📬 Notification + APNs an andere Mitglieder
    # ============================================================
    try:
        user = db.query_one("SELECT display_name FROM users WHERE id=%s", (uid,))
        username = user["display_name"] if user else "Jemand"
        challenge_title = ch["title"] or "eine Challenge"

        notif_message = f"{username} hat in '{challenge_title}' einen Erfolg bestätigt 🎉"

        members = db.query(
            "SELECT user_id FROM challenge_members WHERE challenge_id=%s AND user_id != %s",
            (cid, uid)
        )

        for m in members:
            to_user = m["user_id"]

            # 📬 Notification speichern
            nid = db.insert("notifications", {
                "user_id": to_user,
                "message": notif_message,
                "type": "challenge_confirm",
                "target_type": "challenge",
                "target_id": cid,
                "created_at": now,
                "read": 0
            })
            print(f"🔔 Notification erstellt (id={nid}, user={to_user}, challenge={cid})")

            # 📱 APNs Push
            tokens = db.query("SELECT device_token FROM user_devices WHERE user_id=%s", (to_user,))
            if not tokens:
                print(f"⚠️ Kein Device-Token für user_id={to_user}")
                continue

            for t in tokens:
                token = t["device_token"]
                success = send_apns(token, title="Challenge-Update", body=notif_message)
                if success:
                    print(f"📤 APNs Push erfolgreich an {token[:12]}… (user={to_user})")
                else:
                    print(f"❌ APNs Push fehlgeschlagen für {token[:12]}… (user={to_user})")

    except Exception as e:
        print(f"⚠️ Fehler beim Senden der Challenge-Confirm Push: {e}")

    # ============================================================
    # ✅ Antwort an den Client
    # ============================================================
    return jsonify({
        "ok": True,
        "confirm": {
            "challenge_id": cid,
            "challenge_title": ch["title"],
            "user_id": uid,
            "image_url": body.imageUrl,
            "caption": body.caption,
            "visibility": body.visibility,
            "progress": progress,
            "post_id": post_id,
            "created_at": now
        }
    }), 201