# backend/common/store.py
import json
import os
import time
from typing import Any, Dict, Optional

_STATE: Dict[str, Any] = {}
_SHARDS: Dict[str, str] = {}          # shard_key -> file path
_DIR: str = "state"                   # basisordner fuer sharded dateien
_DIR_READY: bool = False
_DIR_CREATED: bool = False
_DIRTY: Dict[str, bool] = {}          # shard_key -> dirty flag

# ------------------------------------------------------------
# Default-Zustand + Migration
# ------------------------------------------------------------

def now_ms() -> int:
    return int(time.time() * 1000)

def default_state() -> Dict[str, Any]:
    """
    Minimal sinnvoller Startzustand fuer das System.
    """
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
        "challenge_logs": {},                  # "49": [ {...}, ... ]
        "challenge_chat": {},                  # "49": [ {...}, ... ]
        "challenge_invites": [],               # {id,...}
        "challenge_stats": {},                 # "49": {"today": {...}, ...}

        # Benachrichtigungen
        "notifications": [],

        # Blockierungen je Challenge (optional)
        "blocked": {},

        # Feed & Profil-Posts
        "feed_posts": [],
        "user_posts": {},

        # zusaetzlich: per-user verlaufslogs
        "challenge_user_logs": {},            # "challengeId": {"userId":[...]}
    }

def _upgrade_state(st: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migration: sorgt dafuer, dass alle benoetigten Keys existieren.
    """
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

    st.setdefault("feed_posts", [])
    st.setdefault("user_posts", {})

    st.setdefault("challenge_user_logs", {})

    # Typabsicherung
    for key, typ in [
        ("challenge_logs", dict),
        ("challenge_chat", dict),
        ("blocked", dict),
        ("challenge_stats", dict),
        ("user_posts", dict),
        ("feed_posts", list),
        ("friends", list),
        ("friend_requests", list),
        ("challenge_members", list),
        ("challenge_invites", list),
        ("users", dict),
        ("auth", dict),
        ("next_ids", dict),
        ("notifications", list),
        ("challenge_user_logs", dict),
        ("challenges", dict),
    ]:
        if not isinstance(st.get(key), typ):
            st[key] = typ() if typ is not list else []

    return st

# ------------------------------------------------------------
# JSON-Helpers
# ------------------------------------------------------------

def _prepare_for_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _prepare_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_prepare_for_json(v) for v in obj]
    if isinstance(obj, set):
        return sorted(list(obj))
    return obj

def _atomic_write(path: str, content: Dict[str, Any]):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# ------------------------------------------------------------
# Sharding-Config
# ------------------------------------------------------------

def _ensure_dir_ready(data_dir: str):
    global _DIR, _DIR_READY, _DIR_CREATED
    if _DIR_READY and _DIR == data_dir:
        return
    _DIR = data_dir
    if not os.path.exists(_DIR):
        os.makedirs(_DIR, exist_ok=True)
        _DIR_CREATED = True
    _DIR_READY = True

def _init_shards():
    global _SHARDS, _DIRTY
    # shard key -> filename
    mapping = {
        "next_ids": "next_ids.json",
        "users": "users.json",
        "auth": "auth.json",
        "friends": "friends.json",
        "friend_requests": "friend_requests.json",
        "challenges": "challenges.json",
        "challenge_members": "challenge_members.json",
        "challenge_logs": "challenge_logs.json",
        "challenge_chat": "challenge_chat.json",
        "challenge_invites": "challenge_invites.json",
        "challenge_stats": "challenge_stats.json",
        "notifications": "notifications.json",
        "blocked": "blocked.json",
        "feed_posts": "feed_posts.json",
        "user_posts": "user_posts.json",
        "challenge_user_logs": "challenge_user_logs.json",
    }
    _SHARDS = {k: os.path.join(_DIR, fname) for k, fname in mapping.items()}
    _DIRTY = {k: False for k in mapping.keys()}

def _mark_dirty(shard_key: str):
    if shard_key in _DIRTY:
        _DIRTY[shard_key] = True

# ------------------------------------------------------------
# Oeffentliche State-API (kompatibel)
# ------------------------------------------------------------

def state() -> Dict[str, Any]:
    global _STATE
    return _STATE

def load(path: str = "state.json"):
    """
    Legacy-Loader: eine einzige Datei. Migriert in Memory, speichert dann wieder
    in dieser Einzeldatei. (Rueckwaerts kompatibel)
    """
    global _STATE
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                _STATE = json.load(f)
            except Exception:
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
    save(path)

def save(path: str = "state.json"):
    """
    Legacy-Save: eine einzige Datei.
    """
    global _STATE
    serializable = _prepare_for_json(_STATE)
    _atomic_write(path, serializable)

# ------------------------------------------------------------
# Sharded Laden / Speichern
# ------------------------------------------------------------

def load_sharded(data_dir: str = "state", fallback_legacy_path: str = "state.json"):
    """
    Laedt aus mehreren Dateien in data_dir. Falls keine Shards existieren,
    aber eine alte state.json vorhanden ist, wird diese migriert und
    als Shards gespeichert.
    """
    global _STATE
    _ensure_dir_ready(data_dir)
    _init_shards()

    # Pruefen, ob bereits Shards existieren
    any_shard_exists = any(os.path.exists(p) for p in _SHARDS.values())

    if not any_shard_exists and os.path.exists(fallback_legacy_path):
        # Legacy laden und in Shards verteilen
        load(fallback_legacy_path)
        _upgrade_state(_STATE)
        save_all_shards_from_state()
        return

    # Falls keine Shards und keine Legacy: frisch initialisieren
    if not any_shard_exists:
        _STATE = default_state()
        save_all_shards_from_state()
        return

    # Shards laden: fehlende werden mit Defaults ergänzt
    base = default_state()
    loaded: Dict[str, Any] = {}
    for key, path in _SHARDS.items():
        data = _load_json(path)
        loaded[key] = data if data is not None else base.get(key)

    # einen zusammengesetzten STATE bauen
    _STATE = {
        "next_ids": loaded.get("next_ids") or {},
        "users": loaded.get("users") or {},
        "auth": loaded.get("auth") or {"tokens": {}},
        "friends": loaded.get("friends") or [],
        "friend_requests": loaded.get("friend_requests") or [],
        "challenges": loaded.get("challenges") or {},
        "challenge_members": loaded.get("challenge_members") or [],
        "challenge_logs": loaded.get("challenge_logs") or {},
        "challenge_chat": loaded.get("challenge_chat") or {},
        "challenge_invites": loaded.get("challenge_invites") or [],
        "challenge_stats": loaded.get("challenge_stats") or {},
        "notifications": loaded.get("notifications") or [],
        "blocked": loaded.get("blocked") or {},
        "feed_posts": loaded.get("feed_posts") or [],
        "user_posts": loaded.get("user_posts") or {},
        "challenge_user_logs": loaded.get("challenge_user_logs") or {},
    }

    _upgrade_state(_STATE)

def save_all_shards_from_state():
    """
    Schreibt alle Shards (unabhaengig von Dirty-Flags).
    """
    _ensure_dir_ready(_DIR)
    _init_shards()
    for shard_key, path in _SHARDS.items():
        content = _prepare_for_json(_STATE.get(shard_key))
        if content is None:
            # falls Key fehlt, speichere leere Struktur aus default_state
            content = default_state().get(shard_key)
        _atomic_write(path, content)
        _DIRTY[shard_key] = False

def save_shard(shard_key: str):
    """
    Schreibt einen einzelnen Shard. Setzt Dirty-Flag zurueck.
    """
    if shard_key not in _SHARDS:
        raise KeyError(f"Unbekannter Shard: {shard_key}")
    path = _SHARDS[shard_key]
    content = _prepare_for_json(_STATE.get(shard_key))
    if content is None:
        content = default_state().get(shard_key)
    _atomic_write(path, content)
    _DIRTY[shard_key] = False

def save_all_dirty():
    """
    Schreibt nur die Shards, deren Dirty-Flag gesetzt ist.
    """
    for k, is_dirty in _DIRTY.items():
        if is_dirty:
            save_shard(k)

# ------------------------------------------------------------
# Counter / IDs
# ------------------------------------------------------------

def next_id(st: Dict[str, Any], key: str) -> int:
    n = st["next_ids"].get(key, 1)
    st["next_ids"][key] = n + 1
    _mark_dirty("next_ids")
    return n

# ------------------------------------------------------------
# Convenience: Mutations mit Dirty-Marking
# ------------------------------------------------------------

def set_user(user_id: int, obj: Dict[str, Any]):
    st = state()
    st["users"][str(user_id)] = obj
    _mark_dirty("users")

def add_friendship(entry: Dict[str, Any]):
    st = state()
    st["friends"].append(entry)
    _mark_dirty("friends")

def add_friend_request(entry: Dict[str, Any]):
    st = state()
    st["friend_requests"].append(entry)
    _mark_dirty("friend_requests")

def set_challenge(cid: int, obj: Dict[str, Any]):
    st = state()
    st["challenges"][str(cid)] = obj
    _mark_dirty("challenges")

def add_challenge_member(cid: int, uid: int):
    st = state()
    st["challenge_members"].append({"challengeId": cid, "userId": uid})
    _mark_dirty("challenge_members")

def append_challenge_log(cid: int, entry: Dict[str, Any]):
    st = state()
    st.setdefault("challenge_logs", {}).setdefault(str(cid), []).append(entry)
    _mark_dirty("challenge_logs")

def set_challenge_logs(cid: int, lst):
    st = state()
    st.setdefault("challenge_logs", {})[str(cid)] = lst
    _mark_dirty("challenge_logs")

def append_challenge_chat(cid: int, entry: Dict[str, Any]):
    st = state()
    st.setdefault("challenge_chat", {}).setdefault(str(cid), []).append(entry)
    _mark_dirty("challenge_chat")

def set_challenge_stats(cid: int, obj: Dict[str, Any]):
    st = state()
    st.setdefault("challenge_stats", {})[str(cid)] = obj
    _mark_dirty("challenge_stats")

def add_notification(entry: Dict[str, Any]):
    st = state()
    st["notifications"].append(entry)
    _mark_dirty("notifications")

def set_blocked_list(cid: int, lst):
    st = state()
    st.setdefault("blocked", {})[str(cid)] = lst
    _mark_dirty("blocked")

def add_feed_post(entry: Dict[str, Any]):
    st = state()
    st["feed_posts"].append(entry)
    _mark_dirty("feed_posts")

def add_user_post(uid: int, entry: Dict[str, Any]):
    st = state()
    st.setdefault("user_posts", {}).setdefault(str(uid), []).append(entry)
    _mark_dirty("user_posts")

def set_auth_token(token: str, user_id: int):
    st = state()
    st.setdefault("auth", {}).setdefault("tokens", {})[token] = user_id
    _mark_dirty("auth")

# ------------------------------------------------------------
# Vorhandener Helper (angepasst: dirty-marking + shard-save)
# ------------------------------------------------------------

def add_challenge_user_log(challenge_id: int,
                           member_id: int,
                           conf_count: int,
                           fail_count: int,
                           streak: int,
                           blocked: bool,
                           state_value: str,
                           ts: Optional[int] = None) -> dict:
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
        "state": state_value,
        "timestamp": ts or now_ms()
    }

    logs_for_user.append(entry)
    _mark_dirty("challenge_user_logs")
    return entry