from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms

bp = Blueprint("friends", __name__, url_prefix="/friends")
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

# ============================================================
# FRIEND REQUESTS (Pending)
# ============================================================

@bp.get("/requests")
@auth_required
def list_friend_requests():
    """Zeigt alle offenen Freundschaftsanfragen an den eingeloggten User."""
    uid = request.uid
    rows = db.query("""
        SELECT 
            f.id,
            f.user_id AS from_user_id,
            f.friend_id AS to_user_id,
            f.status,
            f.created_at,
            u.display_name,
            u.avatar_url
        FROM user_friends f
        JOIN users u ON u.id = f.user_id
        WHERE f.friend_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
    """, (uid,))
    return jsonify(rows)


# ============================================================
# FRIEND SEARCH
# ============================================================

@bp.get("/search")
@auth_required
def search_users():
    """
    Suche nach Benutzern anhand eines Suchbegriffs (Name oder Email).
    Gibt nur Basisinformationen zurück und markiert, ob bereits befreundet oder pending.
    """
    uid = request.uid
    q = request.args.get("query", "").strip()

    if not q:
        return jsonify({"error": "missing_query"}), 400

    # Benutzer suchen (Name oder Email match)
    users = db.query("""
        SELECT 
            u.id,
            u.display_name,
            u.avatar_url,
            CASE 
                WHEN f.status = 'accepted' THEN 'friend'
                WHEN f.status = 'pending' THEN 'pending'
                ELSE NULL
            END AS relation_status
        FROM users u
        LEFT JOIN user_friends f 
            ON ((f.user_id = LEAST(u.id, %s) AND f.friend_id = GREATEST(u.id, %s)))
        WHERE (LOWER(u.display_name) LIKE LOWER(%s) OR LOWER(u.email) LIKE LOWER(%s))
          AND u.id != %s
        ORDER BY u.display_name
        LIMIT 20
    """, (uid, uid, f"%{q}%", f"%{q}%", uid))

    return jsonify(users)


@bp.post("/request/<int:to_user_id>")
@auth_required
def send_friend_request(to_user_id: int):
    """Sende eine Freundschaftsanfrage an einen anderen User (mit APNs Push)."""
    uid = request.uid
    if uid == to_user_id:
        return jsonify({"error": "cannot_add_self"}), 400

    u1, u2 = sorted([uid, to_user_id])

    # Prüfen, ob bereits existiert
    existing = db.query_one("""
        SELECT * FROM user_friends WHERE user_id=%s AND friend_id=%s
    """, (u1, u2))

    if existing:
        status = existing["status"]

        if status == "pending":
            return jsonify({"error": "already_requested"}), 400
        elif status == "accepted":
            return jsonify({"error": "already_friends"}), 400
        elif status == "blocked":
            return jsonify({"error": "blocked"}), 403

        # Falls declined → wieder pending
        db.update(
            "user_friends",
            {"status": "pending", "updated_at": now_ms()},
            "user_id=%s AND friend_id=%s",
            (u1, u2)
        )

        # Notification trotzdem senden
        _notify_friend_request(sender_id=uid, receiver_id=to_user_id)
        return jsonify({"ok": True, "message": "request_resent"})

    # Neuer Eintrag
    db.insert("user_friends", {
        "user_id": u2,
        "friend_id": u1,
        "status": "pending",
        "created_at": now_ms(),
        "updated_at": now_ms()
    })

    # Notification + Push
    _notify_friend_request(sender_id=uid, receiver_id=to_user_id)

    return jsonify({"ok": True, "message": "request_sent"})


# ============================================================
# 🧩 Hilfsfunktion für Freundschafts-Notification
# ============================================================

def _notify_friend_request(sender_id: int, receiver_id: int):
    """Erstellt Notification & sendet APNs Push an den Empfänger."""
    try:
        # Nachricht generieren
        sender = db.query_one("SELECT username FROM users WHERE id=%s", (sender_id,))
        sender_name = sender["username"] if sender else f"User {sender_id}"
        msg = f"{sender_name} hat dir eine Freundschaftsanfrage gesendet 🤝"

        nid = db.insert("notifications", {
            "user_id": receiver_id,
            "message": msg,
            "type": "friend_request",
            "target_type": "user",
            "target_id": sender_id,
            "created_at": now_ms(),
            "read": 0
        })

        print(f"🔔 Friend-Request Notification erstellt (id={nid}, user={receiver_id})")

        # Device Tokens holen
        tokens = db.query("SELECT device_token FROM user_devices WHERE user_id=%s", (receiver_id,))
        if not tokens:
            print(f"⚠️ Kein Device-Token für user_id={receiver_id}")
            return

        from backend.common.apns import send_apns
        for t in tokens:
            token = t["device_token"]
            print(f"📲 Sende APNs an {token[:12]}…")
            success = send_apns(
                device_token=token,
                title="Neue Freundschaftsanfrage",
                body=msg
            )
            if success:
                print(f"✅ APNs Push erfolgreich an {token[:12]}… (user={receiver_id})")
            else:
                print(f"❌ APNs Push fehlgeschlagen für {token[:12]}… (user={receiver_id})")

    except Exception as e:
        print(f"⚠️ Fehler bei _notify_friend_request: {e}")

# ============================================================
# ACCEPT REQUEST
# ============================================================
@bp.post("/requests/<int:sender_uid>/accept")
@auth_required
def accept_friend_request(sender_uid: int):
    """Akzeptiert eine eingehende Freundschaftsanfrage anhand der Sender-User-ID."""
    receiver_uid = request.uid  # Der eingeloggte User
    now = now_ms()

    # Finde die Freundschaftsanfrage zwischen den beiden Usern (egal in welcher Reihenfolge gespeichert)
    req = db.query_one("""
        SELECT * FROM user_friends
        WHERE (user_id = %s AND friend_id = %s)
           OR (user_id = %s AND friend_id = %s)
    """, (sender_uid, receiver_uid, receiver_uid, sender_uid))

    if not req:
        return jsonify({"error": "not_found"}), 404

    # Nur annehmen, wenn der aktuelle User der Empfänger ist
    if req["friend_id"] != receiver_uid or req["status"] != "pending":
        return jsonify({"error": "forbidden"}), 403

    # Anfrage akzeptieren
    db.update(
        "user_friends",
        {"status": "accepted", "updated_at": now},
        "id=%s",
        (req["id"],)
    )

    # Ursprüngliche Notification auf gelesen setzen
    db.update(
        "notifications",
        {"read": 1},
        "user_id=%s AND target_id=%s AND type=%s",
        (receiver_uid, sender_uid, "friend_request")
    )

    # Neue Notification an den Sender
    receiver_name = db.scalar("SELECT display_name FROM users WHERE id=%s", (receiver_uid,)) or "Ein Nutzer"
    message = f"{receiver_name} hat deine Freundschaftsanfrage akzeptiert 🤝"

    db.insert("notifications", {
        "user_id": sender_uid,
        "message": message,
        "type": "friend_request_accept",
        "target_type": "user",
        "target_id": receiver_uid,
        "created_at": now,
        "read": 0
    })

    print(f"🤝 Friend request accepted: sender={sender_uid}, receiver={receiver_uid}")
    return jsonify({"ok": True, "message": "request_accepted"})

# ============================================================
# DECLINE REQUEST
# ============================================================

@bp.post("/requests/<int:sender_uid>/decline")
@auth_required
def decline_friend_request(sender_uid: int):
    """Lehnt eine eingehende Freundschaftsanfrage ab (nach Sender-User-ID)."""
    receiver_uid = request.uid  # Eingeloggter Benutzer
    now = now_ms()

    # Finde die Freundschaftsanfrage zwischen den beiden Usern
    req = db.query_one("""
        SELECT * FROM user_friends
        WHERE (user_id = %s AND friend_id = %s)
           OR (user_id = %s AND friend_id = %s)
    """, (sender_uid, receiver_uid, receiver_uid, sender_uid))

    if not req:
        return jsonify({"error": "not_found"}), 404

    # Nur ablehnen, wenn der aktuelle User der Empfänger ist und die Anfrage pending ist
    if req["friend_id"] != receiver_uid or req["status"] != "pending":
        return jsonify({"error": "forbidden"}), 403

    # Anfrage ablehnen
    db.update(
        "user_friends",
        {"status": "declined", "updated_at": now},
        "id=%s",
        (req["id"],)
    )

    # Ursprüngliche Notification auf gelesen setzen
    db.update(
        "notifications",
        {"read": 1},
        "user_id=%s AND target_id=%s AND type=%s",
        (receiver_uid, sender_uid, "friend_request")
    )

    # Neue Notification an den Sender
    receiver_name = db.scalar("SELECT display_name FROM users WHERE id=%s", (receiver_uid,)) or "Ein Nutzer"
    message = f"{receiver_name} hat deine Freundschaftsanfrage abgelehnt ❌"

    db.insert("notifications", {
        "user_id": sender_uid,
        "message": message,
        "type": "friend_request_decline",
        "target_type": "user",
        "target_id": receiver_uid,
        "created_at": now,
        "read": 0
    })

    print(f"❌ Friend request declined: sender={sender_uid}, receiver={receiver_uid}")
    return jsonify({"ok": True, "message": "request_declined"})

# ============================================================
# FRIEND LIST
# ============================================================

@bp.get("/list")
@auth_required
def list_friends():
    """Zeigt alle bestätigten Freunde des eingeloggten Users."""
    uid = request.uid
    rows = db.query("""
        SELECT 
            CASE 
                WHEN f.user_id = %s THEN f.friend_id
                ELSE f.user_id
            END AS friend_id,
            u.display_name,
            u.avatar_url
        FROM user_friends f
        JOIN users u ON u.id = CASE 
            WHEN f.user_id = %s THEN f.friend_id
            ELSE f.user_id
        END
        WHERE (f.user_id = %s OR f.friend_id = %s)
          AND f.status = 'accepted'
        ORDER BY u.display_name
    """, (uid, uid, uid, uid))
    return jsonify(rows)

# ============================================================
# REMOVE FRIEND
# ============================================================


@bp.delete("/remove/<int:friend_id>")
@auth_required
def remove_friend(friend_id: int):
    """Entfernt eine bestehende Freundschaft (beide Richtungen)."""
    uid = request.uid

    # Sicherstellen, dass der Freund tatsächlich existiert
    existing = db.query_one("""
        SELECT * FROM user_friends
        WHERE (user_id = %s AND friend_id = %s)
           OR (user_id = %s AND friend_id = %s)
          AND status = 'accepted'
    """, (uid, friend_id, friend_id, uid))

    if not existing:
        return jsonify({"error": "not_friends"}), 404

    # Freundschaft löschen
    try:
        con, cur = db.begin_transaction()
        cur.execute("""
            DELETE FROM user_friends
            WHERE (user_id = %s AND friend_id = %s)
               OR (user_id = %s AND friend_id = %s)
        """, (uid, friend_id, friend_id, uid))
        db.commit(con)
    except Exception as e:
        db.rollback(con)
        print("❌ Fehler beim Entfernen der Freundschaft:", e)
        return jsonify({"error": "db_error", "details": str(e)}), 500

    return jsonify({"ok": True, "message": "friend_removed"})

# ============================================================
# BLOCK USER
# ============================================================

@bp.post("/block/<int:blocked_id>")
@auth_required
def block_user(blocked_id: int):
    """Blockiert einen anderen Benutzer."""
    uid = request.uid

    # Selbstblock verhindern
    if uid == blocked_id:
        return jsonify({"error": "cannot_block_self"}), 400

    # Prüfen, ob Benutzer existiert
    user = db.query_one("SELECT id FROM users WHERE id=%s", (blocked_id,))
    if not user:
        return jsonify({"error": "user_not_found"}), 404

    # Prüfen, ob schon blockiert
    existing = db.query_one("""
        SELECT * FROM user_blocks
        WHERE user_id=%s AND blocked_user_id=%s
    """, (uid, blocked_id))
    if existing:
        return jsonify({"error": "already_blocked"}), 400

    # Freundschaft(en) löschen, falls vorhanden
    db.raw("""
        DELETE FROM user_friends
        WHERE (user_id=%s AND friend_id=%s)
           OR (user_id=%s AND friend_id=%s)
    """, (uid, blocked_id, blocked_id, uid))

    # Block speichern
    db.insert("user_blocks", {
        "user_id": uid,
        "blocked_user_id": blocked_id,
        "created_at": now_ms()
    })

    print(f"🛑 User {uid} hat User {blocked_id} blockiert.")
    return jsonify({"ok": True, "message": "user_blocked", "blocked_id": blocked_id})


# ============================================================
# UNBLOCK USER
# ============================================================

@bp.delete("/block/<int:blocked_id>")
@auth_required
def unblock_user(blocked_id: int):
    """Hebt eine bestehende Blockierung auf."""
    uid = request.uid

    existing = db.query_one("""
        SELECT * FROM user_blocks WHERE user_id=%s AND blocked_user_id=%s
    """, (uid, blocked_id))

    if not existing:
        return jsonify({"error": "not_blocked"}), 404

    db.delete("user_blocks", where="user_id=%s AND blocked_user_id=%s", params=(uid, blocked_id))
    print(f"✅ User {uid} hat User {blocked_id} entblockiert.")
    return jsonify({"ok": True, "message": "user_unblocked", "unblocked_id": blocked_id})


# ============================================================
# LIST BLOCKS
# ============================================================

@bp.get("/blocks")
@auth_required
def list_blocks():
    """Listet alle vom eingeloggten Benutzer blockierten Nutzer auf."""
    uid = request.uid

    rows = db.query("""
        SELECT 
            b.blocked_user_id AS user_id,
            u.display_name,
            u.avatar_url,
            b.created_at
        FROM user_blocks b
        JOIN users u ON u.id = b.blocked_user_id
        WHERE b.user_id = %s
        ORDER BY u.display_name
    """, (uid,))

    return jsonify(rows)