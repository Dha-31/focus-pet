"""ui/space_window.py：个人空间——宠物房间 + 家具 + 宠物入住。"""
import tkinter as tk
from tkinter import messagebox

from core import shop
from ui import pet_renderer
from ui.theme_ui import accent_button, style_window

W, H = 1000, 940
FLOOR_Y = int(H * 0.62)

# 家具摆放槽位（6 个）
SLOTS = [
    (70, FLOOR_Y + 60), (190, FLOOR_Y + 60), (310, FLOOR_Y + 60),
    (430, FLOOR_Y + 60), (130, FLOOR_Y + 110), (430, FLOOR_Y + 110),
]


class SpaceWindow:
    def __init__(self, parent, inventory, pet):
        self.inventory = inventory
        self.pet = pet  # PetApp 实例（读取皮肤/等级/表情/装饰）
        self.root = tk.Toplevel(parent)
        self.root.title("我的空间")
        self.root.geometry(f"{W}x{H + 46}")
        style_window(self.root)

        self.canvas = tk.Canvas(self.root, bg="#fdf6ec", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._draw())
        bar = tk.Frame(self.root)
        bar.pack(pady=6)
        tk.Button(bar, text="移除最后一件家具", command=self._remove_last).pack(side="left", padx=6)
        accent_button(bar, "关闭", self.root.destroy).pack(side="left", padx=6)
        self._draw()

    # ---------- 房间 ----------
    def _draw_room(self, cw, ch):
        c = self.canvas
        fy = int(ch * 0.62)
        # 墙
        c.create_rectangle(0, 0, cw, fy, fill="#fdf1dd", outline="")
        # 地板
        c.create_rectangle(0, fy, cw, ch, fill="#d9b380", outline="")
        for i in range(0, cw, 46):
            c.create_line(i, fy, i, ch, fill="#c49a66")
        # 踢脚线
        c.create_line(0, fy, cw, fy, fill="#b8894f", width=3)

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

    # ---------- 宠物 ----------
    def _draw_pet(self):
        c = self.canvas
        cw = c.winfo_width() or W
        ch = c.winfo_height() or H
        k = min(cw / W, ch / H)          # 随窗口等比缩放
        px = cw / 2
        py = int(ch * 0.62) + 18 * (ch / H)
        img = self.pet._image_for("idle")   # v3.5 主题系统：取兜底/待机图
        if img is not None:
            try:
                iw, ih = img.width(), img.height()
                target_w = int(90 * k)
                scale = target_w / iw
                disp = img
                if scale < 1.0:
                    factor = max(1, int(1.0 / scale))
                    disp = img.subsample(factor, factor)
                    dw, dh = disp.width(), disp.height()
                else:
                    dw, dh = iw, ih
                c.create_image(px, py, image=disp)
                # 装饰/表情叠加
                if self.pet.accessory or self.pet.mood >= 1:
                    meta = self.pet.skin_face
                    if meta:
                        hx = px - dw / 2 + meta["cx"] * dw
                        hy = py - dh / 2 + meta["cy"] * dh
                        hr = meta["r"] * dw
                        if self.pet.accessory:
                            pet_renderer.draw_accessory(c, hx, hy, hr, self.pet.accessory)
                        if self.pet.mood >= 1:
                            pet_renderer.draw_expression_overlay(c, hx, hy, hr, self.pet.mood)
                    else:
                        hx, hy, hr = px, py - 8 * (ch / H), 22 * k
                        if self.pet.accessory:
                            pet_renderer.draw_accessory(c, hx, hy, hr, self.pet.accessory)
                return
            except Exception:
                pass
        # 程序化形象
        pet_renderer.draw_procedural_pet(
            c, px, py, 0, self.pet.mood, self.pet.level,
            accessory=self.pet.accessory, t=self.pet._t, show_level=True,
            view_scale=k)

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
        for i, fid in enumerate(self.inventory.placed_furniture):
            item = shop.get_furniture(fid)
            if item is None:
                continue
            if i < len(SLOTS):
                x0, y0 = SLOTS[i]
                x, y = int(x0 * sx), int(y0 * sy)
                if item["kind"] == "window":
                    self._draw_furniture("window", x, int(fy - 130 * sy))
                elif item["kind"] == "rug":
                    self._draw_furniture("rug", x, int(fy + 20 * sy))
                else:
                    self._draw_furniture(item["kind"], x, y)
        self._draw_pet()

    def _remove_last(self):
        if self.inventory.placed_furniture:
            fid = self.inventory.placed_furniture[-1]
            self.inventory.remove_furniture(fid)
            self._draw()
        else:
            messagebox.showinfo("我的空间", "还没有摆放家具", parent=self.root)