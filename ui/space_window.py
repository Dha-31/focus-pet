"""ui/space_window.py：个人空间——宠物房间 + 家具 + 宠物入住。"""
import tkinter as tk
from tkinter import messagebox

from core import shop
from ui import pet_renderer
from ui.theme_ui import accent_button, style_window

W, H = 1000, 940
FLOOR_Y = int(H * 0.35)   # 分界线上移，地面占底部约 2/3

# 家具摆放槽位（6 个）
SLOTS = [
    (70, FLOOR_Y + 60), (190, FLOOR_Y + 60), (310, FLOOR_Y + 60),
    (430, FLOOR_Y + 60), (130, FLOOR_Y + 110), (430, FLOOR_Y + 110),
]
# v4.0.1：空间场景切换（二维小世界第一步）
DEFAULT_SCENE = "cozy"
SCENES = {
    "cozy":   {"name": "温馨小屋", "wall": "#fdf1dd", "floor": "#d9b380",
               "floor_line": "#c49a66", "trim": "#b8894f", "accent": "#e8b4c8"},
    "star":   {"name": "星空田野", "wall": "#1c2340", "floor": "#7fae5a",
               "floor_line": "#6d9a4a", "trim": "#5a6aa0", "accent": "#ffd166"},
    "sea":    {"name": "海边", "wall": "#bfe3ff", "floor": "#e8d9a0",
               "floor_line": "#d4c27f", "trim": "#8a9bb0", "accent": "#5aa0e0"},
    "forest": {"name": "森林", "wall": "#d9eec9", "floor": "#a8c77a",
               "floor_line": "#8fb064", "trim": "#6d9448", "accent": "#5cb85c"},
}


def _space_path():
    import json
    import os
    from core.config import DATA_DIR
    return os.path.join(DATA_DIR, "space.json")


def load_scene():
    import json
    import os
    try:
        with open(_space_path(), "r", encoding="utf-8-sig") as f:
            s = json.load(f).get("scene", DEFAULT_SCENE)
        return s if s in SCENES else DEFAULT_SCENE
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SCENE


def save_scene(scene):
    import json
    if scene not in SCENES:
        scene = DEFAULT_SCENE
    with open(_space_path(), "w", encoding="utf-8") as f:
        json.dump({"scene": scene}, f, ensure_ascii=False, indent=2)


def load_layout(scene):
    """读取空间布局：家具位置（fid->[x,y] 设计坐标）+ 小猫位置。"""
    import json
    try:
        with open(_space_path(), "r", encoding="utf-8-sig") as f:
            d = json.load(f)
        furn = dict(d.get("furniture_pos", {}) or {})
        pet = d.get("pet_pos")
        if isinstance(pet, (list, tuple)) and len(pet) == 2:
            pet = (float(pet[0]), float(pet[1]))
        else:
            pet = (W / 2, int(H * 0.62) + 18)
        return furn, pet
    except (OSError, json.JSONDecodeError, TypeError):
        return {}, (W / 2, int(H * 0.62) + 18)


def save_layout(scene, furn_pos, pet_pos):
    import json
    with open(_space_path(), "w", encoding="utf-8") as f:
        json.dump({"scene": scene,
                   "furniture_pos": {k: [round(v[0], 1), round(v[1], 1)] for k, v in furn_pos.items()},
                   "pet_pos": [round(pet_pos[0], 1), round(pet_pos[1], 1)]},
                  f, ensure_ascii=False, indent=2)


class SpaceWindow:
    def __init__(self, parent, inventory, pet):
        self.inventory = inventory
        self.pet = pet  # PetApp 实例（读取皮肤/等级/表情/装饰）
        self.root = tk.Toplevel(parent)
        self.root.title("我的空间")
        self.root.geometry(f"{W}x{H + 46}")
        style_window(self.root)

        self.scene = load_scene()
        self._furn_pos, self._pet_pos = load_layout(self.scene)
        self._drag = None   # ("fur", fid) / ("pet", None)
        self.canvas = tk.Canvas(self.root, bg="#fdf6ec", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        bar = tk.Frame(self.root)
        bar.pack(pady=6)
        tk.Label(bar, text="场景:", font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(6, 2))
        self._scene_var = tk.StringVar(value=self.scene)
        tk.OptionMenu(bar, self._scene_var, *list(SCENES.keys()), command=self._switch_scene).pack(side="left", padx=4)
        tk.Button(bar, text="移除最后一件家具", command=self._remove_last).pack(side="left", padx=6)
        accent_button(bar, "关闭", self.root.destroy).pack(side="left", padx=6)
        self._draw()

    # ---------- 房间 ----------
    def _draw_room(self, cw, ch):
        c = self.canvas
        s = SCENES.get(self.scene, SCENES[DEFAULT_SCENE])
        fy = int(ch * 0.62)
        # 墙
        c.create_rectangle(0, 0, cw, fy, fill=s["wall"], outline="")
        # 地板
        c.create_rectangle(0, fy, cw, ch, fill=s["floor"], outline="")
        for i in range(0, cw, 46):
            c.create_line(i, fy, i, ch, fill=s["floor_line"])
        # 踢脚线
        c.create_line(0, fy, cw, fy, fill=s["trim"], width=3)
        self._draw_scene_decor(c, cw, fy, s)

    def _draw_furniture(self, kind, x, y):
        c = self.canvas
        if kind == "rug":
            c.create_oval(x - 80, y - 26, x + 80, y + 26, fill="#e8b4c8", outline="#c98aa2")
        elif kind == "table":
            c.create_rectangle(x - 55, y - 30, x + 55, y - 12, fill="#a9744a", outline="#7d5230")
            c.create_line(x - 40, y - 12, x - 40, y + 22, fill="#7d5230", width=4)
            c.create_line(x + 40, y - 12, x + 40, y + 22, fill="#7d5230", width=4)
        elif kind == "lamp":
            c.create_line(x, y + 18, x, y - 22, fill="#555", width=3)
            c.create_polygon(x - 22, y - 22, x + 22, y - 22, x, y - 46, fill="#ffd166", outline="#d0a020")
            c.create_oval(x - 20, y - 20, x + 20, y + 2, fill="#fff3c4", outline="")
        elif kind == "plant":
            c.create_polygon(x - 14, y + 16, x + 14, y + 16, x, y - 26, fill="#5cb85c", outline="#3a7d3a")
            c.create_oval(x - 18, y + 10, x + 18, y + 30, fill="#c97a4a", outline="#8f4f2a")
        elif kind == "window":
            c.create_rectangle(x - 60, y - 50, x + 60, y + 30, fill="#bfe3ff", outline="#8a6d4a", width=4)
            c.create_line(x, y - 50, x, y + 30, fill="#8a6d4a", width=2)
            c.create_line(x - 60, y - 10, x + 60, y - 10, fill="#8a6d4a", width=2)
        elif kind == "bookshelf":
            c.create_rectangle(x - 45, y - 50, x + 45, y + 22, fill="#a9744a", outline="#7d5230", width=3)
            for sy in (-30, -6):
                c.create_line(x - 42, y + sy, x + 42, y + sy, fill="#7d5230", width=2)
            for bx, color in ((x - 34, "#e05a5a"), (x - 18, "#5aa0e0"), (x - 2, "#5cb85c"), (x + 14, "#e0a020")):
                c.create_rectangle(bx, y - 42, bx + 12, y - 12, fill=color, outline="")
        elif kind == "sofa":
            c.create_rectangle(x - 60, y - 34, x + 60, y + 20, fill="#7db6e0", outline="#4a7ba0", width=3)
            c.create_rectangle(x - 66, y - 44, x - 50, y + 20, fill="#7db6e0", outline="#4a7ba0", width=3)
            c.create_rectangle(x + 50, y - 44, x + 66, y + 20, fill="#7db6e0", outline="#4a7ba0", width=3)
        # ---- 星空书房 ----
        elif kind == "star_rug":
            c.create_oval(x - 70, y - 18, x + 70, y + 18, fill="#2a3158", outline="#4a5478")
            for sx, sy in ((-30, -4), (0, 6), (28, -2)):
                c.create_text(x + sx, y + sy, text="✦", fill="#ffd166", font=("Microsoft YaHei UI", 9))
        elif kind == "moon_lamp":
            c.create_line(x, y + 20, x, y - 8, fill="#555", width=3)
            c.create_arc(x - 26, y - 40, x + 26, y - 8, start=180, extent=180,
                         fill="#ffd166", outline="#d0a020")
        elif kind == "planet":
            c.create_oval(x - 18, y - 18, x + 18, y + 18, fill="#e07a2f", outline="#b05a1a")
            c.create_oval(x - 28, y - 6, x + 28, y + 6, outline="#ffd166", width=3)
        elif kind == "telescope":
            c.create_rectangle(x - 9, y - 34, x + 9, y + 12, fill="#6a5acd", outline="#4a3a9a")
            c.create_polygon(x - 24, y - 34, x + 24, y - 34, x, y - 58,
                             fill="#6a5acd", outline="#4a3a9a")
            c.create_line(x, y - 42, x + 16, y - 12, fill="#4a3a9a", width=2)
        # ---- 海边 ----
        elif kind == "beach_umbrella":
            c.create_line(x, y + 22, x, y - 34, fill="#8a6d4a", width=3)
            c.create_polygon(x - 36, y - 34, x + 36, y - 34, x, y - 76,
                             fill="#ff9ec7", outline="#e0709a")
            c.create_line(x, y - 34, x - 36, y - 76, fill="#e0709a", width=2)
            c.create_line(x, y - 34, x + 36, y - 76, fill="#e0709a", width=2)
        elif kind == "beach_chair":
            c.create_rectangle(x - 30, y - 28, x + 8, y - 12, fill="#5aa0e0", outline="#3a70a8", width=2)
            c.create_line(x - 30, y - 12, x - 18, y + 20, fill="#8a6d4a", width=4)
            c.create_line(x + 8, y - 12, x + 20, y + 20, fill="#8a6d4a", width=4)
        elif kind == "sandcastle":
            c.create_rectangle(x - 32, y - 16, x + 32, y + 16, fill="#e8d9a0", outline="#c4b070")
            c.create_rectangle(x - 18, y - 34, x + 18, y - 16, fill="#e8d9a0", outline="#c4b070")
            c.create_polygon(x - 18, y - 34, x + 18, y - 34, x, y - 52,
                             fill="#e8d9a0", outline="#c4b070")
        elif kind == "shell":
            c.create_oval(x - 22, y - 14, x + 22, y + 14, fill="#ffd9e8", outline="#e0a0b8")
            c.create_line(x - 22, y, x + 22, y, fill="#e0a0b8", width=2)
            c.create_line(x, y - 14, x, y + 14, fill="#e0a0b8", width=2)
        # ---- 森林 ----
        elif kind == "tree":
            c.create_polygon(x - 26, y + 16, x + 26, y + 16, x, y - 42,
                             fill="#4aa858", outline="#3a8a46")
            c.create_polygon(x - 20, y - 10, x + 20, y - 10, x, y - 60,
                             fill="#5cb85c", outline="#4aa858")
            c.create_rectangle(x - 5, y + 16, x + 5, y + 26, fill="#8a5a30", outline="")
        elif kind == "mushroom":
            c.create_rectangle(x - 8, y + 2, x + 8, y + 18, fill="#f0e6d0", outline="#d0b890")
            c.create_oval(x - 22, y - 12, x + 22, y + 10, fill="#e05050", outline="#b03030")
            c.create_oval(x - 12, y - 5, x - 5, y + 2, fill="#fff", outline="")
            c.create_oval(x + 4, y - 9, x + 11, y - 2, fill="#fff", outline="")
        elif kind == "log":
            c.create_rectangle(x - 28, y - 10, x + 28, y + 10, fill="#a9744a", outline="#7d5230")
            c.create_oval(x - 28, y - 14, x + 28, y + 12, fill="#c9975c", outline="#7d5230")
            c.create_oval(x - 10, y - 5, x + 2, y + 5, fill="#8a5a30", outline="")
        elif kind == "birdhouse":
            c.create_rectangle(x - 18, y - 18, x + 18, y + 16, fill="#e0a24a", outline="#b07a2a")
            c.create_polygon(x - 20, y - 18, x + 20, y - 18, x, y - 38,
                             fill="#e05050", outline="#b03030")
            c.create_oval(x - 6, y - 7, x + 6, y + 5, fill="#4a3728", outline="")
        # ---- 温馨小屋新增 ----
        elif kind == "fridge":
            c.create_rectangle(x - 22, y - 38, x + 22, y + 20, fill="#e8f4f8", outline="#8ab8c8", width=2)
            c.create_line(x, y - 38, x, y - 4, fill="#8ab8c8", width=2)
            c.create_oval(x - 9, y - 28, x - 3, y - 22, fill="#8ab8c8", outline="")
        elif kind == "tv":
            c.create_rectangle(x - 34, y - 30, x + 34, y + 12, fill="#333", outline="#111", width=3)
            c.create_rectangle(x - 28, y - 24, x + 28, y + 6, fill="#9fd8ff", outline="")
            c.create_line(x - 8, y + 12, x - 4, y + 24, fill="#444", width=3)
            c.create_line(x + 8, y + 12, x + 4, y + 24, fill="#444", width=3)
        elif kind == "clock":
            c.create_oval(x - 20, y - 20, x + 20, y + 20, fill="#fff8ee", outline="#8a6d4a", width=3)
            c.create_line(x, y, x, y - 12, fill="#555", width=2)
            c.create_line(x, y, x + 9, y + 4, fill="#555", width=2)
            c.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#555", outline="")
        elif kind == "armchair":
            c.create_rectangle(x - 40, y - 28, x + 40, y + 18, fill="#c98aa2", outline="#a06a80", width=2)
            c.create_rectangle(x - 46, y - 38, x - 32, y + 18, fill="#c98aa2", outline="#a06a80", width=2)
            c.create_rectangle(x + 32, y - 38, x + 46, y + 18, fill="#c98aa2", outline="#a06a80", width=2)
        # ---- 星空书房新增 ----
        elif kind == "star_desk":
            c.create_rectangle(x - 50, y - 24, x + 50, y - 10, fill="#4a5478", outline="#2a3158", width=2)
            c.create_line(x - 36, y - 10, x - 36, y + 20, fill="#2a3158", width=4)
            c.create_line(x + 36, y - 10, x + 36, y + 20, fill="#2a3158", width=4)
            c.create_text(x, y - 34, text="✦", fill="#ffd166", font=("Microsoft YaHei UI", 9))
        elif kind == "star_chair":
            c.create_rectangle(x - 20, y - 26, x + 20, y - 10, fill="#5a6aa0", outline="#3a4a7a", width=2)
            c.create_rectangle(x - 22, y - 30, x - 16, y - 8, fill="#5a6aa0", outline="#3a4a7a", width=2)
            c.create_line(x - 14, y - 10, x - 10, y + 20, fill="#3a4a7a", width=4)
            c.create_line(x + 14, y - 10, x + 10, y + 20, fill="#3a4a7a", width=4)
        elif kind == "star_books":
            for bx, color in ((x - 22, "#e05a5a"), (x - 10, "#5aa0e0"), (x + 2, "#5cb85c")):
                c.create_rectangle(bx, y - 18, bx + 11, y + 14, fill=color, outline="")
            c.create_rectangle(x - 16, y - 24, x + 8, y - 16, fill="#e0a020", outline="")
        elif kind == "aurora":
            c.create_rectangle(x - 30, y - 34, x + 30, y + 14, fill="#2a3158", outline="#4a5478", width=2)
            for i in range(4):
                c.create_line(x - 24 + i * 12, y - 30, x - 16 + i * 12, y + 10,
                              fill=["#6bff9e", "#6bc9ff", "#ff9ec7", "#b48cff"][i], width=3)
        # ---- 海边新增 ----
        elif kind == "fish_tank":
            c.create_oval(x - 26, y - 22, x + 26, y + 22, fill="#bfe3ff", outline="#5a8aa0", width=2)
            c.create_oval(x - 18, y - 2, x - 10, y + 6, fill="#e0709a", outline="")
            c.create_polygon(x - 18, y - 2, x - 24, y - 7, x - 16, y - 8, fill="#e0709a", outline="")
            c.create_oval(x + 6, y - 8, x + 13, y - 1, fill="#ffb84d", outline="")
        elif kind == "hammock":
            c.create_line(x - 34, y - 34, x - 30, y + 10, fill="#7d5230", width=3)
            c.create_line(x + 34, y - 34, x + 30, y + 10, fill="#7d5230", width=3)
            c.create_arc(x - 30, y - 8, x + 30, y + 24, start=180, extent=180,
                         fill="#5aa0e0", outline="#3a70a8", width=2)
        elif kind == "sea_rug":
            c.create_oval(x - 72, y - 22, x + 72, y + 22, fill="#f2e3b6", outline="#d9c48a")
            c.create_text(x, y, text="🐚", font=("Segoe UI Emoji", 12))
        elif kind == "crab":
            c.create_oval(x - 18, y - 12, x + 18, y + 14, fill="#e05050", outline="#b03030")
            c.create_line(x - 20, y - 2, x - 30, y - 12, fill="#e05050", width=3)
            c.create_line(x - 20, y - 2, x - 30, y + 6, fill="#e05050", width=3)
            c.create_line(x + 20, y - 2, x + 30, y - 12, fill="#e05050", width=3)
            c.create_line(x + 20, y - 2, x + 30, y + 6, fill="#e05050", width=3)
            c.create_oval(x - 10, y - 4, x - 4, y + 2, fill="#fff", outline="")
            c.create_oval(x + 4, y - 4, x + 10, y + 2, fill="#fff", outline="")
        # ---- 森林新增 ----
        elif kind == "swing":
            c.create_line(x - 30, y - 60, x - 8, y - 6, fill="#7d5230", width=3)
            c.create_line(x + 30, y - 60, x + 8, y - 6, fill="#7d5230", width=3)
            c.create_rectangle(x - 12, y - 8, x + 12, y + 2, fill="#a9744a", outline="#7d5230")
        elif kind == "stump_table":
            c.create_oval(x - 26, y - 12, x + 26, y + 14, fill="#c9975c", outline="#7d5230", width=2)
            c.create_oval(x - 20, y - 20, x + 20, y - 8, fill="#e8d9b0", outline="#b08a50")
        elif kind == "beehive":
            c.create_oval(x - 22, y - 20, x + 22, y + 18, fill="#e0a24a", outline="#b07a2a", width=2)
            c.create_line(x - 18, y - 6, x + 18, y - 6, fill="#b07a2a", width=2)
            c.create_line(x - 18, y + 6, x + 18, y + 6, fill="#b07a2a", width=2)
            c.create_rectangle(x - 6, y + 10, x + 6, y + 24, fill="#8a5a30", outline="")
        elif kind == "forest_lamp":
            c.create_line(x, y + 20, x, y - 26, fill="#555", width=3)
            c.create_oval(x - 14, y - 34, x + 14, y - 6, fill="#fff3c4", outline="#d0a020", width=2)
            for fx, fy in ((x - 22, y - 40), (x + 20, y - 44), (x + 8, y - 52)):
                c.create_oval(fx - 3, fy - 3, fx + 3, fy + 3, fill="#aaffaa", outline="")
        # ---- 星空田野露营 ----
        elif kind == "tent":
            c.create_polygon(x - 34, y + 16, x + 34, y + 16, x, y - 34,
                             fill="#4a8a5a", outline="#2f6f3f")
            c.create_polygon(x - 34, y + 16, x - 8, y + 16, x, y - 34,
                             fill="#3f7a4e", outline="#2f6f3f")
            c.create_polygon(x - 4, y - 34, x, y - 34, x - 18, y + 16, fill="#2f6f3f", outline="")
        elif kind == "campfire":
            c.create_oval(x - 12, y - 4, x + 12, y + 14, fill="#8a5a30", outline="#6f4520")
            c.create_polygon(x - 10, y - 2, x + 10, y - 2, x, y - 26, fill="#ff8c42", outline="#e0702a")
            c.create_polygon(x - 6, y - 10, x + 6, y - 10, x, y - 20, fill="#ffd166", outline="")
        elif kind == "picnic":
            c.create_rectangle(x - 42, y - 12, x + 42, y + 6, fill="#e05050", outline="#b03030")
            c.create_line(x - 42, y - 3, x + 42, y - 3, fill="#fff", width=2)
        elif kind == "camp_lamp":
            c.create_line(x, y + 18, x, y - 22, fill="#555", width=3)
            c.create_oval(x - 12, y - 30, x + 12, y - 6, fill="#fff3c4", outline="#d0a020", width=2)
        elif kind == "camp_chair":
            c.create_rectangle(x - 20, y - 24, x + 20, y - 8, fill="#7db6e0", outline="#4a7ba0", width=2)
            c.create_line(x - 16, y - 8, x - 12, y + 18, fill="#4a7ba0", width=4)
            c.create_line(x + 16, y - 8, x + 12, y + 18, fill="#4a7ba0", width=4)
        elif kind == "cooler":
            c.create_rectangle(x - 18, y - 14, x + 18, y + 12, fill="#5aa0e0", outline="#3a70a8", width=2)
            c.create_line(x - 18, y - 1, x + 18, y - 1, fill="#3a70a8", width=2)

    def _switch_scene(self, scene):
        self.scene = scene if scene in SCENES else DEFAULT_SCENE
        try:
            save_layout(self.scene, self._furn_pos, self._pet_pos)
        except Exception:
            save_scene(self.scene)
        self._draw()

    def _draw_scene_decor(self, c, cw, fy, s):
        """按场景画装饰元素（星空月亮、海浪、树木等）。"""
        if self.scene == "star":
            c.create_text(130, 110, text="🌙", font=("Segoe UI Emoji", 42))
            for sx, sy in ((240, 70), (330, 150), (430, 60), (540, 130), (650, 80), (760, 160), (880, 90)):
                c.create_text(sx, sy, text="✨", font=("Segoe UI Emoji", 16))
        elif self.scene == "sea":
            c.create_text(560, 55, text="🌞", font=("Microsoft YaHei UI", 30))
            for wx, wy in ((60, 120), (180, 100), (300, 130), (430, 105), (540, 125)):
                c.create_arc(wx - 34, wy - 12, wx + 34, wy + 12, start=0, extent=180,
                             style="arc", outline="#7fb8e0", width=3)
        elif self.scene == "forest":
            fy = FLOOR_Y
            # 远山（半圆）
            c.create_oval(40, fy - 120, 500, fy + 40, fill="#7da864", outline="")
            c.create_oval(520, fy - 140, 980, fy + 50, fill="#6d9a56", outline="")
            # 远处浅色树影
            for tx, ty, tr in ((110, fy - 30, 55), (300, fy - 26, 65), (520, fy - 34, 50),
                               (700, fy - 24, 70), (880, fy - 30, 55)):
                c.create_oval(tx - tr, ty, tx + tr, ty + tr * 2, fill="#609654", outline="")
            # 松树（三层三角形 + 树干）
            for tx, ty, sc in ((120, fy - 8, 1.25), (235, fy + 2, 0.95), (390, fy - 14, 1.5),
                               (520, fy, 1.1), (645, fy - 16, 1.35), (785, fy + 2, 0.9), (905, fy - 8, 1.3)):
                c.create_polygon(tx - 36 * sc, ty + 18, tx + 36 * sc, ty + 18, tx, ty - 74 * sc,
                                 fill="#357a40", outline="#2f6f38")
                c.create_polygon(tx - 30 * sc, ty + 4, tx + 30 * sc, ty + 4, tx, ty - 54 * sc,
                                 fill="#3f8f4a", outline="#2f6f38")
                c.create_polygon(tx - 24 * sc, ty - 8, tx + 24 * sc, ty - 8, tx, ty - 34 * sc,
                                 fill="#4aa858", outline="#3a8a46")
                c.create_rectangle(tx - 5 * sc, ty + 18, tx + 5 * sc, ty + 30, fill="#604020", outline="")
            # 灌木丛
            for bx, by, br in ((70, fy + 24, 26), (300, fy + 30, 30), (470, fy + 26, 24),
                               (625, fy + 30, 28), (835, fy + 26, 26)):
                c.create_oval(bx - br, by - br, bx + br, by + br, fill="#5da055", outline="")
            # 萤火虫
            for fx, fy2 in ((160, 118), (285, 205), (420, 88), (565, 175), (720, 108), (865, 202), (960, 140)):
                c.create_oval(fx - 7, fy2 - 7, fx + 7, fy2 + 7, fill="#fff0a0", outline="")
                c.create_oval(fx - 3, fy2 - 3, fx + 3, fy2 + 3, fill="#fff6c8", outline="")
        else:  # cozy
            c.create_rectangle(cw - 210, 40, cw - 40, 150, fill="#fff8ee", outline="#c9b28a", width=3)
            c.create_oval(cw - 195, 60, cw - 165, 90, fill="#e0a24a", outline="")
            c.create_rectangle(cw - 150, 55, cw - 130, 145, fill="#8a6d4a", outline="")

    # ---------- 宠物 ----------
    def _draw_pet(self):
        c = self.canvas
        cw = c.winfo_width() or W
        ch = c.winfo_height() or H
        k = min(cw / W, ch / H)          # 随窗口等比缩放
        sx, sy = cw / W, ch / H
        _ppx, _ppy = self._pet_pos
        px = _ppx * sx
        py = _ppy * sy
        img = self.pet._image_for("idle")   # v3.5 主题系统：取兜底/待机图
        if img is not None:
            try:
                iw, ih = img.width(), img.height()
                target_w = int(200 * k)   # 用户要求：小猫再大一点
                scale = target_w / iw
                disp = img
                if scale < 1.0:
                    factor = max(1, int(1.0 / scale))
                    disp = img.subsample(factor, factor)
                    dw, dh = disp.width(), disp.height()
                else:
                    dw, dh = iw, ih
                c.create_image(px, py, image=disp)
                # 表情叠加（饰品功能已移除）
                if self.pet.mood >= 1:
                    meta = self.pet.skin_face
                    if meta:
                        hx = px - dw / 2 + meta["cx"] * dw
                        hy = py - dh / 2 + meta["cy"] * dh
                        hr = meta["r"] * dw
                        pet_renderer.draw_expression_overlay(c, hx, hy, hr, self.pet.mood)
                    else:
                        hx, hy, hr = px, py - 8 * (ch / H), 22 * k
                        pet_renderer.draw_expression_overlay(c, hx, hy, hr, self.pet.mood)
                return
            except Exception:
                pass
        # 程序化形象
        pet_renderer.draw_procedural_pet(
            c, px, py, 0, self.pet.mood, self.pet.level,
            t=self.pet._t, show_level=True,
            view_scale=k * 2.3)   # 用户要求：小猫再大一点

    # ---------- 刷新 ----------
    def _draw(self):
        c = self.canvas
        c.delete("all")
        cw = c.winfo_width() or W
        ch = c.winfo_height() or H
        sx = cw / W
        sy = ch / H
        fy = int(ch * 0.62)
        self._draw_room(cw, ch)
        # 窗户/地毯这类"贴墙"家具优先
        for i, fid in enumerate(self.inventory.placed_in(self.scene)):
            item = shop.get_furniture(fid)
            if item is None:
                continue
            x0, y0 = self._furn_pos.get(fid, SLOTS[i] if i < len(SLOTS) else (200, 320))
            x, y = int(x0 * sx), int(y0 * sy)
            if item["kind"] == "window":
                self._draw_furniture("window", x, int(fy - 130 * sy))
            elif item["kind"] == "rug":
                self._draw_furniture("rug", x, int(fy + 20 * sy))
            else:
                self._draw_furniture(item["kind"], x, y)
        self._draw_pet()

    # ---------- 自由拖动（家具 + 小猫） ----------
    def _to_design(self, ex, ey):
        cw = self.canvas.winfo_width() or W
        ch = self.canvas.winfo_height() or H
        return ex * W / cw, ey * H / ch

    def _drag_start(self, event):
        sx = (self.canvas.winfo_width() or W) / W
        # 猫永远是最上层：优先判定小猫，其次才看家具
        ppx, ppy = self._pet_pos
        if ((event.x - ppx * sx) ** 2 + (event.y - ppy * sx) ** 2) ** 0.5 < 90 * sx:
            self._drag = ("pet", None)
            return
        best, best_d = None, 60 * sx
        for i, fid in enumerate(self.inventory.placed_in(self.scene)):
            x0, y0 = self._furn_pos.get(fid, SLOTS[i] if i < len(SLOTS) else (200, 320))
            d = ((event.x - x0 * sx) ** 2 + (event.y - y0 * sx) ** 2) ** 0.5
            if d < best_d:
                best, best_d = ("fur", fid), d
        self._drag = best

    def _drag_move(self, event):
        if not self._drag:
            return
        kind, fid = self._drag
        dx, dy = self._to_design(event.x, event.y)
        if kind == "fur":
            self._furn_pos[fid] = (dx, dy)
        else:
            self._pet_pos = (dx, dy)
        self._draw()

    def _drag_end(self, event):
        if self._drag:
            try:
                save_layout(self.scene, self._furn_pos, self._pet_pos)
            except Exception:
                pass
        self._drag = None

    def _remove_last(self):
        lst = self.inventory.placed_in(self.scene)
        if lst:
            fid = lst[-1]
            self.inventory.remove_furniture(fid, scene=self.scene)
            self._furn_pos.pop(fid, None)
            try:
                save_layout(self.scene, self._furn_pos, self._pet_pos)
            except Exception:
                pass
            self._draw()
        else:
            messagebox.showinfo("我的空间", "这个地图还没有摆放家具", parent=self.root)