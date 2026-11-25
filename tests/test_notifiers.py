from yuketang_watch.notifiers import render_text, render_html
from yuketang_watch.models import Item

def test_render():
    it = Item(id="1", type="homework", course="高数", title="作业1", url="https://example.com/x")
    assert "作业1" in render_text(it)
    assert "高数" in render_html(it)
    assert "https://example.com/x" in render_html(it)
