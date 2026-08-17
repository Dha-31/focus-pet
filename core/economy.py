"""core/economy.py：专注币经济 + 库存（家具）。

- 专注 1 分钟 = 1 个专注币（COIN_PER_MINUTE）
- 库存持久化到 data/inventory.json
- 家具按地图（场景）分类摆放；饰品功能已移除
"""
import json
import os

from .config import DATA_DIR
from .settings import settings

COIN_PER_MINUTE = 1.0


class Inventory:
    def __init__(self):
        self.coins = 0.0
        self.owned_furniture = []
        self.placed_furniture = {}   # scene -> [fid]（家具留在购买时所在的地图）
        self._load()

    # ---------- 持久化 ----------
    def _path(self):
        return os.path.join(DATA_DIR, "inventory.json")

    def _load(self):
        if os.path.exists(self._path()):
            try:
                with open(self._path(), "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                self.coins = float(data.get("coins", 0.0))
                self.owned_furniture = list(data.get("owned_furniture", []))
                _pf = data.get("placed_furniture")
                if isinstance(_pf, dict):
                    self.placed_furniture = {k: list(v) for k, v in _pf.items()}
                elif isinstance(_pf, list):
                    self.placed_furniture = {"cozy": list(_pf)}
                else:
                    self.placed_furniture = {}
            except (json.JSONDecodeError, OSError):
                pass
        self.save()

    def save(self):
        data = {
            "coins": round(self.coins, 1),
            "owned_furniture": self.owned_furniture,
            "placed_furniture": self.placed_furniture,
        }
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- 经济 ----------
    def earn(self, seconds):
        rate = settings.get("economy.coin_per_minute", COIN_PER_MINUTE)
        earned = seconds / 60.0 * rate
        self.coins += earned
        self.save()
        return earned

    def can_afford(self, price):
        return self.coins >= price

    def add_coins(self, amount):
        self.coins = max(0.0, self.coins + amount)
        self.save()

    def penalize(self, amount):
        self.coins = max(0.0, self.coins - amount)
        self.save()

    # ---------- 购买（家具） ----------
    def buy(self, item, price=None):
        if price is None:
            price = settings.get(f"shop.prices.{item['id']}") or item["price"]
        if self.coins < price:
            return False
        self.coins -= price
        if item["id"] not in self.owned_furniture:
            self.owned_furniture.append(item["id"])
        self.save()
        return True

    # ---------- 家具摆放（按地图） ----------
    def place(self, furniture_id, scene="cozy"):
        if furniture_id in self.owned_furniture:
            self.placed_furniture.setdefault(scene, [])
            if furniture_id not in self.placed_furniture[scene]:
                self.placed_furniture[scene].append(furniture_id)
                self.save()
                return True
        return False

    def remove_furniture(self, furniture_id, scene="cozy"):
        lst = self.placed_furniture.get(scene)
        if lst and furniture_id in lst:
            lst.remove(furniture_id)
            self.save()
            return True
        return False

    def placed_in(self, scene):
        return list(self.placed_furniture.get(scene, []))
