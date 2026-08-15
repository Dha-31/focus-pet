"""core/checkin.py：每日打卡签到（v4.0.1）。

- 每天限一次；连续签到天数越多额外奖励越多
- 数据存 data/checkin.json：{last_date, streak, total_days}
- 奖励 = base_reward + (连续天数-1) * streak_bonus（集中配置可调）
"""
import datetime
import json
import os

from .config import DATA_DIR
from .settings import settings

DATE_FMT = "%Y-%m-%d"


class CheckIn:
    def __init__(self):
        self.last_date = ""      # 上次打卡日期
        self.streak = 0          # 连续签到天数
        self.total_days = 0      # 累计打卡天数
        self._load()

    def _path(self):
        return os.path.join(DATA_DIR, "checkin.json")

    def _load(self):
        if os.path.exists(self._path()):
            try:
                with open(self._path(), "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                self.last_date = str(data.get("last_date", ""))
                self.streak = int(data.get("streak", 0))
                self.total_days = int(data.get("total_days", 0))
            except (json.JSONDecodeError, OSError):
                pass
        self.save()

    def save(self):
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump({"last_date": self.last_date, "streak": self.streak,
                       "total_days": self.total_days}, f, ensure_ascii=False, indent=2)

    def _today(self):
        return datetime.date.today().strftime(DATE_FMT)

    def status(self):
        """返回 (今天是否已打卡, 当前连续天数, 累计天数)。"""
        return self.last_date == self._today(), self.streak, self.total_days

    def do(self):
        """执行打卡。返回 (奖励金币, 连续天数, 累计天数)；今天已打过返回 None。"""
        today = self._today()
        if self.last_date == today:
            return None
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime(DATE_FMT)
        self.streak = self.streak + 1 if self.last_date == yesterday else 1
        self.total_days += 1
        self.last_date = today
        base = float(settings.get("checkin.base_reward", 10))
        bonus = float(settings.get("checkin.streak_bonus", 2))
        reward = base + max(0, self.streak - 1) * bonus
        self.save()
        return reward, self.streak, self.total_days

