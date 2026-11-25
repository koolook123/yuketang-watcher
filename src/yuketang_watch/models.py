from dataclasses import dataclass, asdict


@dataclass
class Item:
    id: str
    type: str
    course: str
    title: str
    publisher: str = ""
    published_at: int = 0
    url: str = ""
    preview: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_SETTINGS = {
    "poll_interval": 30,
    "time_windows": [
        {"start": "00:00", "end": "23:59", "days": [0, 1, 2, 3, 4, 5, 6]}
    ],
    "content_types": {"homework": True, "exercise": True, "discussion": True},
    "course_filter": [],
    "dnd": False,
    "notify_on_update": False,
    "channels": [],
    "token": "",
    "token_expire_at": 0,
    "collector": {
        "mode": "mock",
        "base_url": "",
        "headers": {},
        "endpoints": {"homework": "", "exercise": "", "discussion": ""},
        "methods": {"homework": "GET", "exercise": "GET", "discussion": "GET"},
        "bodies": {"homework": "", "exercise": "", "discussion": ""},
        "list_path": "data.list",
        "field_map": {
            "id": "id",
            "title": "title",
            "course": "course",
            "publisher": "publisher",
            "published_at": "published_at",
            "url": "url",
            "preview": "preview",
        },
    },
    "backoff": {"enabled": True, "max_factor": 8},
}


CHANNEL_PRESETS = {
    "email_qq": {
        "type": "email", "label": "邮箱 (QQ 预设)",
        "config": {"host": "smtp.qq.com", "port": 465, "user": "", "password": "", "to": [], "use_ssl": True},
    },
    "email_163": {
        "type": "email", "label": "邮箱 (163 预设)",
        "config": {"host": "smtp.163.com", "port": 465, "user": "", "password": "", "to": [], "use_ssl": True},
    },
    "email_gmail": {
        "type": "email", "label": "邮箱 (Gmail 预设)",
        "config": {"host": "smtp.gmail.com", "port": 465, "user": "", "password": "", "to": [], "use_ssl": True},
    },
    "dingtalk": {
        "type": "dingtalk", "label": "钉钉群机器人",
        "config": {"webhook": "", "secret": ""},
    },
    "telegram": {
        "type": "telegram", "label": "Telegram Bot",
        "config": {"bot_token": "", "chat_id": ""},
    },
    "webhook": {
        "type": "webhook", "label": "自定义 Webhook",
        "config": {"url": "", "method": "POST", "headers": {}, "body_template": ""},
    },
}


TYPE_LABELS = {"homework": "作业", "exercise": "习题", "discussion": "讨论"}
