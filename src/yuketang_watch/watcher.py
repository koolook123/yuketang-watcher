import asyncio
import signal
import sys
import time

from .db import (init_db, log_event, heartbeat, mark_seen, is_seen,
                 record_notification, counts_today)
from .settings import effective
from .collectors import collect
from .notifiers import send_all
from .timeutil import in_time_window
from .backoff import jitter
from .models import TYPE_LABELS


_running = True


def _stop(signum, frame):
    global _running
    _running = False


async def _cycle(cfg, errors):
    types = cfg.get("content_types") or {}
    items = await collect(cfg)
    items = [i for i in items if types.get(i.type, True)]
    filt = [str(x) for x in (cfg.get("course_filter") or []) if str(x).strip()]
    if filt:
        items = [i for i in items if i.course in filt]
    new_items = []
    for item in items:
        if not is_seen(item.id):
            if mark_seen(item):
                new_items.append(item)
    heartbeat("last_poll_at")
    if not cfg.get("dnd") and new_items:
        for item in new_items:
            results = await send_all(item, cfg.get("channels") or [])
            for name, typ, ok, err, payload in results:
                record_notification(item, name, typ, ok, err, payload)
                if ok:
                    heartbeat("last_deliver_at")
            log_event("INFO", "推送 " + TYPE_LABELS.get(item.type, item.type)
                      + "：" + item.title + "（" + str(len(results)) + " 渠道）")
    await asyncio.sleep(0)
    return errors and 0 or 0


async def run_loop():
    init_db()
    log_event("INFO", "Watcher 启动")
    heartbeat("watcher_start_at")
    errors = 0
    while _running:
        cfg = effective()
        interval = max(1, int(cfg.get("poll_interval") or 30))
        started = time.time()
        try:
            if in_time_window(cfg.get("time_windows")):
                errors = await _cycle(cfg, errors)
            else:
                heartbeat("last_poll_at")
            errors = 0
        except Exception as exc:
            errors += 1
            log_event("ERROR", "轮询异常（第" + str(errors) + "次）：" + str(exc)[:500])
        delay = jitter(interval, errors, cfg.get("backoff"))
        wait = max(0.2, delay - (time.time() - started))
        try:
            await asyncio.sleep(wait)
        except asyncio.CancelledError:
            break
    log_event("INFO", "Watcher 停止")


def main():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    try:
        asyncio.run(run_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
