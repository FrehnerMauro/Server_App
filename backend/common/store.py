# backend/common/store.py
import json
import os
import time
from typing import Any, Dict

_STATE: Dict[str, Any] = {}

# ------------------------------------------------------------
# Default-Zustand + Migration
# ------------------------------------------------------------

def default_state() -> Dict[str, Any]:
    """
    Minimal sinnvoller Startzustand für das System.
    - next_ids: Zähler pro Entität
    - users/auth: einfache Nutzerverwaltung (Tokens)
    - challenges + Mitglieder + Logs/Chat
    - friends / friend_requests
    - notifications
    - blocked
    - challenge_stats: Platz für Tagesstatus etc.
    - feed_posts: Liste aller Feed-Posts (nur Sichtbarkeit 'freunde' gehört in den Feed)
    - user_posts: pro Benutzer alle seine Posts (inkl. 'privat' und 'freunde')
    """
    now = now_ms()
    return {
        "next_ids": {},

        # Benutzer & Auth
        "users": {},                           # "1": {id, vorname, name, email, avatar}
        "auth": {"tokens": {}},                # token -> userId(int)

        # Freundschaften
        "friends": [],                         # {id, fromUserId, toUserId, status}
        "friend_requests": [],                 # {id, fromUserId, toUserId, message, status, createdAt}

        # Challenges
        "challenges": {},                      # "49": {...}
        "challenge_members": [],               # {challengeId, userId}
        "challenge_logs": {},                  # "49": [ {id, action, evidence{imageUrl,caption}, visibility, timestamp, userId}, ... ]
        "challenge_chat": {},                  # "49": [ {id, userId, text, createdAt}, ... ]
        "challenge_invites": [],               # {id, challengeId, fromUserId, toUserId, message, status, createdAt}
        "challenge_stats": {},                 # "49": {"today": {...}, ...}

        # Benachrichtigungen
        "notifications": [],                   # {id, userId, text, read, createdAt}

        # Blockierungen je Challenge (optional)
        "blocked": {},                         # "49": [userId,...]

        # Neu: Feed & Profil-Posts
        "feed_posts": [],                      # [{id, userId, challengeId, action, evidence{...}, visibility, timestamp, likes:set/list, comments:[...]}]
        "user_posts": {},                      # "1": [ {id, ... wie oben ...}, ... ]
    }

def _upgrade_state(st: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sorgt dafür, dass auch bei älteren gespeicherten States alle benötigten
    Schlüssel existieren. Verändert st *in place* und gibt es zurück.
    """
    # Grundcontainer
    st.setdefault("next_ids", {})
    st.setdefault("users", {})
    st.setdefault("auth", {}).setdefault("tokens", {})

    st.setdefault("friends", [])
    st.setdefault("friend_requests", [])

    st.setdefault("challenges", {})
    st.setdefault("challenge_members", [])
    st.setdefault("challenge_logs", {})
    st.setdefault("challenge_chat", {})
    st.setdefault("challenge_invites", [])
    st.setdefault("challenge_stats", {})

    st.setdefault("notifications", [])
    st.setdefault("blocked", {})

    # Neu: Feed & Profile-Posts
    st.setdefault("feed_posts", [])
    st.setdefault("user_posts", {})

    # Typabsicherung für Strukturen, die Dictionaries pro Challenge erwarten
    if not isinstance(st.get("challenge_logs"), dict):
        st["challenge_logs"] = {}
    if not isinstance(st.get("challenge_chat"), dict):
        st["challenge_chat"] = {}
    if not isinstance(st.get("blocked"), dict):
        st["blocked"] = {}
    if not isinstance(st.get("challenge_stats"), dict):
        st["challenge_stats"] = {}

    # Typabsicherung für neue Strukturen
    if not isinstance(st.get("feed_posts"), list):
        st["feed_posts"] = []
    if not isinstance(st.get("user_posts"), dict):
        st["user_posts"] = {}

    return st

# ------------------------------------------------------------
# Öffentliche State-API
# ------------------------------------------------------------

def state() -> Dict[str, Any]:
    global _STATE
    return _STATE

def load(path: str = "state.json"):
    """
    Lädt den Zustand von Platte oder legt einen Default an.
    Führt anschließend eine Migration (_upgrade_state) durch, damit alle Keys existieren.
    """
    global _STATE
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                _STATE = json.load(f)
            except Exception:
                # Fallback: kaputte Datei -> neu initialisieren, aber alte Datei sichern
                try:
                    os.rename(path, path + ".broken")
                except Exception:
                    pass
                _STATE = default_state()
                save(path)
    else:
        _STATE = default_state()
        save(path)

    _upgrade_state(_STATE)
    # Optional: sofortige Persistenz nach Migration
    save(path)

def save(path: str = "state.json"):
    global _STATE
    # sets in feed_posts (likes) ggf. in Listen serialisieren
    serializable = _prepare_for_json(_STATE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)

def now_ms() -> int:
    return int(time.time() * 1000)

def next_id(st: Dict[str, Any], key: str) -> int:
    """
    Erhöht einen nummerischen Zähler-Namespace (z. B. 'challenge_id', 'log_id', 'feed_post_id' ...).
    """
    n = st["next_ids"].get(key, 1)
    st["next_ids"][key] = n + 1
    return n

# ------------------------------------------------------------
# JSON-Helfer (für persistierbare Strukturen)
# ------------------------------------------------------------

def _prepare_for_json(obj: Any) -> Any:
    """
    Konvertiert Strukturen so, dass sie JSON-serialisierbar sind.
    - sets -> lists
    - rekursiv für dicts/lists
    """
    if isinstance(obj, dict):
        return {k: _prepare_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_prepare_for_json(v) for v in obj]
    if isinstance(obj, set):
        return sorted(list(obj))
    return obj


def add_challenge_user_log(challenge_id: int,
                           member_id: int,
                           conf_count: int,
                           fail_count: int,
                           streak: int,
                           blocked: bool,
                           state: str,
                           ts: int | None = None) -> dict:
    """
    Speichert einen User-Log-Eintrag für eine Challenge.
    """
    st = state()
    logs_for_challenge = st.setdefault("challenge_user_logs", {})
    logs_for_user = logs_for_challenge.setdefault(str(challenge_id), {}).setdefault(str(member_id), [])

    entry = {
        "id": next_id(st, "challenge_user_log_id"),
        "challenge_id": challenge_id,
        "member_id": member_id,
        "conf_count": conf_count,
        "fail_count": fail_count,
        "streak": streak,
        "blocked": blocked,
        "state": state,
        "timestamp": ts or now_ms()
    }

    logs_for_user.append(entry)
    save()
    return entry

