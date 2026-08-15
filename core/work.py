"""core/work.py：工作时钟（宠物打工赚币，v4.0.1）。

- 设定时长后开始倒计时；到期结算专注币（跨重启不丢，继续倒计时）
- 中途取消无奖励；数据存 data/work.json
- 工资 = 时长(分钟) * work.rate_per_min（等级加成由调用方算）
"""
import json
import os
import time

from .config import DATA_DIR
from .settings import settings


class WorkClock:
    def __init__(self):
        self.active = False
        self.start_ts = 0.0
        self.duration_min = 0
        self._load()

    def _path(self):
        return os.path.join(DATA_DIR, "work.json")

    def _load(self):
        if os.path.exists(self._path()):
            try:
                with open(self._path(), "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                self.active = bool(data.get("active", False))
                self.start_ts = float(data.get("start_ts", 0))
                self.duration_min = int(data.get("duration_min", 0))
            except (json.JSONDecodeError, OSError):
                pass
        self.save()

    def save(self):
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump({"active": self.active, "start_ts": self.start_ts,
                       "duration_min": self.duration_min}, f, ensure_ascii=False, indent=2)

    def start(self, duration_min):
        """开始打工。已在打工返回 False。"""
        if self.active:
            return False
        self.active = True
        self.start_ts = time.time()
        self.duration_min = int(duration_min)
        self.save()
        return True

    def cancel(self):
        """中途取消，无奖励。"""
        if not self.active:
            return False
        self.active = False
        self.start_ts = 0.0
        self.duration_min = 0
        self.save()
        return True

    def remaining(self):
        """剩余秒数；未在打工返回 0。"""
        if not self.active:
            return 0
        total = self.duration_min * 60
        return max(0, total - (time.time() - self.start_ts))

    def is_done(self):
        """打工时间是否已到。"""
        return self.active and self.remaining() <= 0

    def finish(self):
        """时间到结算。返回基础工资（金币）；未在打工/未到期返回 None。"""
        if not self.active or not self.is_done():
            return None
        rate = float(settings.get("work.rate_per_min", 2.0))
        duration = self.duration_min
        self.active = False
        self.start_ts = 0.0
        self.duration_min = 0
        self.save()
        return duration * rate

