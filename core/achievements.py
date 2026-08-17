"""core/achievements.py：成就系统。

达成条件后解锁徽章，每个首次解锁奖励 REWARD_COINS 专注币。
持久化到 data/achievements.json。
"""
import datetime
import json
import os

from .config import DATA_DIR

REWARD_COINS = 20

ACHIEVEMENTS = [
    {"id": "first_focus", "name": "初学乍练",   "desc": "累计专注满 1 分钟", "icon": "⭐"},
    {"id": "focus_30",    "name": "小有所成",   "desc": "累计专注 30 分钟",  "icon": "🎯"},
    {"id": "focus_300",   "name": "持之以恒",   "desc": "累计专注 5 小时",   "icon": "🔥"},
    {"id": "focus_1200",  "name": "学霸之姿",   "desc": "累计专注 20 小时",  "icon": "👑"},
    {"id": "streak_30",   "name": "连续作战",   "desc": "单次连续专注 30 分钟", "icon": "⚡"},
    {"id": "streak_120",  "name": "心流状态",   "desc": "单次连续专注 2 小时",  "icon": "🌊"},
    {"id": "level_4",     "name": "加冕时刻",   "desc": "宠物升到 Lv.4",    "icon": "🎓"},
    {"id": "level_8",     "name": "至尊宠主",   "desc": "宠物升到 Lv.8",    "icon": "💎"},
    {"id": "buy_first",   "name": "第一桶金",   "desc": "在商店购买第一件物品", "icon": "🛒"},
    {"id": "furnish_3",   "name": "装修达人",   "desc": "个人空间摆放 3 件家具", "icon": "🛋️"},
    {"id": "escape_free", "name": "自律大师",   "desc": "从未逃跑",         "icon": "🛡️"},
]


class AchievementManager:
    def __init__(self):
        self.unlocked = {}  # id -> 解锁时间
        self._load()

    def _path(self):
        return os.path.join(DATA_DIR, "achievements.json")

    def _load(self):
        if os.path.exists(self._path()):
            try:
                with open(self._path(), "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                self.unlocked = dict(data.get("unlocked", {}))
            except (json.JSONDecodeError, OSError):
                pass
        self.save()

    def save(self):
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump({"unlocked": self.unlocked}, f, ensure_ascii=False, indent=2)

    @staticmethod
    def get(item_id):
        for item in ACHIEVEMENTS:
            if item["id"] == item_id:
                return item
        return None

    def evaluate(self, pet_state, inventory):
        """检查所有成就条件，返回本次新解锁的成就 id 列表（并持久化）。"""
        checks = {
            "first_focus": pet_state.total_focus_minutes >= 1,
            "focus_30": pet_state.total_focus_minutes >= 30,
            "focus_300": pet_state.total_focus_minutes >= 300,
            "focus_1200": pet_state.total_focus_minutes >= 1200,
            "streak_30": pet_state.best_streak >= 1800,
            "streak_120": pet_state.best_streak >= 7200,
            "level_4": pet_state.level >= 4,
            "level_8": pet_state.level >= 8,
            "buy_first": len(inventory.owned_furniture) >= 1,
            "furnish_3": sum(len(v) for v in inventory.placed_furniture.values()) >= 3,
            "escape_free": pet_state.escapes == 0,
        }
        newly = []
        for aid, cond in checks.items():
            if aid not in self.unlocked and cond:
                self.unlocked[aid] = datetime.datetime.now().isoformat(timespec="seconds")
                newly.append(aid)
        if newly:
            self.save()
        return newly