from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import Database, now_ms
from pydantic import ValidationError

bp = Blueprint("feed", __name__)
db = Database("state.db")

# ============================================================
# Helper
# ============================================================

def _is_friend(uid: int, other: int) -> bool:
    if uid == other:
        return True
    row = db.query_one("""
        SELECT 1 FROM friends 
        WHERE status='accepted'
          AND ((from_user_id=? AND to_user_id=?) OR (from_user_id=? AND to_user_id=?))
    """, (uid, other, other, uid))
    return bool(row)

def _visible_for_user(post: dict, uid: int) -> bool:
    owner = post["user_id"]
    vis = (post.get("visibility") or "freunde").lower()
    if owner == uid:
        return True
    if vis == "privat":
        return False
    if vis == "freunde":
        return _is_friend(uid, owner)
    return True  # "public"

def _augment_post(post: dict, uid: int) -> dict:
    likes_count = db.scalar("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (post["id"],))
    comments_count = db.scalar("SELECT COUNT(*) FROM post_comments WHERE post_id=?", (post["id"],))
    liked_by_me = bool(db.query_one("SELECT 1 FROM post_likes WHERE post_id=? AND user_id=?", (post["id"], uid)))
    post["likesCount"] = likes_count
    post["commentsCount"] = comments_count
    post["likedByMe"] = liked_by_me
    return post

def _notify_post_owner(post_id: int, actor_uid: int, text: str, kind: str):
    post = db.find("feed_posts", id=post_id)
    if not post or post["user_id"] == actor_uid:
        return
    db.insert("notifications", {
        "user_id": post["user_id"],
        "text": text,
        "type": kind,
        "read": 0,
        "created_at": now_ms(),
        "post_id": post_id,
    })

# ============================================================
# Feed – Übersicht
# ============================================================

@bp.get("/feed")
@auth_required
def feed():
    uid = request.uid
    posts = db.query("SELECT * FROM feed_posts ORDER BY created_at DESC")
    visible = [p for p in posts if _visible_for_user(p, uid)]
    data = [_augment_post(p, uid) for p in visible]
    return jsonify(data)


@bp.get("/feed/<int:pid>")
@auth_required
def feed_one(pid: int):
    uid = request.uid
    post = db.find("feed_posts", id=pid)
    if not post:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(post, uid):
        return jsonify({"error": "forbidden"}), 403
    return jsonify(_augment_post(post, uid))


# ============================================================
# Posts eines Users
# ============================================================

@bp.get("/me/posts")
@auth_required
def my_posts():
    uid = request.uid
    posts = db.query("SELECT * FROM feed_posts WHERE user_id=? ORDER BY created_at DESC", (uid,))
    return jsonify([_augment_post(p, uid) for p in posts])


@bp.get("/users/<int:uid>/posts")
@auth_required
def user_posts(uid: int):
    viewer_id = request.uid
    posts = db.query("SELECT * FROM feed_posts WHERE user_id=? ORDER BY created_at DESC", (uid,))
    visible = [p for p in posts if _visible_for_user(p, viewer_id)]
    return jsonify([_augment_post(p, viewer_id) for p in visible])


# ============================================================
# Likes
# ============================================================

@bp.post("/feed/<int:pid>/like")
@auth_required
def like_post(pid: int):
    uid = request.uid
    post = db.find("feed_posts", id=pid)
    if not post:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(post, uid):
        return jsonify({"error": "forbidden"}), 403

    exists = db.find("post_likes", where="post_id=? AND user_id=?", params=(pid, uid))
    if not exists:
        db.insert("post_likes", {"post_id": pid, "user_id": uid, "created_at": now_ms()})
        _notify_post_owner(pid, uid, "jemand hat deinen Beitrag geliked", "feed_like")

    count = db.scalar("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (pid,))
    return jsonify({"ok": True, "likesCount": count, "likedByMe": True})


@bp.post("/feed/<int:pid>/unlike")
@auth_required
def unlike_post(pid: int):
    uid = request.uid
    post = db.find("feed_posts", id=pid)
    if not post:
        return jsonify({"error": "not_found"}), 404
    db.delete("post_likes", where="post_id=? AND user_id=?", params=(pid, uid))
    count = db.scalar("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (pid,))
    return jsonify({"ok": True, "likesCount": count, "likedByMe": False})


@bp.get("/feed/<int:pid>/likes")
@auth_required
def list_likes(pid: int):
    uid = request.uid
    post = db.find("feed_posts", id=pid)
    if not post:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(post, uid):
        return jsonify({"error": "forbidden"}), 403

    likes = db.query("""
        SELECT u.id, u.vorname, u.name, u.avatar
        FROM post_likes l
        JOIN users u ON u.id = l.user_id
        WHERE l.post_id=?
    """, (pid,))
    return jsonify(likes)


# ============================================================
# Kommentare
# ============================================================

@bp.get("/feed/<int:pid>/comments")
@auth_required
def list_comments(pid: int):
    uid = request.uid
    post = db.find("feed_posts", id=pid)
    if not post:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(post, uid):
        return jsonify({"error": "forbidden"}), 403

    comments = db.query("""
        SELECT c.*, u.vorname, u.name, u.avatar
        FROM post_comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.post_id=?
        ORDER BY c.created_at DESC
    """, (pid,))
    return jsonify(comments)


@bp.post("/feed/<int:pid>/comments")
@auth_required
def add_comment(pid: int):
    uid = request.uid
    post = db.find("feed_posts", id=pid)
    if not post:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(post, uid):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "validation", "message": "text required"}), 400

    cid = db.insert("post_comments", {
        "post_id": pid,
        "user_id": uid,
        "text": text,
        "created_at": now_ms(),
    })
    _notify_post_owner(pid, uid, "jemand hat deinen Beitrag kommentiert", "feed_comment")
    return jsonify({"id": cid, "text": text, "user_id": uid}), 201


@bp.delete("/feed/<int:pid>/comments/<int:cid>")
@auth_required
def delete_comment(pid: int, cid: int):
    uid = request.uid
    comment = db.find("post_comments", where="id=? AND post_id=?", params=(cid, pid))
    if not comment:
        return jsonify({"error": "not_found"}), 404
    if comment["user_id"] != uid:
        return jsonify({"error": "forbidden"}), 403
    db.delete("post_comments", where="id=?", params=(cid,))
    return jsonify({"ok": True})