"""core/economy.py：专注币经济 + 库存（装饰品/家具）。

- 专注 1 分钟 = 1 个专注币（COIN_PER_MINUTE）
- 库存持久化到 data/inventory.json
"""
import json
import os

from .config import DATA_DIR
from .settings import settings

COIN_PER_MINUTE = 1.0


class Inventory:
    def __init__(self):
        self.coins = 0.0
        self.owned_accessories = []
        self.owned_furniture = []
        self.equipped_accessory = None
        self.placed_furniture = []
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
                self.owned_accessories = list(data.get("owned_accessories", []))
                self.owned_furniture = list(data.get("owned_furniture", []))
                self.equipped_accessory = data.get("equipped_accessory")
                self.placed_furniture = list(data.get("placed_furniture", []))
            except (json.JSONDecodeError, OSError):
                pass
        self.save()

    def save(self):
        data = {
            "coins": round(self.coins, 1),
            "owned_accessories": self.owned_accessories,
            "owned_furniture": self.owned_furniture,
            "equipped_accessory": self.equipped_accessory,
            "placed_furniture": self.placed_furniture,
        }
        with open(self._path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---------- 经济 ----------
    def earn(self, seconds):
        """专注加币（汇率从集中配置读取，可热更新）。返回本次赚到的币数。"""
        rate = settings.get("economy.coin_per_minute", COIN_PER_MINUTE)
        earned = seconds / 60.0 * rate
        self.coins += earned
        self.save()
        return earned

    def can_afford(self, price):
        return self.coins >= price

    def add_coins(self, amount):
        """直接加币（成就奖励等）。"""
        self.coins = max(0.0, self.coins + amount)
        self.save()

    def penalize(self, amount):
        """扣币（逃跑惩罚等）。"""
        self.coins = max(0.0, self.coins - amount)
        self.save()

    # ---------- 购买 ----------
    def buy(self, item, price=None):
        """购买商品（价格优先读集中配置）。返回是否成功。"""
        if price is None:
            price = settings.get(f"shop.prices.{item['id']}") or item["price"]
        if self.coins < price:
            return False
        self.coins -= price
        if item["id"] in ACCESSORY_IDS and item["id"] not in self.owned_accessories:
            self.owned_accessories.append(item["id"])
        elif item["id"] not in self.owned_furniture:
            self.owned_furniture.append(item["id"])
        self.save()
        return True

    # ---------- 装饰品 ----------
    def equip(self, accessory_id):
        if accessory_id in self.owned_accessories:
            self.equipped_accessory = accessory_id
            self.save()
            return True
        return False

    def unequip(self):
        self.equipped_accessory = None
        self.save()

    # ---------- 家具 ----------
    def place(self, furniture_id):
        if furniture_id in self.owned_furniture and len(self.placed_furniture) < MAX_FURNITURE_SLOTS:
            self.placed_furniture.append(furniture_id)
            self.save()
            return True
        return False

    def remove_furniture(self, furniture_id):
        if furniture_id in self.placed_furniture:
            self.placed_furniture.remove(furniture_id)
            self.save()
            return True
        return False


from .shop import ACCESSORIES, MAX_FURNITURE_SLOTS  # noqa: E402

ACCESSORY_IDS = {item["id"] for item in ACCESSORIES}