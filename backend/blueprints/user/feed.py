from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms
from pydantic import ValidationError
import psycopg2  # fuer IntegrityError

bp = Blueprint("feed", __name__, url_prefix="/feed")
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")


def _normalize_visibility(vis: str) -> str:
    v = (vis or "").lower()
    if v in ("freunde", "friends"):
        return "friends"
    if v in ("privat", "private"):
        return "private"
    return "friends"

# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def _friend_ids(uid: int) -> list[int]:
    """IDs aller Freunde (status='accepted')."""
    rows = db.query("""
        SELECT 
            CASE 
                WHEN user_id = %s THEN friend_id 
                ELSE user_id 
            END AS fid
        FROM user_friends
        WHERE (user_id=%s OR friend_id=%s) AND status='accepted'
    """, (uid, uid, uid))
    return [r["fid"] for r in rows]

def _is_friend(uid1: int, uid2: int) -> bool:
    """Prueft Freundschaft (reihenfolgeunabhaengig)."""
    row = db.query_one("""
        SELECT 1 FROM user_friends 
        WHERE ((user_id=%s AND friend_id=%s) OR (user_id=%s AND friend_id=%s))
          AND status='accepted' 
        LIMIT 1
    """, (uid1, uid2, uid2, uid1))
    return row is not None

def _visible_for_user(post: dict, uid: int) -> bool:
    """Sichtbarkeit eines Fremd-Posts fuer uid."""
    if post["user_id"] == uid:
        # Eigene Posts werden NICHT hier beurteilt (siehe Feed-Filter),
        # hier nur fuer Fremde:
        return True
    vis = _normalize_visibility(post.get("visibility"))
    if vis == "friends":
        return _is_friend(post["user_id"], uid)
    return False

def _notify_post_owner(post_id: int, actor_user_id: int, message_text: str, notif_type: str):
    """
    Legt eine Notification für den Besitzer des Posts an und sendet optional APNs.
    Kompatibel mit dem aktuellen Schema:
    (user_id, message, type, target_type, target_id, created_at, read)
    """
    post = db.query_one("SELECT user_id FROM feed_posts WHERE id=%s", (post_id,))
    if not post:
        print(f"⚠️ _notify_post_owner: Post {post_id} nicht gefunden")
        return

    owner_id = post["user_id"]
    if owner_id == actor_user_id:
        # Keine Benachrichtigung an sich selbst
        return

    # Namen des Absenders holen
    actor_name = db.scalar("SELECT display_name FROM users WHERE id=%s", (actor_user_id,)) or "Jemand"

    # Nachricht zusammenbauen (kannst du anpassen)
    message = f"{actor_name} hat deinen Beitrag {message_text}."

    # Notification eintragen
    nid = db.insert("notifications", {
        "user_id": owner_id,
        "message": message,
        "type": notif_type,          # z.B. "feed_comment" oder "feed_like"
        "target_type": "feed_post",  # damit du im Frontend weisst, wohin der Link führt
        "target_id": post_id,
        "created_at": now_ms(),
        "read": 0
    })
    print(f"🔔 Notification erstellt (id={nid}, user={owner_id}, type={notif_type})")

    # Optionale APNs-Pushes (falls du willst)
    try:
        tokens = db.query("SELECT device_token FROM user_devices WHERE user_id=%s", (owner_id,))
        from backend.common.apns import send_apns
        for t in tokens or []:
            token = t["device_token"]
            ok = send_apns(token, title="Neuer Kommentar", body=message)
            if ok:
                print(f"📤 APNs Push → {token[:12]}… (user={owner_id})")
            else:
                print(f"❌ APNs Push fehlgeschlagen → {token[:12]}… (user={owner_id})")
    except Exception as e:
        print(f"⚠️ Push-Error: {e}")

def _augment_post(post: dict, uid: int) -> dict:
    """Fuegt likesCount, likedByMe, commentsCount hinzu."""
    pid = post["id"]
    likes_count = db.scalar("SELECT COUNT(*) FROM feed_likes WHERE post_id=%s", (pid,))
    liked_by_me = db.scalar("SELECT 1 FROM feed_likes WHERE post_id=%s AND user_id=%s", (pid, uid))
    comments_count = db.scalar("SELECT COUNT(*) FROM feed_comments WHERE post_id=%s", (pid,))

    post["likesCount"] = likes_count or 0
    post["likedByMe"] = liked_by_me is not None
    post["commentsCount"] = comments_count or 0
    return post

# ============================================================
# FEED
# ============================================================

@bp.get("/")
@auth_required
def feed():
    """
    Feed mit Posts + Anzeigen.
    - Posts von Freunden (visibility='friends')
    - Eigene Posts (visibility='friends')
    - Anzeigen alle 6 Posts eingestreut
    """
    try:
        uid = request.uid
        friend_ids = _friend_ids(uid)

        # Kandidaten: eigene ID + Freunde
        visible_ids = friend_ids + [uid]
        if not visible_ids:
            return jsonify([])

        placeholders = ",".join(["%s"] * len(visible_ids))

        # Posts laden
        posts = db.query(f"""
            SELECT
                p.id,
                p.user_id,
                p.content,
                p.image_url,
                p.visibility,
                p.progress,
                p.challenge_id,
                p.created_at,
                p.updated_at,
                u.display_name,
                u.avatar_url,
                c.title AS challenge_title
            FROM feed_posts p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN challenges c ON c.id = p.challenge_id
            WHERE p.user_id IN ({placeholders})
            ORDER BY p.created_at DESC
        """, tuple(visible_ids))

        # Filter + Aufbereitung
        visible_posts = []
        for p in posts:
            vis = _normalize_visibility(p.get("visibility"))
            p["visibility"] = vis
            
            if p["user_id"] == uid:
                if vis == "friends":
                    visible_posts.append(p)
            else:
                if _visible_for_user(p, uid):
                    visible_posts.append(p)

        # Posts mit Likes/Comments erweitern
        for post in visible_posts:
            post["kind"] = "post"
            _augment_post(post, uid)

        # ===== ADS SECTION =====
        now = now_ms()
        ads_list = []
        try:
            ads_list = db.query("""
                SELECT id, image_url, click_url, headline, body, cta_label, weight
                FROM feed_ads
                WHERE status='active'
                  AND (start_at IS NULL OR start_at <= %s)
                  AND (end_at IS NULL OR end_at >= %s)
                ORDER BY weight DESC, id
            """, (now, now)) or []
        except Exception as e:
            print(f"⚠️ Ad loading error: {e}")

        # Wenn keine Posts, keine Ads
        if not visible_posts:
            return jsonify([])

        # Wenn keine Ads, nur Posts
        if not ads_list:
            return jsonify(visible_posts)

        # ===== ADS INJECTION =====
        result = []
        ad_slot = 6
        post_count = 0
        ad_idx = 0

        for post in visible_posts:
            result.append(post)
            post_count += 1

            # Jeden 6. Post eine Ad einstreuen
            if post_count % ad_slot == 0 and ad_idx < len(ads_list):
                ad = ads_list[ad_idx]
                ad_idx += 1

                ad_item = {
                    "kind": "ad",
                    "id": ad.get("id"),
                    "image_url": ad.get("image_url"),
                    "click_url": ad.get("click_url"),
                    "headline": ad.get("headline"),
                    "body": ad.get("body"),
                    "cta_label": ad.get("cta_label"),
                }
                result.append(ad_item)

                # Impression tracken
                try:
                    db.insert("feed_ad_events", {
                        "ad_id": ad.get("id"),
                        "user_id": uid,
                        "event_type": "impression",
                        "created_at": now_ms()
                    })
                    db.raw("UPDATE feed_ads SET impressions = impressions + 1 WHERE id=%s", (ad.get("id"),))
                except Exception as e:
                    print(f"⚠️ Impression tracking error: {e}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Feed error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



# ============================================================
# LIKES
# ============================================================

@bp.post("/<int:pid>/like")
@auth_required
def like_post(pid: int):
    uid = request.uid
    post = db.query_one("SELECT * FROM feed_posts WHERE id=%s", (pid,))
    if not post:
        return jsonify({"error": "not_found"}), 404

    if post["user_id"] == uid:
        if _normalize_visibility(post.get("visibility")) != "friends":
            return jsonify({"error": "forbidden"}), 403
    else:
        if not _visible_for_user(post, uid):
            return jsonify({"error": "forbidden"}), 403

    try:
        db.insert("feed_likes", {
            "post_id": pid,
            "user_id": uid,
            "created_at": now_ms(),
        })
    except psycopg2.IntegrityError:
        # schon geliked -> ignorieren
        pass

    likes_count = db.scalar("SELECT COUNT(*) FROM feed_likes WHERE post_id=%s", (pid,)) or 0
    _notify_post_owner(pid, uid, "jemand hat deinen Beitrag geliked", "feed_like")

    return jsonify({"ok": True, "likesCount": likes_count, "likedByMe": True})

@bp.post("/<int:pid>/unlike")
@auth_required
def unlike_post(pid: int):
    uid = request.uid
    post = db.query_one("SELECT * FROM feed_posts WHERE id=%s", (pid,))
    if not post:
        return jsonify({"error": "not_found"}), 404

    if post["user_id"] == uid:
        if _normalize_visibility(post.get("visibility")) != "friends":
            return jsonify({"error": "forbidden"}), 403
    else:
        if not _visible_for_user(post, uid):
            return jsonify({"error": "forbidden"}), 403

    db.delete("feed_likes", "post_id=%s AND user_id=%s", (pid, uid))
    likes_count = db.scalar("SELECT COUNT(*) FROM feed_likes WHERE post_id=%s", (pid,)) or 0
    return jsonify({"ok": True, "likesCount": likes_count, "likedByMe": False})

# ============================================================
# KOMMENTARE
# ============================================================

@bp.get("/<int:pid>/comments")
@auth_required
def get_comments(pid: int):
    uid = request.uid
    post = db.query_one("SELECT * FROM feed_posts WHERE id=%s", (pid,))
    if not post:
        return jsonify({"error": "not_found"}), 404

    if post["user_id"] == uid:
        if _normalize_visibility(post.get("visibility")) != "friends":
            return jsonify({"error": "forbidden"}), 403
    else:
        if not _visible_for_user(post, uid):
            return jsonify({"error": "forbidden"}), 403

    comments = db.query("""
        SELECT c.*, u.display_name, u.avatar_url
        FROM feed_comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.post_id=%s
        ORDER BY c.created_at DESC
    """, (pid,))
    return jsonify(comments)

@bp.post("/<int:pid>/comments")
@auth_required
def add_comment(pid: int):
    uid = request.uid
    post = db.query_one("SELECT * FROM feed_posts WHERE id=%s", (pid,))
    if not post:
        return jsonify({"error": "not_found"}), 404

    if post["user_id"] == uid:
        if (post.get("visibility") or "").lower() != "friends":
            return jsonify({"error": "forbidden"}), 403
    else:
        if not _visible_for_user(post, uid):
            return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "validation", "message": "text required"}), 400

    now = now_ms()
    cid = db.insert("feed_comments", {
        "post_id": pid,
        "user_id": uid,
        "content": text,
        "created_at": now,
        "updated_at": now,
    })

    _notify_post_owner(pid, uid, "jemand hat deinen Beitrag kommentiert", "feed_comment")

    return jsonify({
        "id": cid,
        "post_id": pid,
        "user_id": uid,
        "text": text,
        "created_at": now
    }), 201


# ============================================================
# AD EVENTS
# ============================================================

@bp.post("/ads/<int:aid>/click")
@auth_required
def track_ad_click(aid: int):
    ad = db.query_one("SELECT id FROM feed_ads WHERE id=%s", (aid,))
    if not ad:
        return jsonify({"error": "not_found"}), 404
    db.insert("feed_ad_events", {
        "ad_id": aid,
        "user_id": request.uid,
        "event_type": "click",
        "created_at": now_ms()
    })
    db.raw("UPDATE feed_ads SET clicks = clicks + 1 WHERE id=%s", (aid,))
    return jsonify({"ok": True})

@bp.delete("/<int:pid>/comments/<int:cid>")
@auth_required
def delete_comment(pid: int, cid: int):
    uid = request.uid
    comment = db.query_one("SELECT * FROM feed_comments WHERE id=%s", (cid,))
    if not comment:
        return jsonify({"error": "not_found"}), 404

    if comment["user_id"] != uid:
        user = db.query_one("SELECT is_admin FROM users WHERE id=%s", (uid,))
        if not user or int(user.get("is_admin") or 0) != 1:
            return jsonify({"error": "forbidden", "message": "only owner or admin can delete"}), 403

    db.delete("feed_comments", "id=%s", (cid,))
    return jsonify({"ok": True})


# ============================================================
# POST LÖSCHEN
# ============================================================
@bp.delete("/<int:pid>")
@auth_required
def delete_post(pid: int):
    """Loescht einen Feed-Post sowie alle zugehoerigen Likes und Kommentare."""
    uid = request.uid

    # --- 1️⃣ Post abrufen ---
    post = db.query_one("SELECT * FROM feed_posts WHERE id=%s", (pid,))
    if not post:
        return jsonify({"error": "not_found"}), 404

    # --- 2️⃣ Berechtigung prüfen ---
    if post["user_id"] != uid:
        user = db.query_one("SELECT is_admin FROM users WHERE id=%s", (uid,))
        if not user or int(user.get("is_admin") or 0) != 1:
            return jsonify({
                "error": "forbidden",
                "message": "Nur der Besitzer oder ein Admin darf den Post löschen."
            }), 403

    # --- 3️⃣ Transaktion starten ---
    con, cur = db.begin_transaction()
    try:
        # Zuerst abhängige Daten löschen
        cur.execute("DELETE FROM feed_comments WHERE post_id=%s", (pid,))
        cur.execute("DELETE FROM feed_likes WHERE post_id=%s", (pid,))

        # Dann den Post selbst löschen
        cur.execute("DELETE FROM feed_posts WHERE id=%s", (pid,))

        db.commit(con)
        return jsonify({"ok": True, "message": "Post und zugehörige Daten gelöscht."}), 200

    except Exception as e:
        db.rollback(con)
        print(f"[ERROR] Post löschen fehlgeschlagen: {e}")
        return jsonify({"error": "db_error", "details": str(e)}), 500