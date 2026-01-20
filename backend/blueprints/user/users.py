from flask import Blueprint, jsonify, request
from backend.common.auth import auth_required
from backend.common.store import Database

bp = Blueprint("users", __name__, url_prefix="/users")
db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

# =============================================================
#   EIGENES PROFIL
# =============================================================
@bp.get("/me")
@auth_required
def get_my_profile():
    uid = request.uid
    print(f"\n🟢 [DEBUG] Aufruf /users/me von User {uid}")

    # USERDATEN LADEN
    user = db.query_one("SELECT * FROM users WHERE id=%s", (uid,))
    if not user:
        print(f"🔴 [DEBUG] Kein User mit ID {uid} gefunden!")
        return jsonify({"error": "not_found"}), 404
    user.pop("password", None)
    print(f"🧍 [DEBUG] Userdaten gefunden: {user}")

    # FREUNDE ZÄHLEN
    freunde = db.query("""
        SELECT COUNT(*) AS count
        FROM user_friends
        WHERE status='accepted' AND (user_id=%s OR friend_id=%s)
    """, (uid, uid))
    anzahl_freunde = freunde[0]["count"] if freunde else 0
    print(f"👥 [DEBUG] Freunde gefunden: {anzahl_freunde}")

    # POSTS LADEN
    posts = db.query("""
        SELECT 
            p.id, p.content, p.image_url, p.visibility, p.created_at,
            (SELECT COUNT(*) FROM feed_likes l WHERE l.post_id = p.id) AS like_count,
            (SELECT COUNT(*) FROM feed_comments c WHERE c.post_id = p.id) AS comment_count
        FROM feed_posts p
        WHERE p.user_id = %s
        ORDER BY p.created_at DESC
    """, (uid,))
    print(f"📝 [DEBUG] Gefundene Posts für User {uid}: {len(posts)}")

    # Hilfsfunktion Sichtbarkeit
    def vis(p):
        v = (p.get("visibility") or "").strip().lower()
        if v in ("privat", "private"):
            return "privat"
        elif v in ("freunde", "friends"):
            return "freunde"
        else:
            return "freunde"

    privat_posts = [p for p in posts if vis(p) == "privat"]
    freunde_posts = [p for p in posts if vis(p) == "freunde"]
    print(f"🔍 [DEBUG] privat={len(privat_posts)}, freunde={len(freunde_posts)}")

    # KOMMENTARE & LIKES
    for p in posts:
        pid = p["id"]
        p["comments"] = db.query("""
            SELECT c.id, c.content AS comment, c.created_at, u.display_name, u.avatar_url
            FROM feed_comments c
            JOIN users u ON u.id = c.user_id
            WHERE c.post_id = %s
            ORDER BY c.created_at ASC
        """, (pid,))
        p["likes"] = db.query("""
            SELECT l.user_id, u.display_name, u.avatar_url
            FROM feed_likes l
            JOIN users u ON u.id = l.user_id
            WHERE l.post_id = %s
        """, (pid,))
        print(f"💬 [DEBUG] Post {pid}: {len(p['comments'])} Kommentare, {len(p['likes'])} Likes")

    profile = {
        "id": user["id"],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "anzahl_freunde": anzahl_freunde,
        "anzahl_posts": len(posts),
        "meine_posts": {
            "privat": privat_posts,
            "freunde": freunde_posts
        }
    }

    print(f"✅ [DEBUG] Profil erstellt für {user.get('display_name')}\n")
    return jsonify(profile)


# =============================================================
#   FREMDES PROFIL
# =============================================================
@bp.get("/<int:target_uid>")
@auth_required
def get_user_profile(target_uid: int):
    requester_id = request.uid
    print(f"\n🟣 [DEBUG] Aufruf /users/{target_uid} von User {requester_id}")

    user = db.query_one("SELECT * FROM users WHERE id=%s", (target_uid,))
    if not user:
        print(f"🔴 [DEBUG] Kein Zieluser {target_uid} gefunden!")
        return jsonify({"error": "not_found"}), 404
    user.pop("password", None)
    print(f"🧍 [DEBUG] Zieluser gefunden: {user.get('display_name')}")

    friendship = db.query_one("""
        SELECT 1 FROM user_friends
        WHERE ((user_id=%s AND friend_id=%s) OR (user_id=%s AND friend_id=%s))
          AND status='accepted'
        LIMIT 1
    """, (requester_id, target_uid, target_uid, requester_id))
    is_friend = friendship is not None
    print(f"🤝 [DEBUG] Freundschaft zwischen {requester_id} und {target_uid}: {is_friend}")

    visibility_filter = ("public", "friends", "freunde") if is_friend else ("public",)
    print(f"👁 [DEBUG] Sichtbarkeitsfilter aktiv: {visibility_filter}")

    posts = db.query("""
        SELECT 
            p.id, p.content, p.image_url, p.visibility, p.created_at,
            (SELECT COUNT(*) FROM feed_likes l WHERE l.post_id = p.id) AS like_count,
            (SELECT COUNT(*) FROM feed_comments c WHERE c.post_id = p.id) AS comment_count
        FROM feed_posts p
        WHERE p.user_id = %s
        ORDER BY p.created_at DESC
    """, (target_uid,))
    print(f"📝 [DEBUG] Gefundene Posts bei User {target_uid}: {len(posts)}")

    def vis(p):
        v = (p.get("visibility") or "").strip().lower()
        if v in ("privat", "private"):
            return "privat"
        elif v in ("freunde", "friends"):
            return "freunde"
        elif v in ("public", "öffentlich", "oeffentlich"):
            return "public"
        else:
            return "freunde"

    visible_posts = [p for p in posts if vis(p) in visibility_filter]
    print(f"📸 [DEBUG] Sichtbare Posts für {requester_id}: {len(visible_posts)}")

    for p in visible_posts:
        pid = p["id"]
        p["comments"] = db.query("""
            SELECT c.id, c.comment, c.created_at, u.display_name, u.avatar_url
            FROM feed_comments c
            JOIN users u ON u.id = c.user_id
            WHERE c.post_id = %s
            ORDER BY c.created_at ASC
        """, (pid,))
        p["likes"] = db.query("""
            SELECT l.user_id, u.display_name, u.avatar_url
            FROM feed_likes l
            JOIN users u ON u.id = l.user_id
            WHERE l.post_id = %s
        """, (pid,))
        print(f"💬 [DEBUG] Post {pid}: {len(p['comments'])} Kommentare, {len(p['likes'])} Likes")

    freunde = db.query("""
        SELECT COUNT(*) AS count
        FROM user_friends
        WHERE status='accepted' AND (user_id=%s OR friend_id=%s)
    """, (target_uid, target_uid))
    anzahl_freunde = freunde[0]["count"] if freunde else 0

    profile = {
        "id": user["id"],
        "display_name": user.get("display_name"),
        "avatar_url": user.get("avatar_url"),
        "anzahl_freunde": anzahl_freunde,
        "anzahl_posts": len(visible_posts),
        "meine_posts": {
            "freunde": [p for p in visible_posts if vis(p) == "freunde"],
            "public": [p for p in visible_posts if vis(p) == "public"]
        }
    }

    print(f"✅ [DEBUG] Profil für {user.get('display_name')} erfolgreich abgerufen. is_friend={is_friend}\n")
    return jsonify(profile)