import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .db import (init_db, log_event, get_heartbeats, query_notifications,
                 query_events, counts_today)
from .settings import effective, draft, save_draft, reset_draft, apply_draft
from .paths import project_root, pid_path, guardian_lock_path, db_path
from .models import CHANNEL_PRESETS
from .notifiers import send_one
from .models import Item

app = FastAPI(title="yuketang-watcher")
WEB_DIR = project_root() / "src" / "yuketang_watch" / "web"
LOCK_FD = None


def _read_pid():
    try:
        return int(pid_path().read_text().strip())
    except Exception:
        return 0


def _alive(pid):
    if not pid:
        return False
    if sys.platform == "win32":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def watcher_status():
    pid = _read_pid()
    return {"running": _alive(pid), "pid": pid or None}


def start_watcher():
    st = watcher_status()
    if st["running"]:
        return st
    log = open(db_path().parent / "watcher.log", "a", encoding="utf-8")
    p = subprocess.Popen(
        [sys.executable, "-m", "yuketang_watch.watcher"],
        cwd=str(project_root()), stdout=log, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, close_fds=True,
    )
    pid_path().write_text(str(p.pid))
    log_event("INFO", "启动 Watcher PID=" + str(p.pid))
    time.sleep(0.4)
    return watcher_status()


def stop_watcher():
    pid = _read_pid()
    if pid and _alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(30):
                if not _alive(pid):
                    break
                time.sleep(0.1)
        except Exception as exc:
            log_event("ERROR", "停止 Watcher 失败：" + str(exc))
    try:
        pid_path().unlink()
    except Exception:
        pass
    log_event("INFO", "停止 Watcher")
    return watcher_status()


def _acquire_lock():
    global LOCK_FD
    path = guardian_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR)
    try:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except ImportError:
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, str(os.getpid()).encode())
            os.ftruncate(fd, 32)
        except OSError:
            os.close(fd)
            raise SystemExit("Guardian already running")
    except BlockingIOError:
        os.close(fd)
        raise SystemExit("Guardian already running")
    LOCK_FD = fd


@app.get("/api/status")
def api_status():
    init_db()
    hb = get_heartbeats()
    return {
        "watcher": watcher_status(),
        "heartbeats": hb,
        "counts_today": counts_today(),
        "settings": {
            "poll_interval": effective().get("poll_interval"),
            "dnd": effective().get("dnd"),
            "channels": [{"name": c.get("name"), "type": c.get("type"), "enabled": c.get("enabled", True)}
                         for c in (effective().get("channels") or [])],
        },
        "token_expire_at": effective().get("token_expire_at", 0),
    }


@app.post("/api/watcher/start")
def api_start():
    return start_watcher()


@app.post("/api/watcher/stop")
def api_stop():
    return stop_watcher()


@app.get("/api/settings")
def api_get_settings():
    return {"effective": effective(), "draft": draft(), "presets": CHANNEL_PRESETS}


@app.post("/api/settings/draft")
def api_save_draft(payload: dict = Body(...)):
    return {"settings": save_draft(payload)}


@app.post("/api/settings/reset")
def api_reset_draft():
    return {"settings": reset_draft()}


@app.post("/api/settings/apply")
def api_apply():
    d = apply_draft()
    log_event("INFO", "配置已生效：频率=" + str(d.get("poll_interval")) + "s")
    return {"settings": d}


@app.post("/api/settings/applyWithDraft")
def api_apply_with_draft(payload: dict = Body(...)):
    save_draft(payload)
    d = apply_draft()
    log_event("INFO", "配置已保存并生效：频率=" + str(d.get("poll_interval")) + "s")
    return {"settings": d}


@app.get("/api/notifications")
def api_notifications(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    type: str = Query(None),
    status: str = Query(None),
    channel_type: str = Query(None),
    course: str = Query(None),
    since: int = Query(None),
    until: int = Query(None),
):
    init_db()
    rows, total = query_notifications(limit, offset, type, status, channel_type, course, since, until)
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


@app.get("/api/events")
def api_events(limit: int = Query(200, ge=1, le=1000)):
    init_db()
    return {"items": query_events(limit)}


@app.post("/api/channels/test")
async def api_channel_test(payload: dict = Body(...)):
    channel = payload.get("channel") or {}
    item = Item(id="test-" + str(int(time.time())), type=payload.get("type", "homework"),
                course="测试课程", title="【测试通知】这是一条测试消息",
                publisher="yuketang-watcher", published_at=int(time.time()),
                url="", preview="收到即表示渠道配置正确。")
    name, typ, ok, err, _ = await send_one(item, channel)
    return {"ok": ok, "error": err, "channel": name, "type": typ}


@app.get("/")
def index():
    return FileResponse(str(WEB_DIR / "index.html"))


app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def _auto_restart_task():
    while True:
        try:
            st = watcher_status()
            if not st["running"]:
                desired = effective().get("auto_restart", True)
                if desired:
                    start_watcher()
        except Exception:
            pass
        time.sleep(5)


def main():
    global LOCK_FD
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")))
    args = parser.parse_args()
    if args.status:
        print(json.dumps({"watcher": watcher_status()}, ensure_ascii=False))
        return
    _acquire_lock()
    init_db()
    if effective().get("auto_restart", True):
        start_watcher()
    import threading
    threading.Thread(target=_auto_restart_task, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port, log_level=os.getenv("LOG_LEVEL", "info").lower())


if __name__ == "__main__":
    main()
