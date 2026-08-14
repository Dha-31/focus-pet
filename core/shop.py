"""core/shop.py：商店商品目录（装饰品 + 家具）。

装饰品：戴在宠物身上（帽子/蝴蝶结/眼镜/围巾/小花/皇冠）
家具：摆进个人空间（桌子/台灯/地毯/书架/绿植/窗户/沙发）
"""
ACCESSORIES = [
    {"id": "flower",     "name": "小花",       "price": 15, "kind": "flower"},
    {"id": "bow_pink",   "name": "粉色蝴蝶结",  "price": 20, "kind": "bow"},
    {"id": "scarf",      "name": "暖暖围巾",    "price": 25, "kind": "scarf"},
    {"id": "hat_red",    "name": "小红帽",      "price": 30, "kind": "hat"},
    {"id": "glasses",    "name": "酷酷眼镜",    "price": 40, "kind": "glasses"},
    {"id": "crown_gold", "name": "金皇冠",      "price": 80, "kind": "crown"},
]

FURNITURE = [
    {"id": "rug",       "name": "软软地毯",  "price": 20, "kind": "rug"},
    {"id": "lamp",      "name": "小台灯",    "price": 25, "kind": "lamp"},
    {"id": "plant",     "name": "绿植",      "price": 30, "kind": "plant"},
    {"id": "window",    "name": "大窗户",    "price": 35, "kind": "window"},
    {"id": "table",     "name": "学习桌",    "price": 40, "kind": "table"},
    {"id": "bookshelf", "name": "书架",      "price": 60, "kind": "bookshelf"},
    {"id": "sofa",      "name": "小沙发",    "price": 80, "kind": "sofa"},
]

MAX_FURNITURE_SLOTS = 6


def get_accessory(item_id):
    for item in ACCESSORIES:
        if item["id"] == item_id:
            return item
    return None


def get_furniture(item_id):
    for item in FURNITURE:
        if item["id"] == item_id:
            return item
    return None


def price_of(item):
    """商品价格（优先读集中配置，支持热更新）。"""
    from .settings import settings
    return settings.get(f"shop.prices.{item['id']}") or item["price"]