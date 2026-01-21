from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms
from backend.common.apns import send_apns  # nutzt PEM-basierten APNs-Sender

bp = Blueprint("notifications", __name__)
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

# ============================================================
# LIST NOTIFICATIONS
# ============================================================

@bp.get("/notifications")
@auth_required
def list_notifications():
    """Gibt alle *ungelesenen* Benachrichtigungen für den eingeloggten User zurück."""
    uid = request.uid
    rows = db.query("""
        SELECT 
            id,
            user_id,
            message,
            type,
            target_type,
            target_id,
            read,
            created_at
        FROM notifications
        WHERE user_id = %s AND read = 0
        ORDER BY created_at DESC
    """, (uid,))
    print(f"📨 /notifications → {len(rows)} ungelesene Einträge für User {uid}")
    return jsonify(rows)


# ============================================================
# MARK AS READ
# ============================================================

@bp.post("/notifications/mark_read/<int:notification_id>")
@auth_required
def mark_read(notification_id: int):
    """Markiert eine Benachrichtigung als gelesen (read = 1)."""
    uid = request.uid

    # Notification prüfen
    notif = db.query_one("SELECT * FROM notifications WHERE id=%s", (notification_id,))
    if not notif:
        print(f"⚠️ Notification {notification_id} nicht gefunden.")
        return jsonify({"error": "not_found"}), 404

    # Sicherheitscheck: gehört dem User
    if notif["user_id"] != uid:
        print(f"⚠️ User {uid} versucht fremde Notification {notification_id} zu markieren.")
        return jsonify({"error": "forbidden"}), 403

    # Update auf gelesen
    db.update("notifications", {"read": 1}, "id=%s", (notification_id,))
    print(f"✅ Notification {notification_id} als gelesen markiert (user={uid})")

    return jsonify({"ok": True, "notification_id": notification_id})


# ============================================================
# CLEAR ALL
# ============================================================

@bp.delete("/notifications/clear")
@auth_required
def clear_notifications():
    """Löscht alle Benachrichtigungen des eingeloggten Users."""
    uid = request.uid
    count = db.delete("notifications", "user_id=%s", (uid,))
    print(f"🧹 {count} Notifications für User {uid} gelöscht.")
    return jsonify({"ok": True, "deleted": count})


# ============================================================
# CREATE + PUSH SENDEN
# ============================================================

def create_notification_for_user(
    user_id: int,
    message: str,
    ntype: str,
    target_type: str = None,
    target_id: int = None
):
    """
    Erstellt eine Notification in der DB und sendet Push via Apple APNs (Zertifikat).
    """
    nid = db.insert("notifications", {
        "user_id": user_id,
        "message": message,
        "type": ntype,
        "target_type": target_type,
        "target_id": target_id,
        "created_at": now_ms(),
        "read": 0
    })

    print(f"🔔 Notification erstellt (user={user_id}, id={nid}, type={ntype})")

    # ------------------------------------------------------------
    # 📱 APNs Push senden (Zertifikatsauth)
    # ------------------------------------------------------------
    try:
        tokens = db.query(
            "SELECT device_token FROM user_devices WHERE user_id=%s",
            (user_id,)
        )

        if not tokens:
            print(f"⚠️ Kein Device-Token für user_id={user_id}")
        else:
            for t in tokens:
                device_token = t["device_token"]
                print(f"📲 Versuche Push an Device {device_token[:12]}…")
                success = send_apns(
                    device_token=device_token,
                    title="Neue Benachrichtigung",
                    body=message
                )
                if success:
                    print(f"✅ APNs Push erfolgreich an {device_token[:12]}… (user={user_id})")
                else:
                    print(f"❌ APNs Push fehlgeschlagen für {device_token[:12]}… (user={user_id})")

    except Exception as e:
        print(f"⚠️ Fehler beim Senden via APNs: {e}")

    return nid


# ============================================================
# MANUELLER TEST-ENDPUNKT
# ============================================================

@bp.post("/notifications/create")
def create_notification():
    """Test-Endpoint zum manuellen Erstellen einer Notification (z. B. via Postman)."""
    data = request.get_json(silent=True) or {}
    uid = data.get("user_id")
    msg = data.get("message") or "Neue Benachrichtigung"
    ntype = data.get("type") or "info"
    target_type = data.get("target_type")
    target_id = data.get("target_id")

    if not uid:
        return jsonify({"error": "user_id_required"}), 400

    nid = create_notification_for_user(
        user_id=uid,
        message=msg,
        ntype=ntype,
        target_type=target_type,
        target_id=target_id
    )

    print(f"🧪 Test-Notification erstellt (user={uid}, id={nid})")
    return jsonify({"ok": True, "id": nid})