import os, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TEST_DB = Path(tempfile.gettempdir()) / "yuketang_watcher_test.db"
os.environ["DB_PATH"] = str(TEST_DB)

import pytest

@pytest.fixture(autouse=True, scope="session")
def clean_db():
    for suffix in ("", "-shm", "-wal"):
        p = Path(str(TEST_DB) + suffix)
        if p.exists():
            p.unlink()
    from yuketang_watch import db
    db.init_db()
