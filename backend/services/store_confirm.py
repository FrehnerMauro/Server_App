from backend.common.store import Database, now_ms
from typing import Optional

db = Database("postgresql://mauro:1234@localhost:5432/socialhabit")

def add_challenge_confirm(
    challenge_id: int,
    user_id: int,
    image_url: str,
    caption: Optional[str],
    visibility: str = "freunde"
) -> dict:
    """
    Fügt eine Challenge-Bestätigung hinzu:
      1️⃣ Speichert Log in challenge_logs
      2️⃣ Legt denselben Eintrag in user_posts ab
      3️⃣ Falls visibility ∈ ('freunde', 'public'), auch in feed_posts
    """

    ts = now_ms()
    visibility = (visibility or "freunde").lower()
    caption = caption or None

    # 1️⃣ Challenge-Log
    log_id = db.insert("challenge_logs", {
        "challenge_id": challenge_id,
        "user_id": user_id,
        "action": "CONFIRM",
        "timestamp": ts,
        "visibility": visibility,
        "image_url": image_url,
        "caption": caption
    })

    confirm = {
        "id": log_id,
        "challengeId": challenge_id,
        "userId": user_id,
        "action": "CONFIRM",
        "timestamp": ts,
        "visibility": visibility,
        "imageUrl": image_url,
        "caption": caption,
    }

    # 2️⃣ User-Posts
    db.insert("user_posts", {
        "user_id": user_id,
        "challenge_id": challenge_id,
        "image_url": image_url,
        "caption": caption,
        "visibility": visibility,
        "created_at": ts
    })

    # 3️⃣ Feed-Posts (nur bei 'freunde' oder 'public')
    if visibility in ("freunde", "public"):
        db.insert("feed_posts", {
            "user_id": user_id,
            "challenge_id": challenge_id,
            "image_url": image_url,
            "caption": caption,
            "visibility": visibility,
            "created_at": ts
        })

    return confirm