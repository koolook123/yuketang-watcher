import asyncio
import json
import time
from .models import Item
from .paths import db_path


def _dig(obj, path, default=None):
    cur = obj
    for part in str(path or "").split("."):
        if not part:
            continue
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list) and part.isdigit():
            idx = int(part)
            cur = cur[idx] if idx < len(cur) else None
        else:
            return default
        if cur is None:
            return default
    return cur


class MockCollector:
    """无需真实账号即可跑通全流程：固定 3 条 + 每 5 分钟一条动态内容。"""

    async def fetch(self, cfg):
        items = [
            Item(id="mock-homework-1", type="homework", course="示例课程",
                 title="【示例作业】第三章习题", publisher="示例老师",
                 published_at=int(time.time()) - 120, url="", preview="这是 Mock 数据，用于验证通知链路。"),
            Item(id="mock-exercise-1", type="exercise", course="示例课程",
                 title="【示例习题】随堂测验", publisher="示例老师",
                 published_at=int(time.time()) - 90, url="", preview="这是 Mock 数据。"),
            Item(id="mock-discussion-1", type="discussion", course="示例课程",
                 title="【示例讨论】你怎么看这个知识点？", publisher="示例老师",
                 published_at=int(time.time()) - 60, url="", preview="这是 Mock 数据。"),
        ]
        interval = int((cfg.get("collector") or {}).get("mock_interval") or 300)
        bucket = int(time.time()) // max(1, interval)
        items.append(Item(
            id="mock-dynamic-" + str(interval) + "-" + str(bucket), type="discussion", course="示例课程",
            title="【动态示例】新讨论 #" + str(bucket % 100000),
            publisher="MockCollector", published_at=int(time.time()), url="",
            preview="用于验证『新内容 → 通知历史』是否正常工作。",
        ))
        return items


class HttpCollector:
    """配置驱动 HTTP 采集器：抓包后填写 endpoints / headers / field_map 即可。"""

    def __init__(self, cfg):
        c = cfg.get("collector", {})
        self.base = str(c.get("base_url") or "").rstrip("/")
        self.headers = c.get("headers") or {}
        self.endpoints = c.get("endpoints") or {}
        self.methods = c.get("methods") or {}
        self.bodies = c.get("bodies") or {}
        self.list_path = c.get("list_path") or "data.list"
        self.fmap = c.get("field_map") or {}
        self.token = cfg.get("token") or ""
        self.timeout = 15.0

    def _url(self, path):
        path = str(path or "")
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return self.base + "/" + path.lstrip("/")

    def _render(self, text):
        return str(text or "").replace("{{token}}", self.token)

    async def _fetch_type(self, client, typ):
        import httpx
        endpoint = self.endpoints.get(typ)
        if not endpoint:
            return []
        method = str(self.methods.get(typ) or "GET").upper()
        headers = dict(self.headers)
        if self.token:
            headers.setdefault("Authorization", "Bearer " + self.token)
        body = self._render(self.bodies.get(typ, ""))
        kwargs = {"headers": headers, "timeout": self.timeout}
        if method == "POST":
            try:
                kwargs["json"] = json.loads(body) if body.strip() else {}
            except Exception:
                kwargs["content"] = body.encode("utf-8")
                headers["Content-Type"] = "application/json"
        r = await client.request(method, self._url(endpoint), **kwargs)
        r.raise_for_status()
        data = r.json()
        rows = _dig(data, self.list_path, []) or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        out = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            f = lambda key, default="": _dig(row, self.fmap.get(key, key), default)
            item_id = str(f("id") or "")
            if not item_id:
                continue
            published = f("published_at", 0)
            try:
                published = int(published)
            except Exception:
                published = 0
            out.append(Item(
                id=typ + ":" + item_id, type=typ,
                course=str(f("course") or ""), title=str(f("title") or "(无标题)"),
                publisher=str(f("publisher") or ""), published_at=published,
                url=str(f("url") or ""), preview=str(f("preview") or ""),
            ))
        return out

    async def fetch(self, cfg):
        import httpx
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *[self._fetch_type(client, t) for t in ("homework", "exercise", "discussion")],
                return_exceptions=True,
            )
        items = []
        for res in results:
            if isinstance(res, Exception):
                continue
            items.extend(res)
        return items


async def collect(cfg) -> list:
    c = cfg.get("collector") or {}
    mode = str(c.get("mode") or "mock").lower()
    if mode == "http":
        return await HttpCollector(cfg).fetch(cfg)
    return await MockCollector().fetch(cfg)
