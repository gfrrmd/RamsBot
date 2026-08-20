from datetime import datetime, timedelta

import psycopg2

from config import DATABASE_URL


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            created_at TEXT
        )
    """)
    c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_used INTEGER DEFAULT 0")
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            user_id BIGINT PRIMARY KEY,
            api_id BIGINT NOT NULL,
            api_hash TEXT NOT NULL,
            string_session TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id BIGINT PRIMARY KEY,
            plan TEXT DEFAULT 'vip',
            paid_at TEXT,
            expired_at TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY,
            auto_dl_view_once INTEGER DEFAULT 0
        )
    """)
    c.execute("ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS auto_dl_view_once INTEGER DEFAULT 0")
    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist_channels (
            id SERIAL PRIMARY KEY,
            identifier TEXT NOT NULL UNIQUE,
            note TEXT,
            added_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bc_group_blacklist (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            group_id BIGINT NOT NULL,
            group_name TEXT,
            added_at TEXT NOT NULL,
            UNIQUE (user_id, group_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS auto_block_channels (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            channel_id BIGINT NOT NULL,
            channel_name TEXT,
            UNIQUE(user_id, channel_id)
        )
    """)
    conn.commit()
    conn.close()


def upsert_user(user_id, username, full_name):
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        INSERT INTO users (user_id, username, full_name, created_at)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT(user_id) DO UPDATE SET username=EXCLUDED.username, full_name=EXCLUDED.full_name
    """, (user_id, username, full_name, datetime.now().isoformat()))
    conn.commit(); conn.close()


def get_user_display_name(user_id: int) -> str:
    """Ambil nama depan user dari DB. Fallback ke ID jika tidak ada."""
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT full_name FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone(); conn.close()
    if row and row[0]:
        first_name = row[0].strip().split()[0]
        return first_name
    return str(user_id)


def save_user_session(user_id, api_id, api_hash, string_session):
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        INSERT INTO sessions (user_id, api_id, api_hash, string_session)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT(user_id) DO UPDATE SET api_id=EXCLUDED.api_id, api_hash=EXCLUDED.api_hash, string_session=EXCLUDED.string_session
    """, (user_id, api_id, api_hash, string_session))
    conn.commit(); conn.close()


def get_user_session(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT api_id, api_hash, string_session FROM sessions WHERE user_id=%s", (user_id,))
    row = c.fetchone(); conn.close()
    return {"api_id": row[0], "api_hash": row[1], "string_session": row[2]} if row else None


def delete_user_session(user_id):
    conn = get_conn(); c = conn.cursor(); c.execute("DELETE FROM sessions WHERE user_id=%s", (user_id,))
    conn.commit(); conn.close()


def is_subscribed(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT expired_at FROM subscriptions WHERE user_id=%s AND is_active=1", (user_id,))
    row = c.fetchone(); conn.close()
    if not row:
        return False
    return datetime.now() < datetime.fromisoformat(row[0])


def get_subscription_info(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT paid_at, expired_at, is_active, plan FROM subscriptions WHERE user_id=%s", (user_id,))
    row = c.fetchone(); conn.close(); return row


def activate_subscription(user_id, days=30):
    now = datetime.now(); expired = now + timedelta(days=days)
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        INSERT INTO subscriptions (user_id, plan, paid_at, expired_at, is_active)
        VALUES (%s,'vip',%s,%s,1)
        ON CONFLICT(user_id) DO UPDATE SET paid_at=EXCLUDED.paid_at, expired_at=EXCLUDED.expired_at, is_active=1, plan='vip'
    """, (user_id, now.isoformat(), expired.isoformat()))
    conn.commit(); conn.close(); return expired


# Ubah nilai minutes di sini untuk mengatur durasi trial
TRIAL_DURATION_MINUTES = 5


def activate_trial(user_id):
    minutes = TRIAL_DURATION_MINUTES
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT trial_used FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone()
    if row and row[0]:
        conn.close()
        return False, None, minutes
    c.execute("UPDATE users SET trial_used=1 WHERE user_id=%s", (user_id,))
    now = datetime.now()
    expired = now + timedelta(minutes=minutes)
    c.execute("""
        INSERT INTO subscriptions (user_id, plan, paid_at, expired_at, is_active)
        VALUES (%s,'trial',%s,%s,1)
        ON CONFLICT(user_id) DO UPDATE SET paid_at=EXCLUDED.paid_at, expired_at=EXCLUDED.expired_at, is_active=1, plan='trial'
    """, (user_id, now.isoformat(), expired.isoformat()))
    conn.commit(); conn.close()
    return True, expired, minutes


def has_used_trial(user_id) -> bool:
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT trial_used FROM users WHERE user_id=%s", (user_id,))
    row = c.fetchone(); conn.close()
    return bool(row and row[0])


def revoke_subscription(user_id):
    conn = get_conn(); c = conn.cursor(); c.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=%s", (user_id,))
    conn.commit(); conn.close()


def get_user_by_username(username):
    conn = get_conn(); c = conn.cursor(); username_clean = username.lstrip("@").lower()
    c.execute("SELECT user_id FROM users WHERE LOWER(username)=%s", (username_clean,))
    row = c.fetchone(); conn.close(); return row[0] if row else None


def get_auto_dl_view_once(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT auto_dl_view_once FROM user_settings WHERE user_id=%s", (user_id,))
    row = c.fetchone(); conn.close(); return bool(row[0]) if row else False


def set_auto_dl_view_once(user_id, enabled: bool):
    conn = get_conn(); c = conn.cursor()
    c.execute("""
        INSERT INTO user_settings (user_id, auto_dl_view_once)
        VALUES (%s, %s)
        ON CONFLICT(user_id) DO UPDATE SET auto_dl_view_once=EXCLUDED.auto_dl_view_once
    """, (user_id, 1 if enabled else 0))
    conn.commit(); conn.close()


def blacklist_add(identifier: str, note: str = "") -> bool:
    clean = identifier.strip().lstrip("@"); conn = get_conn(); c = conn.cursor()
    try:
        c.execute("INSERT INTO blacklist_channels (identifier, note, added_at) VALUES (%s,%s,%s)", (clean, note or "", datetime.now().isoformat()))
        conn.commit(); return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback(); return False
    finally:
        conn.close()


def blacklist_remove(identifier: str) -> bool:
    clean = identifier.strip().lstrip("@"); conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM blacklist_channels WHERE identifier=%s", (clean,)); deleted = c.rowcount
    conn.commit(); conn.close(); return deleted > 0


def blacklist_list() -> list[dict]:
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT identifier, note, added_at FROM blacklist_channels ORDER BY added_at DESC")
    rows = c.fetchall(); conn.close()
    return [{"identifier": r[0], "note": r[1], "added_at": r[2]} for r in rows]


def is_channel_blacklisted(identifier: str) -> bool:
    from utils.helpers import _normalize_channel_id
    variants = _normalize_channel_id(identifier)
    conn = get_conn(); c = conn.cursor(); c.execute("SELECT identifier FROM blacklist_channels")
    rows = c.fetchall(); conn.close()
    return any(variants & _normalize_channel_id(db_id) for (db_id,) in rows)


def bc_blacklist_add(user_id: int, group_id: int, group_name: str = "") -> bool:
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO bc_group_blacklist (user_id, group_id, group_name, added_at)
            VALUES (%s,%s,%s,%s) ON CONFLICT (user_id, group_id) DO NOTHING
        """, (user_id, group_id, group_name or "", datetime.now().isoformat()))
        conn.commit(); return c.rowcount > 0
    finally:
        conn.close()


def bc_blacklist_remove(user_id: int, group_id: int) -> bool:
    conn = get_conn(); c = conn.cursor(); c.execute("DELETE FROM bc_group_blacklist WHERE user_id=%s AND group_id=%s", (user_id, group_id))
    deleted = c.rowcount; conn.commit(); conn.close(); return deleted > 0


def bc_blacklist_get(user_id: int) -> list[dict]:
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT group_id, group_name, added_at FROM bc_group_blacklist WHERE user_id=%s ORDER BY added_at DESC", (user_id,))
    rows = c.fetchall(); conn.close()
    return [{"group_id": r[0], "group_name": r[1], "added_at": r[2]} for r in rows]


def bc_blacklist_ids(user_id: int) -> set:
    conn = get_conn(); c = conn.cursor(); c.execute("SELECT group_id FROM bc_group_blacklist WHERE user_id=%s", (user_id,))
    rows = c.fetchall(); conn.close(); return {r[0] for r in rows}


# ── Auto Block Leaver ──────────────────────────────────────────────────────────

def add_auto_block_channel(user_id: int, channel_id: int, channel_name: str = "") -> bool:
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO auto_block_channels (user_id, channel_id, channel_name)
            VALUES (%s, %s, %s) ON CONFLICT(user_id, channel_id) DO NOTHING
        """, (user_id, channel_id, channel_name or ""))
        conn.commit(); return c.rowcount > 0
    finally:
        conn.close()


def remove_auto_block_channel(user_id: int, channel_id: int) -> bool:
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM auto_block_channels WHERE user_id=%s AND channel_id=%s", (user_id, channel_id))
    deleted = c.rowcount; conn.commit(); conn.close(); return deleted > 0


def get_auto_block_channels(user_id: int) -> list[dict]:
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT channel_id, channel_name FROM auto_block_channels WHERE user_id=%s", (user_id,))
    rows = c.fetchall(); conn.close()
    return [{"channel_id": r[0], "channel_name": r[1]} for r in rows]


def get_all_auto_block_channel_owners(channel_id: int) -> list[int]:
    """Kembalikan semua user_id yang memantau channel_id ini."""
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT user_id FROM auto_block_channels WHERE channel_id=%s", (channel_id,))
    rows = c.fetchall(); conn.close()
    return [r[0] for r in rows]
