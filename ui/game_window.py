"""ui/game_window.py：内置小游戏「猫猫接金币」（v4.0.1，纯 Tk 零依赖）。

- 猫左右移动（←/→ 或 A/D），接金币 +1 分，接炸弹 -1 命（共 3 命）
- 60 秒倒计时；结束按得分兑换专注币（1 分 = 1 币，每天上限防刷）
- 借鉴：RunCat365 的桌面小猫动起来的感觉
"""
import random
import tkinter as tk

from ui import pet_renderer
from ui.theme_ui import style_window

W, H = 720, 560
GROUND_Y = H - 70
GAME_SECONDS = 60


class GameWindow:
    def __init__(self, parent, on_claim=None):
        self.on_claim = on_claim   # on_claim(score) -> 实际入账币数
        self.root = tk.Toplevel(parent)
        self.root.title("猫猫接金币")
        self.root.geometry(f"{W}x{H + 40}")
        style_window(self.root)
        self.canvas = tk.Canvas(self.root, width=W, height=H, bg="#1e2a3a", highlightthickness=0)
        self.canvas.pack()
        self.canvas.focus_set()

        self.cat_x = W // 2
        self.cat_speed = 12
        self.score = 0
        self.lives = 3
        self.time_left = GAME_SECONDS
        self.items = []      # [{"type": "coin"/"bomb", "x":, "y":, "r":}]
        self.over = False

        self.canvas.bind("<Left>", lambda e: self._move(-1))
        self.canvas.bind("<Right>", lambda e: self._move(1))
        self.canvas.bind("<a>", lambda e: self._move(-1))
        self.canvas.bind("<d>", lambda e: self._move(1))

        self._info = tk.Label(self.root, font=("Microsoft YaHei UI", 11),
                              bg="#f0f0f0", anchor="w")
        self._info.pack(fill="x", padx=8, pady=4)
        self._draw_info()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._spawn_timer()
        self._tick()

    def _move(self, d):
        if self.over:
            return
        self.cat_x = max(30, min(W - 30, self.cat_x + d * self.cat_speed))

    def _spawn_timer(self):
        if self.over:
            return
        kind = "coin" if random.random() < 0.72 else "bomb"
        self.items.append({"type": kind, "x": random.randint(25, W - 25), "y": -10, "r": 14})
        self.root.after(550, self._spawn_timer)

    def _tick(self):
        if self.over:
            return
        self.time_left -= 0.05
        if self.time_left <= 0:
            self._finish()
            return
        # 下落 + 碰撞
        for it in self.items:
            it["y"] += 5
            if abs(it["x"] - self.cat_x) < it["r"] + 30 and it["y"] > GROUND_Y - 34:
                if it["type"] == "coin":
                    self.score += 1
                else:
                    self.lives -= 1
                it["y"] = H + 999
        self.items = [it for it in self.items if it["y"] < H + 60]
        if self.lives <= 0:
            self._finish()
            return
        self._draw()
        self._draw_info()
        self.root.after(50, self._tick)

    def _draw(self):
        c = self.canvas
        c.create_rectangle(0, GROUND_Y, W, H, fill="#22304a", outline="")
        pet_renderer.draw_procedural_pet(c, self.cat_x, GROUND_Y - 20, 0, 0, 1,
                                         t=0, view_scale=0.6)
        for it in self.items:
            if it["type"] == "coin":
                c.create_oval(it["x"] - it["r"], it["y"] - it["r"],
                              it["x"] + it["r"], it["y"] + it["r"],
                              fill="#ffd166", outline="#d0a020", width=2)
                c.create_text(it["x"], it["y"], text="¥", fill="#a06a00",
                              font=("Microsoft YaHei UI", 10, "bold"))
            else:
                c.create_oval(it["x"] - it["r"], it["y"] - it["r"],
                              it["x"] + it["r"], it["y"] + it["r"],
                              fill="#e05a5a", outline="#8f2a2a", width=2)
                c.create_text(it["x"], it["y"], text="!", fill="#fff",
                              font=("Microsoft YaHei UI", 12, "bold"))

    def _draw_info(self):
        extra = "" if self.over else "  ｜ ←→/AD 移动"
        self._info.config(text=f"得分 {self.score} ｜ 生命 {'♥' * max(0, self.lives)} ｜ 剩余 {int(self.time_left)} 秒{extra}")

    def _finish(self):
        self.over = True
        self.canvas.delete("all")
        claimed = int(self.on_claim(self.score) or 0) if self.on_claim else 0
        c = self.canvas
        c.create_text(W / 2, H / 2 - 60, text="游戏结束！", fill="#ffffff",
                      font=("Microsoft YaHei UI", 24, "bold"))
        c.create_text(W / 2, H / 2 - 10, text=f"得分 {self.score}  →  +{claimed} 专注币",
                      fill="#ffd166", font=("Microsoft YaHei UI", 16))
        c.create_text(W / 2, H / 2 + 40, text="右键桌宠 → 小游戏… 可再玩",
                      fill="#9fb0c8", font=("Microsoft YaHei UI", 11))
        self._draw_info()

    def _close(self):
        self.over = True
        self.root.destroy()

