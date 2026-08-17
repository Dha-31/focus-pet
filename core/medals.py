"""core/medals.py：奖章系统（苹果健身 App 风格）。

- 每日奖章：每天重置（如"今日专注 30 分""零分心"）
- 每周奖章：每周重置（如"本周专注 5 小时""每周学习 5 天"）
- 每月奖章：每月重置（如"本月专注 20 小时""本月 20 次会话"）
- 里程碑（长期累计）在 core/achievements.py

数据来源：focus_log.json（学习会话：start / focus_minutes / distract_minutes）。
解锁记录持久化到 data/achievements.json 的 "medals" 字段。
"""
import datetime
import json
import os

from .config import DATA_DIR

REWARD_COINS = 20

MEDALS = [
    # ---- 每日 ----
    {"id": "daily_focus_30", "type": "daily",   "name": "每日专注 30 分", "desc": "今日专注满 30 分钟", "icon": "🎯"},
    {"id": "daily_focus_60", "type": "daily",   "name": "每日专注 1 小时", "desc": "今日专注满 60 分钟", "icon": "⭐"},
    {"id": "daily_session",  "type": "daily",   "name": "今日学习",       "desc": "今日完成 1 次学习会话", "icon": "📚"},
    {"id": "daily_clean",    "type": "daily",   "name": "零分心",         "desc": "今日学习全程零分心", "icon": "🛡️"},
    # ---- 每周 ----
    {"id": "weekly_focus_300", "type": "weekly", "name": "每周 5 小时",  "desc": "本周专注满 300 分钟", "icon": "🔥"},
    {"id": "weekly_focus_600", "type": "weekly", "name": "每周 10 小时", "desc": "本周专注满 600 分钟", "icon": "💪"},
    {"id": "weekly_5days",     "type": "weekly", "name": "每周 5 天",    "desc": "本周学习满 5 天", "icon": "📅"},
    # ---- 每月 ----
    {"id": "monthly_focus_1200",  "type": "monthly", "name": "每月 20 小时", "desc": "本月专注满 1200 分钟", "icon": "🏆"},
    {"id": "monthly_sessions_20", "type": "monthly", "name": "每月 20 次",   "desc": "本月完成 20 次学习会话", "icon": "🎓"},
]

TYPE_NAMES = [("daily", "每日奖章"), ("weekly", "每周奖章"), ("monthly", "每月奖章")]


class MedalManager:
    def __init__(self):
        self.unlocked = {}   # key("id:周期") -> 解锁时间
        self._load()

    def _path(self):
        return os.path.join(DATA_DIR, "achievements.json")

    def _load(self):
        try:
            with open(self._path(), "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            self.unlocked = dict(data.get("medals", {}) or {})
        except (OSError, json.JSONDecodeError):
            self.unlocked = {}

    def _save(self):
        try:
            with open(self._path(), "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {}
        data["medals"] = self.unlocked
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- 周期聚合 ----------
    def period_stats(self, now=None):
        now = now or datetime.datetime.now()
        today = now.date()
        week_start = today - datetime.timedelta(days=today.weekday())
        month = (today.year, today.month)
        stats = {
            "today_focus": 0.0, "today_distract": 0.0, "today_sessions": 0,
            "week_focus": 0.0, "week_days": set(),
            "month_focus": 0.0, "month_sessions": 0,
        }
        try:
            with open(os.path.join(DATA_DIR, "focus_log.json"), "r", encoding="utf-8-sig") as f:
                sessions = json.load(f)
        except (OSError, json.JSONDecodeError):
            sessions = []
        for s in sessions:
            if not isinstance(s, dict):
                continue
            try:
                st = datetime.datetime.fromisoformat(str(s.get("start", "")))
            except ValueError:
                continue
            d = st.date()
            fm = float(s.get("focus_minutes", 0) or 0)
            dm = float(s.get("distract_minutes", 0) or 0)
            if d == today:
                stats["today_focus"] += fm
                stats["today_distract"] += dm
                stats["today_sessions"] += 1
            if week_start <= d <= today:
                stats["week_focus"] += fm
                stats["week_days"].add(d.isoformat())
            if (d.year, d.month) == month:
                stats["month_focus"] += fm
                stats["month_sessions"] += 1
        stats["week_days"] = len(stats["week_days"])
        return stats

    # ---------- 判定 ----------
    def _period_key(self, mtype, now):
        today = now.date()
        if mtype == "daily":
            return today.isoformat()
        if mtype == "weekly":
            week_start = today - datetime.timedelta(days=today.weekday())
            return week_start.isoformat()
        return now.strftime("%Y-%m")

    def evaluate(self, now=None):
        """判定所有奖章，返回新解锁的奖章 id 列表（并持久化）。"""
        now = now or datetime.datetime.now()
        stats = self.period_stats(now)
        checks = {
            "daily_focus_30": stats["today_focus"] >= 30,
            "daily_focus_60": stats["today_focus"] >= 60,
            "daily_session": stats["today_sessions"] >= 1,
            "daily_clean": stats["today_distract"] <= 0 and stats["today_sessions"] >= 1,
            "weekly_focus_300": stats["week_focus"] >= 300,
            "weekly_focus_600": stats["week_focus"] >= 600,
            "weekly_5days": stats["week_days"] >= 5,
            "monthly_focus_1200": stats["month_focus"] >= 1200,
            "monthly_sessions_20": stats["month_sessions"] >= 20,
        }
        newly = []
        for mid, cond in checks.items():
            m = next((x for x in MEDALS if x["id"] == mid), None)
            if not m:
                continue
            key = f"{mid}:{self._period_key(m['type'], now)}"
            if cond and key not in self.unlocked:
                self.unlocked[key] = now.isoformat(timespec="seconds")
                newly.append(mid)
        if newly:
            self._save()
        return newly

    def status(self, now=None):
        """返回每个奖章当前周期的解锁状态。"""
        now = now or datetime.datetime.now()
        out = []
        for m in MEDALS:
            key = f"{m['id']}:{self._period_key(m['type'], now)}"
            out.append({"id": m["id"], "type": m["type"], "unlocked": key in self.unlocked})
        return out
