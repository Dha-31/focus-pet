"""声明制学习会话：开始前告诉宠物目标，结束时写总结到 focus_log.json。"""
import datetime
import json
import os
import time

from .config import DATA_DIR


class StudySession:
    def __init__(self):
        self.goal = None
        self.start_time = None
        self.focus_seconds = 0.0
        self.distract_seconds = 0.0
        self.active = False

    def start(self, goal="学习"):
        if self.active:
            return False
        self.goal = goal
        self.start_time = time.time()
        self.focus_seconds = 0.0
        self.distract_seconds = 0.0
        self.active = True
        return True

    def tick(self, is_focus, dt=1.0):
        if not self.active:
            return
        if is_focus:
            self.focus_seconds += dt
        else:
            self.distract_seconds += dt

    def end(self):
        """结束会话，返回总结 dict（同时写入 focus_log.json）。"""
        if not self.active:
            return None
        self.active = False
        summary = {
            "goal": self.goal,
            "start": datetime.datetime.fromtimestamp(self.start_time).isoformat(timespec="seconds"),
            "end": datetime.datetime.now().isoformat(timespec="seconds"),
            "focus_minutes": round(self.focus_seconds / 60.0, 1),
            "distract_minutes": round(self.distract_seconds / 60.0, 1),
        }
        self._append_log(summary)
        self.goal = None
        return summary

    @staticmethod
    def _append_log(entry):
        path = os.path.join(DATA_DIR, "focus_log.json")
        logs = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    logs = json.load(f)
            except (json.JSONDecodeError, OSError):
                logs = []
        logs.append(entry)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    @staticmethod
    def read_log(limit=None):
        path = os.path.join(DATA_DIR, "focus_log.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        return logs[-limit:] if limit else logs