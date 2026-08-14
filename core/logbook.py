"""分心日志：按时间线记录事件（分心、教宠物、会话开始/结束等）。"""
import datetime
import json
import os

from .config import DATA_DIR

MAX_ENTRIES = 2000


def log_event(kind, detail):
    path = os.path.join(DATA_DIR, "events.json")
    events = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                events = json.load(f)
        except (json.JSONDecodeError, OSError):
            events = []
    events.append({
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "kind": kind,
        "detail": detail,
    })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events[-MAX_ENTRIES:], f, ensure_ascii=False, indent=2)


def read_events(limit=50):
    path = os.path.join(DATA_DIR, "events.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            events = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    return events[-limit:] if limit else events