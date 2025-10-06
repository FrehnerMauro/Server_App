from flask import Blueprint, request, jsonify
from backend.common.auth import auth_required
from backend.common.store import state, save, now_ms, next_id

bp = Blueprint("feed", __name__)

# ---------------------------
# Helpers
# ---------------------------

def _is_friend(st, uid: int, other: int) -> bool:
    if uid == other:
        return True
    for fr in st.get("friends", []):
        if fr.get("status") == "accepted":
            a, b = fr.get("fromUserId"), fr.get("toUserId")
            if (a == uid and b == other) or (a == other and b == uid):
                return True
    for req in st.get("friend_requests", []):
        if req.get("status") == "accepted":
            a, b = req.get("fromUserId"), req.get("toUserId")
            if (a == uid and b == other) or (a == other and b == uid):
                return True
    return False

def _get_post(st, pid: int):
    for p in st.get("feed_posts", []):
        if p.get("id") == pid:
            return p
    return None

def _ensure_lists_on_post(post: dict):
    # likes: Liste von userIds
    if "likes" not in post or not isinstance(post["likes"], list):
        post["likes"] = []
    # comments: Liste von {id, userId, text, createdAt}
    if "comments" not in post or not isinstance(post["comments"], list):
        post["comments"] = []

def _visible_for_user(st, post: dict, uid: int) -> bool:
    owner = post.get("userId")
    vis = (post.get("visibility") or "freunde").lower()
    if owner == uid:
        return True
    if vis == "privat":
        return False
    if vis == "freunde":
        return _is_friend(st, uid, owner)
    if vis == "public":
        return True
    return False

def _augment(post: dict, uid: int) -> dict:
    # reiche Post um likedByMe, likesCount, commentsCount an (ohne den Original-Storage zu veraendern)
    likes = post.get("likes") or []
    comments = post.get("comments") or []
    out = dict(post)
    out["likesCount"] = len(likes)
    out["commentsCount"] = len(comments)
    out["likedByMe"] = uid in likes
    return out

def _display_name(uid: int) -> str:
    """Zeigt hübschen Namen für einen User."""
    st = state()
    u = st.get("users", {}).get(str(uid)) or {}
    vor = (u.get("vorname") or "").strip()
    nam = (u.get("name") or "").strip()
    full = " ".join([p for p in [vor, nam] if p])
    return full if full else (nam if nam else f"User {uid}")

def _notify_post_owner(post: dict, actor_uid: int, text: str, kind: str):
    """
    Benachrichtigt den Besitzer des Posts (falls != actor) mit einem simplen Text.
    kind: "feed_comment" | "feed_like"
    """
    st = state()
    owner_uid = int(post.get("userId"))
    if owner_uid == actor_uid:
        return
    notif = {
        "id": next_id(st, "notification_id"),
        "userId": owner_uid,
        "text": text,                # z. B. "Max Mustermann hat deinen Beitrag kommentiert"
        "read": False,
        "createdAt": now_ms(),
        "type": kind,
        "postId": int(post.get("id") or 0),
    }
    # Optional: Falls der Post aus einer Challenge stammt, mitgeben (falls vorhanden)
    if "challengeId" in post and post.get("challengeId") is not None:
        notif["challengeId"] = int(post["challengeId"])

    st.setdefault("notifications", []).append(notif)
    save()

# ---------------------------
# Feed: Liste & Einzelpost
# ---------------------------

@bp.get("/feed")
@auth_required
def feed():
    st = state()
    uid = request.uid
    posts = list(st.get("feed_posts", []))

    visible = [p for p in posts if _visible_for_user(st, p, uid)]
    visible.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # augment
    data = [_augment(p, uid) for p in visible]
    return jsonify(data)

@bp.get("/feed/<int:pid>")
@auth_required
def feed_one(pid: int):
    st = state()
    uid = request.uid
    p = _get_post(st, pid)
    if not p:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(st, p, uid):
        return jsonify({"error": "forbidden"}), 403
    return jsonify(_augment(p, uid))

# ---------------------------
# Profil-Posts
# ---------------------------

@bp.get("/me/posts")
@auth_required
def my_posts():
    st = state()
    uid = request.uid
    posts = [p for p in st.get("feed_posts", []) if p.get("userId") == uid]
    posts.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return jsonify([_augment(p, uid) for p in posts])

@bp.get("/users/<int:uid>/posts")
@auth_required
def user_posts(uid: int):
    st = state()
    me = request.uid
    posts = [p for p in st.get("feed_posts", []) if p.get("userId") == uid]
    visible = [p for p in posts if _visible_for_user(st, p, me)]
    visible.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return jsonify([_augment(p, me) for p in visible])

# ---------------------------
# Likes
# ---------------------------

@bp.post("/feed/<int:pid>/like")
@auth_required
def like_post(pid: int):
    st = state()
    uid = request.uid
    p = _get_post(st, pid)
    if not p:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(st, p, uid):
        return jsonify({"error": "forbidden"}), 403

    _ensure_lists_on_post(p)
    if uid not in p["likes"]:
        p["likes"].append(uid)
        save()

        # 🔔 Benachrichtigung an den Besitzer
        actor_name = _display_name(uid)
        _notify_post_owner(
            p,
            actor_uid=uid,
            text=f"{actor_name} hat deinen Beitrag geliked",
            kind="feed_like",
        )

    return jsonify({"ok": True, "likesCount": len(p["likes"]), "likedByMe": True})

@bp.post("/feed/<int:pid>/unlike")
@auth_required
def unlike_post(pid: int):
    st = state()
    uid = request.uid
    p = _get_post(st, pid)
    if not p:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(st, p, uid):
        return jsonify({"error": "forbidden"}), 403

    _ensure_lists_on_post(p)
    if uid in p["likes"]:
        p["likes"] = [u for u in p["likes"] if u != uid]
        save()
    return jsonify({"ok": True, "likesCount": len(p["likes"]), "likedByMe": False})

@bp.get("/feed/<int:pid>/likes")
@auth_required
def list_likes(pid: int):
    st = state()
    uid = request.uid
    p = _get_post(st, pid)
    if not p:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(st, p, uid):
        return jsonify({"error": "forbidden"}), 403

    _ensure_lists_on_post(p)
    users = st.get("users", {})
    result = []
    for user_id in p["likes"]:
        u = users.get(str(user_id))
        if u:
            result.append({
                "id": u["id"],
                "vorname": u.get("vorname"),
                "name": u.get("name") or u.get("nachname") or "",
                "avatar": u.get("avatar")
            })
        else:
            result.append({"id": user_id})
    return jsonify(result)

# ---------------------------
# Kommentare
# ---------------------------

@bp.get("/feed/<int:pid>/comments")
@auth_required
def list_comments(pid: int):
    st = state()
    uid = request.uid
    p = _get_post(st, pid)
    if not p:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(st, p, uid):
        return jsonify({"error": "forbidden"}), 403

    _ensure_lists_on_post(p)
    # neueste zuerst
    comments = sorted(p["comments"], key=lambda c: c.get("createdAt", 0), reverse=True)
    return jsonify(comments)

@bp.post("/feed/<int:pid>/comments")
@auth_required
def add_comment(pid: int):
    st = state()
    uid = request.uid
    p = _get_post(st, pid)
    if not p:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(st, p, uid):
        return jsonify({"error": "forbidden"}), 403

    data = (request.get_json(silent=True) or {})
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "validation", "details": "text required"}), 400

    _ensure_lists_on_post(p)
    com = {
        "id": next_id(st, "comment_id"),
        "userId": uid,
        "text": text,
        "createdAt": now_ms()
    }
    p["comments"].append(com)
    save()

    # 🔔 Benachrichtigung an den Besitzer
    actor_name = _display_name(uid)
    _notify_post_owner(
        p,
        actor_uid=uid,
        text=f"{actor_name} hat deinen Beitrag kommentiert",
        kind="feed_comment",
    )

    return jsonify(com), 201

@bp.delete("/feed/<int:pid>/comments/<int:cid>")
@auth_required
def delete_comment(pid: int, cid: int):
    st = state()
    uid = request.uid
    p = _get_post(st, pid)
    if not p:
        return jsonify({"error": "not_found"}), 404
    if not _visible_for_user(st, p, uid):
        return jsonify({"error": "forbidden"}), 403

    _ensure_lists_on_post(p)
    # nur eigener Kommentar loeschbar
    found = None
    for c in p["comments"]:
        if c.get("id") == cid:
            found = c
            break
    if not found:
        return jsonify({"error": "not_found"}), 404
    if found.get("userId") != uid:
        return jsonify({"error": "forbidden"}), 403

    p["comments"] = [c for c in p["comments"] if c.get("id") != cid]
    save()
    return jsonify({"ok": True})