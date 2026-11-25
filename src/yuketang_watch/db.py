import json
import sqlite3
import threading
import time
from .paths import db_path

_LOCAL = threading.local()


def conn() -> sqlite3.Connection:
    c = getattr(_LOCAL, "conn", None)
    if c is None:
        c = sqlite3.connect(str(db_path()), timeout=20, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=20000")
        _LOCAL.conn = c
    return c


def init_db() -> None:
    c = conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS seen_items (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            course TEXT,
            title TEXT,
            publisher TEXT,
            published_at INTEGER,
            url TEXT,
            preview TEXT,
            first_seen_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id TEXT,
            type TEXT,
            course TEXT,
            title TEXT,
            channel TEXT,
            channel_type TEXT,
            status TEXT,
            error TEXT,
            payload TEXT,
            sent_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_noti_time ON notifications(sent_at DESC);
        CREATE INDEX IF NOT EXISTS idx_noti_type ON notifications(type, status);
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings_draft (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
        CREATE TABLE IF NOT EXISTS heartbeat (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    c.commit()


def log_event(level: str, message: str) -> None:
    try:
        conn().execute(
            "INSERT INTO events(ts, level, message) VALUES(?,?,?)",
            (int(time.time()), level, str(message)[:1000]),
        )
        conn().commit()
    except Exception:
        pass


def heartbeat(key: str, value: str = "") -> None:
    if not value:
        value = str(int(time.time()))
    conn().execute(
        "INSERT INTO heartbeat(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn().commit()


def get_heartbeats() -> dict:
    return {r["key"]: r["value"] for r in conn().execute("SELECT key,value FROM heartbeat")}


def is_seen(item_id: str) -> bool:
    return conn().execute("SELECT 1 FROM seen_items WHERE id=?", (item_id,)).fetchone() is not None


def mark_seen(item) -> bool:
    c = conn()
    cur = c.execute("INSERT OR IGNORE INTO seen_items VALUES(?,?,?,?,?,?,?,?,?)", (
        item.id, item.type, item.course, item.title, item.publisher,
        item.published_at, item.url, item.preview, int(time.time()),
    ))
    c.commit()
    return cur.rowcount > 0


def record_notification(item, channel, channel_type, ok, error, payload) -> None:
    conn().execute(
        "INSERT INTO notifications(item_id,type,course,title,channel,channel_type,status,error,payload,sent_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (item.id, item.type, item.course, item.title, channel, channel_type,
         "ok" if ok else "fail", str(error or "")[:1000], payload, int(time.time())),
    )
    conn().commit()


def query_notifications(limit=100, offset=0, type=None, status=None, channel_type=None, course=None, since=None, until=None):
    sql = "SELECT * FROM notifications WHERE 1=1"
    args = []
    if type:
        sql += " AND type=?"; args.append(type)
    if status:
        sql += " AND status=?"; args.append(status)
    if channel_type:
        sql += " AND channel_type=?"; args.append(channel_type)
    if course:
        sql += " AND course LIKE ?"; args.append("%" + course + "%")
    if since:
        sql += " AND sent_at>=?"; args.append(int(since))
    if until:
        sql += " AND sent_at<=?"; args.append(int(until))
    sql += " ORDER BY sent_at DESC LIMIT ? OFFSET ?"
    args.extend([int(limit), int(offset)])
    rows = [dict(r) for r in conn().execute(sql, args)]
    total = conn().execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    return rows, total


def query_events(limit=200):
    return [dict(r) for r in conn().execute("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (int(limit),))]


def counts_today():
    start = int(time.time()) - 86400
    row = conn().execute(
        "SELECT COUNT(*) n, SUM(status='ok') ok, SUM(status='fail') fail FROM notifications WHERE sent_at>=?",
        (start,),
    ).fetchone()
    return {"total": row["n"] or 0, "ok": row["ok"] or 0, "fail": row["fail"] or 0}
