import asyncio
from yuketang_watch.collectors import _dig, MockCollector

def test_dig():
    obj = {"data": {"list": [{"id": "7"}]}}
    assert _dig(obj, "data.list.0.id") == "7"
    assert _dig(obj, "data.missing", "fallback") == "fallback"

def test_mock_covers_three_types():
    items = asyncio.run(MockCollector().fetch({}))
    assert {i.type for i in items} == {"homework", "exercise", "discussion"}
    assert all(i.id for i in items)
