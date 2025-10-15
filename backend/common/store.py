# backend/common/store.py
# SQL-backed persistence, drop-in kompatibel mit dem alten JSON Store.
# - state() liefert das In-Memory Dict
# - save() persistiert als JSON in SQLite (state.db)
# - load() lädt aus SQLite, importiert einmalig legacy state.json falls vorhanden
# - next_id(): akzeptiert jetzt (kind) ODER (state_dict, kind) für volle Rückwärtskompatibilität.

import json
import os
import sqlite3
import time
from typing import Any, Dict, Optional, Tuple

_STATE: Dict[str, Any] = {}
_DB_PATH: Optional[str] = None


# ------------------------------------------------------------
# Helper (Zeit + IDs)
# ------------------------------------------------------------

def now_ms() -> int:
    return int(time.time() * 1000)


def _coerce_next_id_args(*args) -> Tuple[Dict[str, Any], str]:
    """
    Erlaubt beide Signaturen:
      - next_id("challenge_id")
      - next_id(state_dict, "challenge_id")
    """
    if len(args) == 1:
        kind = args[0]
        st = state()
        return st, str(kind)
    if len(args) == 2:
        maybe_st, kind = args
        if isinstance(maybe_st, dict):
            return maybe_st, str(kind)
        # Falls erster Parameter kein Dict ist, behandle es wie (kind)
        return state(), str(kind)
    raise TypeError("next_id() akzeptiert 1 oder 2 Argumente: (kind) oder (state_dict, kind)")


def next_id(*args) -> int:
    """
    Monoton steigende IDs pro Entity-Typ.
    Kompatibel zu altem Aufruf: next_id(st, "kind") UND neuem: next_id("kind").
    """
    st, kind = _coerce_next_id_args(*args)
    nid = int(st.setdefault("next_ids", {}).get(kind, 0)) + 1
    st["next_ids"][kind] = nid
    return nid


# ------------------------------------------------------------
# Default-Zustand + Migration
# ------------------------------------------------------------

def default_state() -> Dict[str, Any]:
    """
    Minimal sinnvoller Startzustand für das System.
    Hinweis: Bitte keine deutschen doppel s Regelbrüche.
    """
    return {
        "next_ids": {},
        "users": {},
        "auth": {"tokens": {}},
        "friends": [],
        "friend_requests": [],
        "challenges": {},
        "challenge_members": [],
        "challenge_logs": {},
        "challenge_chat": {},
        "challenge_invites": [],
        "challenge_stats": {},
        "notifications": [],
        "blocked": {},
        "feed_posts": [],
        "user_posts": {},
    }


def _upgrade_state(st: Dict[str, Any]) -> Dict[str, Any]:
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
    return st


# ------------------------------------------------------------
# Public State API (Dict bleibt erhalten)
# ------------------------------------------------------------

def state() -> Dict[str, Any]:
    global _STATE
    return _STATE


# ------------------------------------------------------------
# SQLite-Persistence (eine JSON-Zeile)
# ------------------------------------------------------------

def _connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, isolation_level=None)  # autocommit
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS app_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """
    )


def _read_db(con: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    cur = con.execute("SELECT state_json FROM app_state WHERE id = 1;")
    row = cur.fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def _write_db(con: sqlite3.Connection, st: Dict[str, Any]) -> None:
    payload = json.dumps(st, ensure_ascii=False, separators=(',', ':'))
    ts = now_ms()
    con.execute(
        """
        INSERT INTO app_state (id, state_json, updated_at)
        VALUES (1, ?, ?)
        ON CONFLICT(id) DO UPDATE
        SET state_json = excluded.state_json,
            updated_at = excluded.updated_at;
        """,
        (payload, ts),
    )


def load(db_path: str = "state.db", legacy_json_path: str = "state.json") -> None:
    """
    Lädt Zustand aus SQLite. Falls die DB leer ist:
      1) Import aus legacy JSON, falls vorhanden.
      2) Sonst default_state().
    Danach _upgrade_state() und sofort in DB schreiben.
    """
    global _STATE, _DB_PATH
    _DB_PATH = db_path

    con = _connect(db_path)
    _ensure_schema(con)

    st = _read_db(con)
    if st is None and os.path.exists(legacy_json_path):
        try:
            with open(legacy_json_path, "r", encoding="utf-8") as f:
                st = json.load(f)
        except Exception:
            st = None
    if st is None:
        st = default_state()

    _STATE = _upgrade_state(st)
    _write_db(con, _STATE)
    con.close()


def save() -> None:
    """
    Persistiert den aktuellen STATE in die SQLite-DB.
    """
    global _DB_PATH
    if not _DB_PATH:
        load()
        return
    con = _connect(_DB_PATH)
    _ensure_schema(con)
    _write_db(con, _STATE)
    con.close()