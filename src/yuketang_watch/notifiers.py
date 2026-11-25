import asyncio
import base64
import hashlib
import hmac
import html
import json
import smtplib
import time
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .models import TYPE_LABELS


def render_text(item) -> str:
    label = TYPE_LABELS.get(item.type, item.type)
    return (
        "【雨课堂新" + label + "】" + item.title + "\n"
        + "课程：" + item.course + "\n"
        + "发布者：" + item.publisher + "\n"
        + "时间：" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.published_at or time.time()))
        + (("\n链接：" + item.url) if item.url else "")
        + (("\n摘要：" + item.preview) if item.preview else "")
    )


def render_html(item) -> str:
    label = TYPE_LABELS.get(item.type, item.type)
    e = html.escape
    link = ('<p><a href="' + e(item.url) + '">查看详情</a></p>') if item.url else ""
    return (
        '<div style="font-family:system-ui,sans-serif;max-width:640px">'
        '<h2>雨课堂新' + e(label) + '</h2>'
        '<h3>' + e(item.title) + '</h3>'
        '<p><b>课程：</b>' + e(item.course) + '</p>'
        '<p><b>发布者：</b>' + e(item.publisher) + '</p>'
        '<p><b>时间：</b>' + e(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.published_at or time.time()))) + '</p>'
        + link
        + ('<p>' + e(item.preview) + '</p>' if item.preview else '')
        + '</div>'
    )


def _email(item, cfg):
    host = cfg.get("host")
    user = cfg.get("user")
    password = cfg.get("password")
    to = cfg.get("to") or []
    if isinstance(to, str):
        to = [x.strip() for x in to.split(",") if x.strip()]
    if not host or not user or not password or not to:
        return False, "邮箱配置不完整"
    port = int(cfg.get("port") or 465)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "【雨课堂新" + TYPE_LABELS.get(item.type, item.type) + "】" + item.title
    msg["From"] = user
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(render_text(item), "plain", "utf-8"))
    msg.attach(MIMEText(render_html(item), "html", "utf-8"))
    if cfg.get("use_ssl", True):
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)
        server.starttls()
    with server:
        server.login(user, password)
        server.sendmail(user, to, msg.as_string())
    return True, ""


def _dingtalk_sign(secret):
    ts = str(round(time.time() * 1000))
    sign = urllib.parse.quote(base64.b64encode(
        hmac.new(secret.encode(), (ts + "\n" + secret).encode(), hashlib.sha256).digest()
    ))
    return "&timestamp=" + ts + "&sign=" + sign


async def _dingtalk(item, cfg):
    import httpx
    url = cfg.get("webhook") or ""
    if not url:
        return False, "钉钉 webhook 未配置"
    secret = cfg.get("secret") or ""
    if secret:
        url += _dingtalk_sign(secret)
    payload = {"msgtype": "markdown", "markdown": {
        "title": "雨课堂新" + TYPE_LABELS.get(item.type, item.type),
        "text": "### " + render_text(item).replace("\n", "\n\n"),
    }}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload)
    data = {}
    try:
        data = r.json()
    except Exception:
        pass
    ok = r.status_code == 200 and data.get("errcode", 0) == 0
    return ok, ("" if ok else str(data or r.text)[:500])


async def _telegram(item, cfg):
    import httpx
    token = cfg.get("bot_token") or ""
    chat = cfg.get("chat_id") or ""
    if not token or not chat:
        return False, "Telegram 配置不完整"
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json={"chat_id": chat, "text": render_text(item)})
    data = {}
    try:
        data = r.json()
    except Exception:
        pass
    ok = r.status_code == 200 and data.get("ok") is True
    return ok, ("" if ok else str(data or r.text)[:500])


async def _webhook(item, cfg):
    import httpx
    url = cfg.get("url") or ""
    if not url:
        return False, "Webhook URL 未配置"
    tpl = cfg.get("body_template") or ""
    if tpl.strip():
        body = tpl.replace("{title}", item.title).replace("{course}", item.course)
        body = body.replace("{type}", item.type).replace("{text}", render_text(item))
        try:
            payload = json.loads(body)
        except Exception:
            payload = body
    else:
        payload = {"title": item.title, "course": item.course, "type": item.type,
                   "publisher": item.publisher, "url": item.url, "text": render_text(item)}
    method = str(cfg.get("method") or "POST").upper()
    headers = cfg.get("headers") or {}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.request(method, url, json=payload if isinstance(payload, dict) else None,
                                 content=None if isinstance(payload, dict) else str(payload).encode(),
                                 headers=headers)
    ok = 200 <= r.status_code < 300
    return ok, ("" if ok else r.text[:500])


async def send_one(item, channel):
    """channel: {name, type, enabled, config}"""
    typ = channel.get("type")
    cfg = channel.get("config") or {}
    name = channel.get("name") or typ
    try:
        if typ == "email":
            ok, err = await asyncio.to_thread(_email, item, cfg)
        elif typ == "dingtalk":
            ok, err = await _dingtalk(item, cfg)
        elif typ == "telegram":
            ok, err = await _telegram(item, cfg)
        elif typ == "webhook":
            ok, err = await _webhook(item, cfg)
        else:
            ok, err = False, "未知渠道类型：" + str(typ)
    except Exception as exc:
        ok, err = False, str(exc)[:1000]
    payload = json.dumps({"channel": name, "type": typ, "item": item.to_dict()}, ensure_ascii=False)[:4000]
    return name, typ, ok, err, payload


async def send_all(item, channels):
    enabled = [c for c in (channels or []) if c.get("enabled", True)]
    if not enabled:
        return []
    return await asyncio.gather(*[send_one(item, c) for c in enabled])
