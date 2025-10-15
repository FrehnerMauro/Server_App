# backend/services/store_confirm.py
from backend.common.store import state, save, now_ms, next_id

def add_challenge_confirm(challenge_id: int, user_id: int,
                          image_url: str,
                          caption: str | None,
                          visibility: str = "freunde") -> dict:
    """
    Fügt eine Challenge-Bestätigung hinzu.
    - Speichert den Log in challenge_logs[challengeId]
    - Legt denselben Post in user_posts[userId] ab (privat & freunde)
    - Wenn visibility == 'freunde', zusätzlich auch in feed_posts
    """
    st = state()
    logs_by_ch = st.setdefault("challenge_logs", {})
    lst = logs_by_ch.setdefault(str(challenge_id), [])

    new_id = next_id(st, "challenge_log_id")
    ts = now_ms()

    confirm = {
        "id": new_id,
        "challengeId": challenge_id,
        "userId": user_id,
        "action": "CONFIRM",
        "timestamp": ts,
        "visibility": visibility or "freunde",
        "evidence": {
            "imageUrl": image_url,
            "caption": caption
        },
        # neu: Interaktionsfelder
        "likes": [],
        "comments": []
    }

    # --- 1. Im Challenge-Log speichern ---
    lst.append(confirm)

    # --- 2. Im Profil des Users speichern ---
    user_posts = st.setdefault("user_posts", {})
    posts_for_user = user_posts.setdefault(str(user_id), [])
    posts_for_user.append(confirm.copy())

    # --- 3. In Feed aufnehmen, wenn öffentlich für Freunde ---
    feed = st.setdefault("feed_posts", [])
    feed.append(confirm.copy())

    save()
    return confirm