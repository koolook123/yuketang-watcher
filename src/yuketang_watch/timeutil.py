import time
from datetime import datetime


def _parse_hhmm(s: str):
    try:
        h, m = str(s).split(":", 1)
        return int(h), int(m)
    except Exception:
        return None


def in_time_window(windows, now=None) -> bool:
    if not windows:
        return True
    dt = datetime.fromtimestamp(now or time.time())
    minute = dt.hour * 60 + dt.minute
    weekday = dt.weekday()  # Mon=0 ... Sun=6
    for w in windows:
        days = w.get("days")
        if days is not None and weekday not in [int(d) for d in days]:
            continue
        a = _parse_hhmm(w.get("start", "00:00"))
        b = _parse_hhmm(w.get("end", "23:59"))
        if not a or not b:
            continue
        start, end = a[0] * 60 + a[1], b[0] * 60 + b[1]
        if start <= end:
            if start <= minute <= end:
                return True
        else:
            if minute >= start or minute <= end:
                return True
    return False
