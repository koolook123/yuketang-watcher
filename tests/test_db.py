from yuketang_watch.db import mark_seen, is_seen, record_notification, query_notifications
from yuketang_watch.models import Item

def test_dedup():
    it = Item(id="unit-seen-1", type="homework", course="测试课", title="作业")
    assert is_seen(it.id) is False
    assert mark_seen(it) is True
    assert is_seen(it.id) is True
    assert mark_seen(it) is False

def test_notification_history():
    it = Item(id="unit-noti-1", type="discussion", course="历史课", title="讨论题")
    record_notification(it, "邮箱", "email", True, "", "{}")
    record_notification(it, "钉钉", "dingtalk", False, "超时", "{}")
    rows, total = query_notifications(type="discussion", limit=10)
    assert total >= 2
    assert any(r["channel"] == "邮箱" and r["status"] == "ok" for r in rows)
    assert any(r["channel"] == "钉钉" and r["status"] == "fail" for r in rows)
