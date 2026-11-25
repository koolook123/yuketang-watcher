import os
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def db_path() -> Path:
    raw = os.getenv("DB_PATH", "data/watcher.db")
    p = Path(raw)
    if not p.is_absolute():
        p = project_root() / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def pid_path() -> Path:
    return db_path().parent / "watcher.pid"


def guardian_lock_path() -> Path:
    return db_path().parent / "guardian.lock"
