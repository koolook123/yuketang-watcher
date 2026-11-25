from datetime import datetime
from yuketang_watch.timeutil import in_time_window

WED_0900 = datetime(2026, 11, 25, 9, 0).timestamp()   # 周三
MON_2300 = datetime(2026, 11, 23, 23, 0).timestamp()  # 周一

def test_all_day():
    assert in_time_window([{"start":"00:00","end":"23:59","days":[0,1,2,3,4,5,6]}], now=WED_0900)

def test_empty_means_always():
    assert in_time_window([], now=WED_0900)

def test_weekday_gate():
    assert not in_time_window([{"start":"00:00","end":"23:59","days":[0]}], now=WED_0900)

def test_cross_midnight():
    w = [{"start":"22:00","end":"02:00","days":[0,1,2,3,4,5,6]}]
    assert in_time_window(w, now=MON_2300)
    assert not in_time_window(w, now=WED_0900)

def test_inside_range():
    assert in_time_window([{"start":"08:00","end":"12:00","days":[2]}], now=WED_0900)
