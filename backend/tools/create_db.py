#!/usr/bin/env python3
"""
Tool zum Erstellen einer neuen relationalen state.db fuer die Server-App.
Erzeugt alle Tabellen (ohne JSON) und legt optional ein paar Testdaten an.
"""

import sqlite3
import os
import time

DB_PATH = os.path.abspath("state.db")

def now_ms() -> int:
    """Aktuelle Zeit in Millisekunden"""
    return int(time.time() * 1000)

def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")
    return con

def create_schema(con: sqlite3.Connection):
    """Erstellt das komplette relationale Schema"""
    cur = con.cursor()

    # USERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        display_name TEXT,
        email TEXT UNIQUE,
        avatar_url TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
    );
    """)

    # AUTH
    cur.execute("""
    CREATE TABLE IF NOT EXISTS auth (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        password_hash TEXT,
        token TEXT,
        token_expires INTEGER
    );
    """)

    # FRIENDSHIPS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS friends (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        friend_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL,
        PRIMARY KEY (user_id, friend_id)
    );
    """)

    # FRIEND REQUESTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS friend_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        to_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL,
        status TEXT CHECK(status IN ('pending','accepted','declined')) NOT NULL DEFAULT 'pending'
    );
    """)

    # CHALLENGES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        description TEXT,
        start_at INTEGER NOT NULL,
        duration_days INTEGER NOT NULL,
        allowed_fails INTEGER DEFAULT 0,
        due_weekdays TEXT,
        created_at INTEGER NOT NULL
    );
    """)

    # CHALLENGE MEMBERS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challenge_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        joined_at INTEGER NOT NULL
    );
    """)

    # CHALLENGE LOGS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challenge_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        timestamp INTEGER NOT NULL,
        image_url TEXT,
        caption TEXT,
        visibility TEXT CHECK(visibility IN ('privat','freunde','oeffentlich')) DEFAULT 'freunde'
    );
    """)

    # CHALLENGE INVITES
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challenge_invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
        from_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        to_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at INTEGER NOT NULL,
        status TEXT CHECK(status IN ('pending','accepted','declined')) DEFAULT 'pending'
    );
    """)

    # CHALLENGE STATS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS challenge_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        conf_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        neg_streak INTEGER DEFAULT 0,
        blocked TEXT CHECK(blocked IN ('none','run','gesperrt','completed')) DEFAULT 'none',
        updated_at INTEGER NOT NULL
    );
    """)

    # NOTIFICATIONS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        message TEXT NOT NULL,
        type TEXT,
        created_at INTEGER NOT NULL,
        read INTEGER DEFAULT 0
    );
    """)

    # FEED POSTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feed_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        image_url TEXT,
        caption TEXT,
        visibility TEXT CHECK(visibility IN ('private','friends','privat','freunde')) DEFAULT 'friends',
        created_at INTEGER NOT NULL
    );
    """)

    # FEED ADS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feed_ads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_url TEXT NOT NULL,
        click_url TEXT,
        headline TEXT,
        body TEXT,
        cta_label TEXT,
        status TEXT CHECK(status IN ('draft','active','paused')) DEFAULT 'draft',
        start_at INTEGER,
        end_at INTEGER,
        weight INTEGER DEFAULT 1,
        audience_filter TEXT,
        impressions INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        created_at INTEGER NOT NULL,
        updated_at INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feed_ad_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_id INTEGER NOT NULL REFERENCES feed_ads(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        event_type TEXT CHECK(event_type IN ('impression','click')) NOT NULL,
        created_at INTEGER NOT NULL
    );
    """)

    # USER POSTS
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        challenge_id INTEGER REFERENCES challenges(id) ON DELETE SET NULL,
        image_url TEXT,
        caption TEXT,
        created_at INTEGER NOT NULL
    );
    """)

    con.commit()

def insert_sample_data(con: sqlite3.Connection):
    """Fuegt ein paar Demo-Daten hinzu"""
    now = now_ms()
    cur = con.cursor()

    # Beispiel-User
    cur.execute("INSERT INTO users (username, display_name, email, created_at, updated_at) VALUES (?,?,?,?,?)",
                ("mauro", "Mauro F.", "mauro@example.com", now, now))
    uid = cur.lastrowid

    cur.execute("INSERT INTO users (username, display_name, email, created_at, updated_at) VALUES (?,?,?,?,?)",
                ("anna", "Anna B.", "anna@example.com", now, now))
    uid2 = cur.lastrowid

    # Freundschaft
    cur.execute("INSERT INTO friends (user_id, friend_id, created_at) VALUES (?,?,?)", (uid, uid2, now))
    cur.execute("INSERT INTO friends (user_id, friend_id, created_at) VALUES (?,?,?)", (uid2, uid, now))

    # Challenge
    cur.execute("INSERT INTO challenges (creator_id, title, description, start_at, duration_days, created_at) VALUES (?,?,?,?,?,?)",
                (uid, "10k Steps", "Jeden Tag 10'000 Schritte", now, 30, now))
    cid = cur.lastrowid

    # Challenge-Member
    cur.execute("INSERT INTO challenge_members (challenge_id, user_id, joined_at) VALUES (?,?,?)", (cid, uid, now))
    cur.execute("INSERT INTO challenge_members (challenge_id, user_id, joined_at) VALUES (?,?,?)", (cid, uid2, now))

    # Challenge-Log
    cur.execute("INSERT INTO challenge_logs (challenge_id, user_id, timestamp, image_url, caption, visibility) VALUES (?,?,?,?,?,?)",
                (cid, uid, now, "https://example.com/img1.jpg", "Erster Tag geschafft!", "friends"))

    # Feed-Post
    cur.execute("INSERT INTO feed_posts (user_id, image_url, caption, created_at, visibility) VALUES (?,?,?,?,?)",
                (uid, "https://example.com/post1.jpg", "Challenge gestartet!", now, "friends"))

    con.commit()

def main():
    if os.path.exists(DB_PATH):
        print(f"⚠️  Alte DB {DB_PATH} existiert – wird neu erstellt...")
        os.remove(DB_PATH)
    con = connect()
    create_schema(con)
    insert_sample_data(con)
    con.close()
    print(f"✅ Neue relationale state.db erstellt unter {DB_PATH}")

if __name__ == "__main__":
    main()