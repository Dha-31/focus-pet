"""ui/shop_window.py：商店——专注币购买家具。

- 按地图（场景）分类：温馨小屋 / 星空书房 / 海边 / 森林。
- 在哪个地图分类买的家具，只能放在那个地图（空间切换场景时各自显示）。
- 商品卡片：上面是物品图案，下面是名字 + 价格。
"""
import tkinter as tk
from tkinter import messagebox, ttk

from core import shop
from ui.theme_ui import accent_button, add_header, style_window

FUR_EMOJI = {
    # 温馨小屋
    "rug": "🟫", "lamp": "🛋️", "plant": "🪴", "window": "🪟",
    "table": "🪑", "bookshelf": "📚", "sofa": "🛋️",
    "fridge": "🧊", "tv": "📺", "clock": "🕰️", "armchair": "💺",
    # 星空书房
    "star_rug": "🌌", "moon_lamp": "🌙", "planet": "🪐", "telescope": "🔭",
    "star_desk": "🪩", "star_chair": "🪑", "star_books": "📚", "aurora": "🌠",
    # 海边
    "beach_umbrella": "⛱️", "beach_chair": "🏖️", "sandcastle": "🏰", "shell": "🐚",
    "fish_tank": "🐠", "hammock": "🪢", "sea_rug": "🏝️", "crab": "🦀",
    # 森林
    "tree": "🌲", "mushroom": "🍄", "log": "🪵", "birdhouse": "🏠",
    "swing": "🪁", "stump_table": "🪑", "beehive": "🐝", "forest_lamp": "🏮",
}


class ShopWindow:
    def __init__(self, parent, inventory, on_place=None):
        self.inventory = inventory
        self.on_place = on_place or (lambda fid: None)
        self.root = tk.Toplevel(parent)
        self.root.title("商店 - 专注币兑换")
        self.root.geometry("1080x1000")
        style_window(self.root)
        self._fur_btns = {}
        self._build()
        self.refresh()

    def _build(self):
        self.coin_var = tk.StringVar()
        add_header(self.root, "商店",
                   "学习赚专注币买家具：在哪个地图分类买的，就只能放在那个地图"
                   ).pack(padx=14, pady=(12, 0), anchor="w")
        tk.Label(self.root, textvariable=self.coin_var,
                 font=("Microsoft YaHei UI", 12, "bold"), fg="#e07a2f").pack(pady=(6, 2))

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=6)
        # 家具按地图分类
        for scene, label in shop.FURNITURE_SCENES:
            tab = tk.Frame(nb)
            nb.add(tab, text=label)
            items = [it for it in shop.FURNITURE if it.get("scene") == scene]
            if items:
                self._build_grid(tab, items)
            else:
                tk.Label(tab, text="这个地图的家具还在准备中，敬请期待~",
                         font=("Microsoft YaHei UI", 12), fg="#aaa").pack(pady=50)

        accent_button(self.root, "关闭", self.root.destroy, width=10).pack(pady=(0, 10))

    def _build_grid(self, parent, items):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for idx, item in enumerate(items):
            row, col = divmod(idx, 3)
            card = tk.Frame(inner, bd=1, relief="groove", padx=10, pady=8, bg="#fffdf7")
            card.grid(row=row, column=col, padx=8, pady=8, sticky="n")
            prev = tk.Canvas(card, width=120, height=100, bg="#fff8ee", highlightthickness=0)
            prev.pack()
            prev.create_text(60, 52, text=FUR_EMOJI.get(item["id"], "🪑"),
                             font=("Segoe UI Emoji", 42))
            tk.Label(card, text=item["name"], font=("Microsoft YaHei UI", 11, "bold"),
                     bg="#fffdf7").pack(pady=(6, 0))
            tk.Label(card, text=f"💰 {shop.price_of(item):.0f} 币", fg="#e07a2f",
                     font=("Microsoft YaHei UI", 10), bg="#fffdf7").pack()
            btn = tk.Button(card, width=8)
            btn.pack(pady=4)
            self._fur_btns[item["id"]] = btn

    def refresh(self):
        inv = self.inventory
        self.coin_var.set(f"专注币：{inv.coins:.0f}")
        for item in shop.FURNITURE:
            btn = self._fur_btns.get(item["id"])
            if btn is None:
                continue
            btn.config(text="放置" if item["id"] in inv.owned_furniture else "购买",
                       state="normal",
                       command=lambda it=item: self._click_furniture(it))

    def _click_furniture(self, item):
        inv = self.inventory
        if item["id"] not in inv.owned_furniture:
            if not inv.can_afford(shop.price_of(item)):
                messagebox.showinfo("商店", "专注币不足！多学一会儿再来~", parent=self.root)
                return
            inv.buy(item)
            messagebox.showinfo("商店", f"已购买 {item['name']}！", parent=self.root)
        # 家具归属 = 它所在的地图分类
        scene = item.get("scene", "cozy")
        if inv.place(item["id"], scene=scene):
            self.on_place(item["id"])
            scene_name = dict(shop.FURNITURE_SCENES).get(scene, scene)
            messagebox.showinfo("商店", f"{item['name']} 已摆进「{scene_name}」！", parent=self.root)
        self.refresh()
