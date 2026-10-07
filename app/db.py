import sqlite3
import threading
import time

from .config import DB_PATH, DEFAULTS

_lock = threading.RLock()
_conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
_conn.row_factory = sqlite3.Row
_conn.execute("PRAGMA journal_mode=WAL")

_conn.executescript(
    """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT, first_name TEXT, last_name TEXT,
    joined_at INTEGER NOT NULL, last_seen INTEGER NOT NULL,
    free_left INTEGER NOT NULL DEFAULT 0,
    balance INTEGER NOT NULL DEFAULT 0,
    premium INTEGER NOT NULL DEFAULT 0,
    banned INTEGER NOT NULL DEFAULT 0,
    tutorial_seen INTEGER NOT NULL DEFAULT 0,
    gens_total INTEGER NOT NULL DEFAULT 0,
    stars_spent INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_ref TEXT NOT NULL, title TEXT NOT NULL, link TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, kind TEXT NOT NULL, stars INTEGER NOT NULL,
    charge_id TEXT, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS gens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL, kind TEXT NOT NULL, created_at INTEGER NOT NULL
);
"""
)


def _q(sql: str, args=()) -> list[sqlite3.Row]:
    with _lock:
        return _conn.execute(sql, args).fetchall()


def _x(sql: str, args=()) -> sqlite3.Cursor:
    with _lock:
        return _conn.execute(sql, args)


# ---------- settings ----------
def get_setting(key: str) -> str:
    rows = _q("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0]["value"] if rows else DEFAULTS[key]


def get_int(key: str) -> int:
    try:
        return int(get_setting(key))
    except ValueError:
        return int(DEFAULTS[key])


def set_setting(key: str, value: str) -> None:
    _x("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


# ---------- users ----------
def upsert_user(u: dict) -> tuple[sqlite3.Row, bool]:
    now = int(time.time())
    uid = int(u["id"])
    with _lock:
        row = _q("SELECT * FROM users WHERE id=?", (uid,))
        if row:
            _x(
                "UPDATE users SET username=?, first_name=?, last_name=?, last_seen=? WHERE id=?",
                (u.get("username"), u.get("first_name"), u.get("last_name"), now, uid),
            )
            return _q("SELECT * FROM users WHERE id=?", (uid,))[0], False
        _x(
            "INSERT INTO users(id,username,first_name,last_name,joined_at,last_seen,free_left) VALUES(?,?,?,?,?,?,?)",
            (uid, u.get("username"), u.get("first_name"), u.get("last_name"), now, now, get_int("free_gens")),
        )
        return _q("SELECT * FROM users WHERE id=?", (uid,))[0], True


def get_user(uid: int) -> sqlite3.Row | None:
    rows = _q("SELECT * FROM users WHERE id=?", (uid,))
    return rows[0] if rows else None


def can_generate(uid: int) -> bool:
    u = get_user(uid)
    return bool(u and (u["premium"] or u["free_left"] > 0 or u["balance"] > 0))


def consume(uid: int, kind: str) -> bool:
    """Списывает одну генерацию: премиум — бесплатно, затем free_left, затем balance."""
    with _lock:
        u = get_user(uid)
        if not u:
            return False
        if u["premium"]:
            pass
        elif u["free_left"] > 0:
            _x("UPDATE users SET free_left=free_left-1 WHERE id=?", (uid,))
        elif u["balance"] > 0:
            _x("UPDATE users SET balance=balance-1 WHERE id=?", (uid,))
        else:
            return False
        _x("UPDATE users SET gens_total=gens_total+1 WHERE id=?", (uid,))
        _x("INSERT INTO gens(user_id,kind,created_at) VALUES(?,?,?)", (uid, kind, int(time.time())))
        return True


def add_balance(uid: int, delta: int) -> int | None:
    with _lock:
        u = get_user(uid)
        if not u:
            return None
        new = max(0, u["balance"] + delta)
        _x("UPDATE users SET balance=? WHERE id=?", (new, uid))
        return new


def set_premium(uid: int, on: bool) -> None:
    _x("UPDATE users SET premium=? WHERE id=?", (1 if on else 0, uid))


def set_banned(uid: int, on: bool) -> bool:
    cur = _x("UPDATE users SET banned=? WHERE id=?", (1 if on else 0, uid))
    return cur.rowcount > 0


def mark_tutorial_seen(uid: int) -> None:
    _x("UPDATE users SET tutorial_seen=1 WHERE id=?", (uid,))


def list_users(query: str = "", offset: int = 0, limit: int = 20, banned_only: bool = False) -> tuple[list[dict], int]:
    where, args = [], []
    if query:
        q = query.strip().lstrip("@")
        where.append("(CAST(id AS TEXT) = ? OR username LIKE ? OR first_name LIKE ?)")
        args += [q, f"%{q}%", f"%{q}%"]
    if banned_only:
        where.append("banned=1")
    w = ("WHERE " + " AND ".join(where)) if where else ""
    total = _q(f"SELECT COUNT(*) c FROM users {w}", args)[0]["c"]
    rows = _q(f"SELECT * FROM users {w} ORDER BY joined_at DESC LIMIT ? OFFSET ?", (*args, limit, offset))
    return [dict(r) for r in rows], total


def all_user_ids() -> list[int]:
    return [r["id"] for r in _q("SELECT id FROM users WHERE banned=0")]


def stats() -> dict:
    day = int(time.time()) - 86400
    one = lambda sql, a=(): _q(sql, a)[0][0]  # noqa: E731
    return {
        "users": one("SELECT COUNT(*) FROM users"),
        "new_24h": one("SELECT COUNT(*) FROM users WHERE joined_at>?", (day,)),
        "active_24h": one("SELECT COUNT(*) FROM users WHERE last_seen>?", (day,)),
        "premium": one("SELECT COUNT(*) FROM users WHERE premium=1"),
        "banned": one("SELECT COUNT(*) FROM users WHERE banned=1"),
        "gens": one("SELECT COUNT(*) FROM gens"),
        "gens_24h": one("SELECT COUNT(*) FROM gens WHERE created_at>?", (day,)),
        "stars": one("SELECT COALESCE(SUM(stars),0) FROM payments"),
        "stars_24h": one("SELECT COALESCE(SUM(stars),0) FROM payments WHERE created_at>?", (day,)),
        "gens_slice": one("SELECT COUNT(*) FROM gens WHERE kind='slice'"),
        "gens_frame": one("SELECT COUNT(*) FROM gens WHERE kind='frame'"),
    }


# ---------- payments ----------
def log_payment(uid: int, kind: str, stars: int, charge_id: str) -> None:
    _x("INSERT INTO payments(user_id,kind,stars,charge_id,created_at) VALUES(?,?,?,?,?)", (uid, kind, stars, charge_id, int(time.time())))
    _x("UPDATE users SET stars_spent=stars_spent+? WHERE id=?", (stars, uid))


# ---------- channels ----------
def list_channels() -> list[dict]:
    return [dict(r) for r in _q("SELECT * FROM channels ORDER BY id")]


def add_channel(chat_ref: str, title: str, link: str) -> None:
    _x("INSERT INTO channels(chat_ref,title,link) VALUES(?,?,?)", (chat_ref, title, link))


def del_channel(cid: int) -> None:
    _x("DELETE FROM channels WHERE id=?", (cid,))
