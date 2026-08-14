"""core/pet_state.py：桌宠养成状态（等级/经验/好感度/模式/逃跑次数）。

- xp：专注经验（秒）。等级由累计专注时长决定，升级后桌宠会长大/戴皇冠。
- affinity：好感度 0-100。学习缓慢增加，摸鱼/分心下降。
- mode：日常自习 daily / 考试冲刺 exam（更严格的阻断阈值）。

持久化到 data/pet_state.json。
"""
import json
import os

from .config import DATA_DIR

# 升到 Lv.N 需要的累计专注秒数（Lv1=0 起步）
LEVEL_XP_SECONDS = [0, 1800, 5400, 10800, 18000, 28800, 43200, 64800]


class PetState:
    def __init__(self):
        self.xp = 0.0
        self.level = 1
        self.affinity = 50.0
        self.mode = "daily"
        self.escapes = 0
        self.total_focus_minutes = 0.0
        self.total_distract_minutes = 0.0
        self.current_streak = 0.0
        self.best_streak = 0.0
        self._leveled = False
        self._load()

    # ---------- 持久化 ----------
    def _path(self):
        return os.path.join(DATA_DIR, "pet_state.json")

    def _load(self):
        if os.path.exists(self._path()):
            try:
                with open(self._path(), "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                self.xp = float(data.get("xp", 0.0))
                self.affinity = float(data.get("affinity", 50.0))
                self.mode = data.get("mode", "daily")
                self.escapes = int(data.get("escapes", 0))
                self.total_focus_minutes = float(data.get("total_focus_minutes", 0.0))
                self.total_distract_minutes = float(data.get("total_distract_minutes", 0.0))
                self.current_streak = float(data.get("current_streak", 0.0))
                self.best_streak = float(data.get("best_streak", 0.0))
            except (json.JSONDecodeError, OSError):
                pass
        self.level = self._level_from_xp()
        self.save()

    def save(self):
        data = {
            "xp": round(self.xp, 1),
            "level": self.level,
            "affinity": round(self.affinity, 1),
            "mode": self.mode,
            "escapes": self.escapes,
            "total_focus_minutes": round(self.total_focus_minutes, 1),
            "total_distract_minutes": round(self.total_distract_minutes, 1),
            "current_streak": round(self.current_streak, 1),
            "best_streak": round(self.best_streak, 1),
        }
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- 等级 ----------
    def _level_from_xp(self):
        level = 1
        for i, threshold in enumerate(LEVEL_XP_SECONDS):
            if self.xp >= threshold:
                level = i + 1
        return level

    def add_focus(self, seconds):
        self.xp += seconds
        self.affinity = min(100.0, self.affinity + 0.02 * seconds)
        self.total_focus_minutes += seconds / 60.0
        self.current_streak += seconds
        if self.current_streak > self.best_streak:
            self.best_streak = self.current_streak
        new_level = self._level_from_xp()
        if new_level > self.level:
            self.level = new_level
            self._leveled = True
        self.save()

    def add_distraction(self, seconds):
        self.affinity = max(0.0, self.affinity - 0.04 * seconds)
        self.total_distract_minutes += seconds / 60.0
        self.current_streak = 0.0  # 连续专注中断
        self.save()

    def consume_level_up(self):
        """返回并清除"刚升级"标记。"""
        if self._leveled:
            self._leveled = False
            return True
        return False

    def add_escape(self):
        self.escapes += 1
        self.affinity = max(0.0, self.affinity - 5.0)
        self.save()

    # ---------- 模式 ----------
    def set_mode(self, mode):
        self.mode = mode if mode in ("daily", "exam") else "daily"
        self.save()