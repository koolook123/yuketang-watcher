import random
import time


def jitter(seconds: float, errors: int, cfg: dict) -> float:
    cfg = cfg or {}
    if not cfg.get("enabled", True):
        return max(1.0, seconds)
    factor = min(int(cfg.get("max_factor") or 8), 2 ** max(0, errors))
    return max(1.0, seconds * factor) + random.uniform(0, min(2.0, seconds * 0.2))
