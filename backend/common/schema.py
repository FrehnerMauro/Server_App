# backend/common/schema.py
# ============================================================
# Zentrales Datenbankschema für SQLite
# ============================================================

SCHEMA = """
PRAGMA foreign_keys = ON;

-- ============================================================
-- AUTHENTICATION
-- ============================================================
CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    device TEXT,
    expires_at INTEGER,
    created_at INTEGER NOT NULL
);

-- ============================================================
-- USERS & BLOCKING
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT,
    email TEXT UNIQUE,
    password TEXT,                
    avatar_url TEXT,
    is_admin INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    -- Billing Fields
    credits REAL DEFAULT 10.0,
    billing_status TEXT CHECK(billing_status IN ('active','suspended','cancelled')) DEFAULT 'active',
    subscription_tier TEXT CHECK(subscription_tier IN ('free','pro','enterprise')) DEFAULT 'free',
    last_billing_date INTEGER
);

CREATE TABLE IF NOT EXISTS user_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    UNIQUE(user_id, blocked_user_id)
);

-- ============================================================
-- FRIENDS & REQUESTS
-- ============================================================
CREATE TABLE IF NOT EXISTS user_friends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    friend_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT CHECK(status IN ('pending','accepted','declined','blocked')) DEFAULT 'pending',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(user_id, friend_id)
);

-- ============================================================
-- CHALLENGES
-- ============================================================
CREATE TABLE IF NOT EXISTS challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    start_at INTEGER NOT NULL,
    duration_days INTEGER NOT NULL,
    allowed_fails INTEGER DEFAULT 0,
    due_weekdays TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER
);

CREATE TABLE IF NOT EXISTS challenge_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at INTEGER NOT NULL,
    UNIQUE(challenge_id, user_id)
);

CREATE TABLE IF NOT EXISTS challenge_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    conf_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0,
    neg_streak INTEGER DEFAULT 0,
    blocked TEXT DEFAULT 'run',

    today_done INTEGER DEFAULT 0,     -- ✅ neu: ob heutige Aufgabe abgeschlossen ist
    today_pending INTEGER DEFAULT 1,  -- ✅ neu: ob heute noch offen ist

    last_computed TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE (challenge_id, user_id)
);

CREATE TABLE IF NOT EXISTS challenge_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT,
    image_url TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS challenge_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenge_id INTEGER NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    from_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT,
    status TEXT CHECK(status IN ('pending','accepted','declined')) NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL,
    updated_at INTEGER,
    UNIQUE(challenge_id, from_user_id, to_user_id)
);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    type TEXT,
    target_type TEXT,
    target_id INTEGER,
    created_at INTEGER NOT NULL,
    read INTEGER DEFAULT 0
);

-- ============================================================
-- FEED / SOCIAL
-- ============================================================
CREATE TABLE IF NOT EXISTS feed_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    image_url TEXT,
    visibility TEXT CHECK(visibility IN ('private','friends')) DEFAULT 'friends',
    created_at INTEGER NOT NULL,
    updated_at INTEGER
);

CREATE TABLE IF NOT EXISTS feed_likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES feed_posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at INTEGER NOT NULL,
    UNIQUE(post_id, user_id)
);

CREATE TABLE IF NOT EXISTS feed_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES feed_posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    comment TEXT NOT NULL,
    image_url TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER
);

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

CREATE TABLE IF NOT EXISTS feed_ad_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id INTEGER NOT NULL REFERENCES feed_ads(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT CHECK(event_type IN ('impression','click')) NOT NULL,
    created_at INTEGER NOT NULL
);

-- ============================================================
-- REPORTS (Posts, Comments, Profiles)
-- ============================================================
CREATE TABLE IF NOT EXISTS feed_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER REFERENCES feed_posts(id) ON DELETE CASCADE,
    comment_id INTEGER REFERENCES feed_comments(id) ON DELETE CASCADE,
    profile_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reason TEXT,
    status TEXT CHECK(status IN ('pending', 'reviewed', 'dismissed')) DEFAULT 'pending',
    created_at INTEGER NOT NULL,
    updated_at INTEGER,
    UNIQUE(post_id, comment_id, profile_id, reporter_id)
);

-- ============================================================
-- BILLING & EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS billing_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    created_at INTEGER NOT NULL
);

-- ============================================================
-- INDIZES (Performance)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_feed_posts_user ON feed_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_feed_comments_post ON feed_comments(post_id);
CREATE INDEX IF NOT EXISTS idx_feed_ads_status ON feed_ads(status);
CREATE INDEX IF NOT EXISTS idx_feed_ads_active_window ON feed_ads(start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_billing_events_user ON billing_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_friends_status ON user_friends(status);
CREATE INDEX IF NOT EXISTS idx_challenge_invites_status ON challenge_invites(status);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);
CREATE INDEX IF NOT EXISTS idx_challenge_members_user ON challenge_members(user_id);
CREATE INDEX IF NOT EXISTS idx_feed_reports_status ON feed_reports(status);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user ON auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
"""