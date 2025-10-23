import sqlite3
import threading
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from backend.common.schema import SCHEMA  # dein globales Schema


# ------------------------------------------------------------
# Zeit- und ID-Helfer
# ------------------------------------------------------------

def now_ms() -> int:
    """Aktuelle Zeit in Millisekunden"""
    return int(time.time() * 1000)


_id_lock = threading.Lock()

def next_id(kind: str) -> int:
    """Gibt eine eindeutige fortlaufende ID für eine Kategorie zurück"""
    with _id_lock:
        with _connect("state.db") as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS next_ids (
                    name TEXT PRIMARY KEY,
                    val INTEGER DEFAULT 0
                )
            """)
            cur = con.execute("SELECT val FROM next_ids WHERE name=?", (kind,))
            row = cur.fetchone()
            if row is None:
                new_val = 1
                con.execute("INSERT INTO next_ids (name, val) VALUES (?, ?)", (kind, new_val))
            else:
                new_val = row["val"] + 1
                con.execute("UPDATE next_ids SET val=? WHERE name=?", (new_val, kind))
            con.commit()
            return new_val


# ------------------------------------------------------------
# Verbindung
# ------------------------------------------------------------

def _connect(db_path: str = "state.db") -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    con.execute("PRAGMA journal_mode = WAL;")
    return con


# ------------------------------------------------------------
# Hauptklasse
# ------------------------------------------------------------

class Database:
    def __init__(self, db_path: str = "state.db"):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """Initialisiert DB mit SCHEMA falls leer"""
        with _connect(self.db_path) as con:
            con.executescript(SCHEMA)
            con.commit()

    # --------------------------------------------------------
    # CRUD
    # --------------------------------------------------------
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
        with _connect(self.db_path) as con:
            cur = con.execute(sql, list(data.values()))
            con.commit()
            return cur.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple):
        keys = ", ".join([f"{k}=?" for k in data.keys()])
        sql = f"UPDATE {table} SET {keys} WHERE {where}"
        with _connect(self.db_path) as con:
            con.execute(sql, tuple(data.values()) + params)
            con.commit()

    def delete(self, table: str, where: str, params: tuple):
        sql = f"DELETE FROM {table} WHERE {where}"
        with _connect(self.db_path) as con:
            con.execute(sql, params)
            con.commit()

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        with _connect(self.db_path) as con:
            cur = con.execute(f"SELECT * FROM {table}")
            return [dict(row) for row in cur.fetchall()]

    # --------------------------------------------------------
    # find
    # --------------------------------------------------------
    def find(self, table: str, where: Optional[str] = None, params: Optional[tuple] = None, **kwargs):
        if kwargs:
            where = " AND ".join([f"{k}=?" for k in kwargs.keys()])
            params = tuple(kwargs.values())
        if not where:
            raise ValueError("Missing WHERE for .find()")
        with _connect(self.db_path) as con:
            cur = con.execute(f"SELECT * FROM {table} WHERE {where} LIMIT 1", params)
            row = cur.fetchone()
            return dict(row) if row else None

    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------
    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with _connect(self.db_path) as con:
            cur = con.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with _connect(self.db_path) as con:
            cur = con.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    # --------------------------------------------------------
    # Raw SQL (für Admin)
    # --------------------------------------------------------
    def raw(self, sql: str, params: tuple = ()):
        """Führt beliebige SQL-Statements aus"""
        with _connect(self.db_path) as con:
            cur = con.execute(sql, params)
            con.commit()
            return cur.rowcount

    # --------------------------------------------------------
    # Hilfsmethoden
    # --------------------------------------------------------
    def list_tables(self) -> List[str]:
        """Listet alle Tabellen in der DB"""
        with _connect(self.db_path) as con:
            cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            return [r["name"] for r in cur.fetchall()]


# ------------------------------------------------------------
# Hilfsfunktion Passwort-Hash
# ------------------------------------------------------------
def hash_pw(pw: str) -> str:
    return hashlib.sha256((pw or "").encode("utf-8")).hexdigest()