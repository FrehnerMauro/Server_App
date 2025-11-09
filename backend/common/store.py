import os
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import psycopg2.extras

# ------------------------------------------------------------
# Zeit-Helper
# ------------------------------------------------------------
def now_ms() -> int:
    return int(time.time() * 1000)

# ------------------------------------------------------------
# DSN / Verbindung
# ------------------------------------------------------------
def _resolve_dsn(passed: Optional[str]) -> str:
    # Nur Postgres. Nimmt erst "passed", dann $DB_DSN, sonst Default.
    if passed and passed.startswith("postgresql://"):
        return passed
    env_dsn = os.getenv("DB_DSN")
    if env_dsn and env_dsn.startswith("postgresql://"):
        return env_dsn
    return "postgresql://mauro:1234@localhost:5432/socialhabit"

def _connect(dsn: str):
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)

# ------------------------------------------------------------
# DB-API (nur Postgres)
# ------------------------------------------------------------
class Database:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = _resolve_dsn(dsn)
        # kein SCHEMA-Init: DB wurde migriert

    # Transaktion
    def begin_transaction(self):
        con = _connect(self.dsn)
        cur = con.cursor()
        return con, cur

    def commit(self, con):
        if con:
            con.commit()
            con.close()

    def rollback(self, con):
        if con:
            con.rollback()
            con.close()

    # Fortlaufende IDs (pro "kind"), rein in PG
    def _ensure_next_ids(self, cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS next_ids (
                name TEXT PRIMARY KEY,
                val BIGINT NOT NULL DEFAULT 0
            );
        """)

    def next_id(self, kind: str) -> int:
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                self._ensure_next_ids(cur)
                cur.execute("SELECT val FROM next_ids WHERE name=%s FOR UPDATE", (kind,))
                row = cur.fetchone()
                if row is None:
                    new_val = 1
                    cur.execute("INSERT INTO next_ids (name, val) VALUES (%s, %s)", (kind, new_val))
                else:
                    new_val = int(row["val"]) + 1
                    cur.execute("UPDATE next_ids SET val=%s WHERE name=%s", (new_val, kind))
            con.commit()
            return new_val

    # CRUD
    def insert(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO {table} ({keys}) VALUES ({placeholders}) RETURNING id"
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute(sql, list(data.values()))
                row = cur.fetchone()
            con.commit()
            return row["id"] if row and "id" in row else None

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple):
        sets = ", ".join([f"{k}=%s" for k in data.keys()])
        sql = f"UPDATE {table} SET {sets} WHERE {where}"
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute(sql, tuple(data.values()) + params)
            con.commit()

    def delete(self, table: str, where: str, params: tuple):
        sql = f"DELETE FROM {table} WHERE {where}"
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute(sql, params)
            con.commit()

    def get_all(self, table: str) -> List[Dict[str, Any]]:
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute(f"SELECT * FROM {table}")
                return cur.fetchall()

    # Query
    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                return dict(row) if row else None

    # Utilities
    def raw(self, sql: str, params: tuple = ()):
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute(sql, params)
            con.commit()

    def list_tables(self) -> List[str]:
        with _connect(self.dsn) as con:
            with con.cursor() as cur:
                cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public';")
                return [r["tablename"] for r in cur.fetchall()]

    def scalar(self, sql: str, params: tuple = ()):
        row = self.query_one(sql, params)
        if not row:
            return None
        return next(iter(row.values()))
    


# ------------------------------------------------------------
# Passwort-Hash
# ------------------------------------------------------------
def hash_pw(pw: str) -> str:
    return hashlib.sha256((pw or "").encode("utf-8")).hexdigest()

# ------------------------------------------------------------
# Kompat-Wrappers (falls alter Code next_id als freie Funktion importiert)
# ------------------------------------------------------------
_db_singleton = Database()  # nutzt DB_DSN oder Default

def next_id(kind: str) -> int:
    return _db_singleton.next_id(kind)