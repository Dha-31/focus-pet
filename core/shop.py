"""core/shop.py：商店商品目录（家具）。

家具按地图（场景）分类：温馨小屋 / 星空书房 / 海边 / 森林。
在哪个地图分类买的家具，只能在那个地图用（饰品功能已移除）。
"""
FURNITURE = [
    # 温馨小屋
    {"id": "rug",       "name": "软软地毯", "price": 1600, "kind": "rug",       "scene": "cozy"},
    {"id": "lamp",      "name": "小台灯",   "price": 1800, "kind": "lamp",      "scene": "cozy"},
    {"id": "plant",     "name": "绿植",     "price": 2000, "kind": "plant",     "scene": "cozy"},
    {"id": "window",    "name": "大窗户",   "price": 3600, "kind": "window",    "scene": "cozy"},
    {"id": "table",     "name": "学习桌",   "price": 4400, "kind": "table",     "scene": "cozy"},
    {"id": "bookshelf", "name": "书架",     "price": 4800, "kind": "bookshelf", "scene": "cozy"},
    {"id": "sofa",      "name": "小沙发",   "price": 5600, "kind": "sofa",      "scene": "cozy"},
    {"id": "fridge",    "name": "小冰箱",   "price": 6000, "kind": "fridge",    "scene": "cozy"},
    {"id": "tv",        "name": "电视机",   "price": 6800, "kind": "tv",        "scene": "cozy"},
    {"id": "clock",     "name": "挂钟",     "price": 1600, "kind": "clock",     "scene": "cozy"},
    {"id": "armchair",  "name": "单人沙发", "price": 5200, "kind": "armchair",  "scene": "cozy"},
    # 星空书房
    {"id": "star_rug",  "name": "星空地毯", "price": 2400, "kind": "star_rug",  "scene": "star"},
    {"id": "moon_lamp", "name": "月亮灯",   "price": 2800, "kind": "moon_lamp", "scene": "star"},
    {"id": "planet",    "name": "星球摆件", "price": 3200, "kind": "planet",    "scene": "star"},
    {"id": "telescope", "name": "望远镜",   "price": 7600, "kind": "telescope", "scene": "star"},
    {"id": "star_desk", "name": "星云书桌", "price": 5200, "kind": "star_desk", "scene": "star"},
    {"id": "star_chair","name": "星光椅子", "price": 2400, "kind": "star_chair","scene": "star"},
    {"id": "star_books","name": "书堆",     "price": 2000, "kind": "star_books","scene": "star"},
    {"id": "aurora",    "name": "极光挂画", "price": 6000, "kind": "aurora",    "scene": "star"},
    # 星空田野露营
    {"id": "tent",      "name": "露营帐篷", "price": 6800, "kind": "tent",      "scene": "star"},
    {"id": "campfire",  "name": "篝火",     "price": 4000, "kind": "campfire",  "scene": "star"},
    {"id": "picnic",    "name": "野餐垫",   "price": 2400, "kind": "picnic",    "scene": "star"},
    {"id": "camp_lamp", "name": "露营灯",   "price": 2800, "kind": "camp_lamp", "scene": "star"},
    {"id": "camp_chair","name": "露营椅",   "price": 2400, "kind": "camp_chair","scene": "star"},
    {"id": "cooler",    "name": "保温箱",   "price": 3600, "kind": "cooler",    "scene": "star"},
    # 海边
    {"id": "beach_umbrella", "name": "遮阳伞", "price": 3600, "kind": "beach_umbrella", "scene": "sea"},
    {"id": "beach_chair",    "name": "沙滩椅", "price": 2800, "kind": "beach_chair",    "scene": "sea"},
    {"id": "sandcastle",     "name": "沙堡",   "price": 2400, "kind": "sandcastle",     "scene": "sea"},
    {"id": "shell",          "name": "贝壳",   "price": 1600, "kind": "shell",          "scene": "sea"},
    {"id": "fish_tank",      "name": "鱼缸",   "price": 6000, "kind": "fish_tank",      "scene": "sea"},
    {"id": "hammock",        "name": "吊床",   "price": 5200, "kind": "hammock",        "scene": "sea"},
    {"id": "sea_rug",        "name": "沙毯",   "price": 2000, "kind": "sea_rug",        "scene": "sea"},
    {"id": "crab",           "name": "小螃蟹", "price": 1600, "kind": "crab",           "scene": "sea"},
    # 森林
    {"id": "tree",       "name": "小树",     "price": 2400, "kind": "tree",       "scene": "forest"},
    {"id": "mushroom",   "name": "蘑菇",     "price": 1600, "kind": "mushroom",   "scene": "forest"},
    {"id": "log",        "name": "木桩",     "price": 2000, "kind": "log",        "scene": "forest"},
    {"id": "birdhouse",  "name": "鸟屋",     "price": 2800, "kind": "birdhouse",  "scene": "forest"},
    {"id": "swing",      "name": "秋千",     "price": 5200, "kind": "swing",      "scene": "forest"},
    {"id": "stump_table","name": "树桩桌",   "price": 3600, "kind": "stump_table","scene": "forest"},
    {"id": "beehive",    "name": "蜂箱",     "price": 3200, "kind": "beehive",    "scene": "forest"},
    {"id": "forest_lamp","name": "萤火灯",   "price": 4400, "kind": "forest_lamp","scene": "forest"},
]

# 家具按地图（场景）分类
FURNITURE_SCENES = [
    ("cozy", "温馨小屋"),
    ("star", "星空书房"),
    ("sea", "海边"),
    ("forest", "森林"),
]


def get_furniture(item_id):
    for item in FURNITURE:
        if item["id"] == item_id:
            return item
    return None


def price_of(item):
    """商品价格（优先读集中配置，支持热更新）。"""
    from .settings import settings
    return settings.get(f"shop.prices.{item['id']}") or item["price"]
