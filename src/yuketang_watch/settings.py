import json
import time
from .db import conn, init_db
from .models import DEFAULT_SETTINGS


def _get(table, key):
    row = conn().execute("SELECT value FROM " + table + " WHERE key=?", (key,)).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["value"])
    except Exception:
        return None


def _set(table, key, value):
    conn().execute(
        "INSERT INTO " + table + "(key,value,updated_at) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, json.dumps(value, ensure_ascii=False), int(time.time())),
    )
    conn().commit()


def _deep_merge(base, patch):
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def effective() -> dict:
    init_db()
    stored = _get("settings", "app") or {}
    return _deep_merge(DEFAULT_SETTINGS, stored)


def draft() -> dict:
    init_db()
    saved = _get("settings_draft", "app")
    if saved is None:
        return effective()
    return _deep_merge(effective(), saved)


def save_draft(patch: dict) -> dict:
    cur = draft()
    merged = _deep_merge(cur, patch)
    _set("settings_draft", "app", merged)
    return merged


def reset_draft() -> dict:
    conn().execute("DELETE FROM settings_draft WHERE key='app'")
    conn().commit()
    return effective()


def apply_draft() -> dict:
    d = draft()
    _set("settings", "app", d)
    conn().execute("DELETE FROM settings_draft WHERE key='app'")
    conn().commit()
    return d
