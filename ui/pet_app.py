"""桌宠窗口：透明置顶小窗 + Canvas 程序化形象（v1）。

功能：
- 上下浮动、眨眼、按情绪切换表情（开心/好奇/不耐烦/生气/暴怒）
- 生气时脸红、抖动；说话气泡自动消失
- 可拖拽移动；右键菜单：开始学习 / 结束学习 / 番茄钟开关 / 教宠物 / 退出
- 阻断 Lv2 时放大挡在屏幕中间
- 皮肤系统：skins/<名字>/pet.png 存在则用图片形象，否则用程序化形象

线程安全：监督线程通过消息队列 -> 主线程 after() 轮询，不直接操作 Tk 控件。
"""
import math
import os
import queue
import time
import tkinter as tk
from tkinter import simpledialog

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS_DIR = os.path.join(PROJECT_ROOT, "skins")

TRANSPARENT_BG = "#010203"
NORMAL_SIZE = (170, 170)
BLOCK_SIZE = (460, 320)

BODY_NORMAL = "#ffe0b3"
BODY_ANGRY = "#f7b9b9"
OUTLINE_NORMAL = "#e8a95b"
OUTLINE_ANGRY = "#d9534f"
BLUSH = "#ffb3b3"


class PetApp:
    def __init__(self, config, on_teach=None, on_start_study=None,
                 on_end_study=None, on_toggle_pomodoro=None, on_exit=None):
        self.on_teach = on_teach
        self.on_start_study = on_start_study
        self.on_end_study = on_end_study
        self.on_toggle_pomodoro = on_toggle_pomodoro
        self.on_exit = on_exit

        self.mood = 0
        self.block_mode = False
        self.pomodoro_enabled = bool(config["pomodoro"]["enabled"])
        self.bubble_text = ""
        self._bubble_until = 0.0
        self._t = 0.0
        self._blink_period = 3.0
        self.latest_info = None
        self.closed = False
        self._drag = None

        self._queue = queue.Queue()
        self.image_skin = self._load_skin(config)
        self._skin_disp = None  # 缩放后的显示用图片（防止被垃圾回收）

        self.root = tk.Tk()
        self.root.title("Focus Pet")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-transparentcolor", TRANSPARENT_BG)
        except tk.TclError:
            pass

        self._normal_pos = None  # 普通模式下窗口位置 (x, y)
        self._set_geometry(NORMAL_SIZE)

        self.canvas = tk.Canvas(self.root, bg=TRANSPARENT_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._setup_drag()
        self._build_menu()
        self._poll_queue()
        self._anim()

    # ---------- 皮肤 ----------
    @staticmethod
    def _load_skin(config):
        name = config["pet"]["skin"]
        if name and name != "default":
            path = os.path.join(SKINS_DIR, name, "pet.png")
            if os.path.exists(path):
                try:
                    return tk.PhotoImage(file=path)
                except Exception as exc:
                    print("[pet] 皮肤加载失败，回退到程序化形象：", exc)
        return None

    # ---------- 窗口几何 ----------
    def _set_geometry(self, size):
        w, h = size
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if self._normal_pos:
            x, y = self._normal_pos
        else:
            x = sw - w - 40
            y = sh - h - 120
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        if size == NORMAL_SIZE:
            self._normal_pos = (x, y)

    def _center_for_block(self):
        w, h = BLOCK_SIZE
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ---------- 拖拽 ----------
    def _setup_drag(self):
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)

    def _drag_start(self, event):
        self._drag = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y())

    def _drag_move(self, event):
        if not self._drag or self.block_mode:
            return
        rx, ry, wx, wy = self._drag
        dx = event.x_root - rx
        dy = event.y_root - ry
        self.root.geometry(f"+{wx + dx}+{wy + dy}")

    def _drag_end(self, event):
        self._drag = None
        self._normal_pos = (self.root.winfo_x(), self.root.winfo_y())

    # ---------- 右键菜单 ----------
    def _build_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="开始学习…", command=self._menu_start_study)
        menu.add_command(label="结束学习", command=self._menu_end_study)
        menu.add_separator()
        label = "番茄钟：开启" if not self.pomodoro_enabled else "番茄钟：关闭"
        menu.add_command(label=label, command=self._menu_toggle_pomodoro)
        menu.add_separator()
        menu.add_command(label="这个是学习用的！", command=self._menu_teach)
        menu.add_separator()
        menu.add_command(label="退出", command=self._menu_exit)
        self.canvas.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))
        self._menu = menu

    def _menu_start_study(self):
        if self.on_start_study is None:
            return
        goal = simpledialog.askstring("开始学习", "今天学什么？", parent=self.root)
        if goal is None:
            return
        self.on_start_study(goal.strip() or "学习")

    def _menu_end_study(self):
        if self.on_end_study:
            self.on_end_study()

    def _menu_toggle_pomodoro(self):
        if self.on_toggle_pomodoro:
            self.on_toggle_pomodoro()

    def _menu_teach(self):
        if self.on_teach:
            self.on_teach(self.latest_info)

    def _menu_exit(self):
        allowed = True
        if self.on_exit:
            allowed = bool(self.on_exit())
        if allowed:
            self.closed = True
            self.root.destroy()

    # ---------- 监督线程 -> 主线程 ----------
    def say(self, text, seconds=4):
        self._queue.put(("say", (text, seconds)))

    def set_mood(self, mood):
        self._queue.put(("mood", (int(max(0, min(4, mood))),)))

    def block(self, on):
        self._queue.put(("block", (bool(on),)))

    def set_pomodoro_enabled(self, enabled):
        self._queue.put(("pomodoro", (bool(enabled),)))

    def update_info(self, info):
        self._queue.put(("info", (info,)))

    def _poll_queue(self):
        try:
            while True:
                kind, args = self._queue.get_nowait()
                if kind == "say":
                    text, seconds = args
                    self.bubble_text = text
                    self._bubble_until = time.time() + seconds
                elif kind == "mood":
                    self.mood = args[0]
                elif kind == "block":
                    self._set_block_mode(args[0])
                elif kind == "pomodoro":
                    self.pomodoro_enabled = args[0]
                    self._build_menu()
                elif kind == "info":
                    self.latest_info = args[0]
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _set_block_mode(self, on):
        if on == self.block_mode:
            return
        self.block_mode = on
        if on:
            self._center_for_block()
        else:
            self._set_geometry(NORMAL_SIZE)

    # ---------- 动画 ----------
    def _anim(self):
        if self.closed:
            return
        self._t += 0.033
        self._draw()
        self.root.after(33, self._anim)

    def _draw(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or NORMAL_SIZE[0]
        h = c.winfo_height() or NORMAL_SIZE[1]
        cx, cy = w / 2.0, h / 2.0
        bob = math.sin(self._t * 2.5) * 4.0
        shake = math.sin(self._t * 40.0) * 3.0 if (self.mood >= 3 or self.block_mode) else 0.0
        if self.image_skin is not None:
            self._draw_image(c, cx, cy + bob, shake)
        else:
            self._draw_procedural(c, cx, cy + bob, shake)
        self._draw_bubble(c, w, h)

    def _draw_image(self, c, cx, cy, shake):
        base = self.image_skin
        if base is None:
            return
        iw, ih = base.width(), base.height()
        w = c.winfo_width() or NORMAL_SIZE[0]
        h = c.winfo_height() or NORMAL_SIZE[1]
        if iw > w or ih > h:
            factor_x = iw // w + (1 if iw % w else 0)
            factor_y = ih // h + (1 if ih % h else 0)
            factor = max(1, max(factor_x, factor_y))
            self._skin_disp = base.subsample(factor, factor)
        else:
            self._skin_disp = base
        c.create_image(cx + shake, cy, image=self._skin_disp)

    def _draw_procedural(self, c, cx, cy, shake):
        angry = self.mood >= 3
        body = BODY_ANGRY if angry else BODY_NORMAL
        outline = OUTLINE_ANGRY if angry else OUTLINE_NORMAL

        # 耳朵
        ear_l = [(cx - 30 + shake, cy - 34), (cx - 18 + shake, cy - 52), (cx - 6 + shake, cy - 32)]
        ear_r = [(cx + 6 + shake, cy - 32), (cx + 18 + shake, cy - 52), (cx + 30 + shake, cy - 34)]
        c.create_polygon(ear_l, fill=body, outline=outline, width=2)
        c.create_polygon(ear_r, fill=body, outline=outline, width=2)

        # 身体
        c.create_oval(cx - 40 + shake, cy - 40, cx + 40 + shake, cy + 40,
                      fill=body, outline=outline, width=3)

        # 腮红
        if self.mood >= 1:
            blush = "#ff8080" if self.mood >= 3 else BLUSH
            c.create_oval(cx - 34 + shake, cy + 6, cx - 22 + shake, cy + 16, fill=blush, outline="")
            c.create_oval(cx + 22 + shake, cy + 6, cx + 34 + shake, cy + 16, fill=blush, outline="")

        # 眼睛（眨眼）
        blinking = (self._t % self._blink_period) < 0.18
        eye_y = cy - 10
        if blinking:
            c.create_line(cx - 16 + shake, eye_y, cx - 8 + shake, eye_y, fill="#4a3728", width=2)
            c.create_line(cx + 8 + shake, eye_y, cx + 16 + shake, eye_y, fill="#4a3728", width=2)
        else:
            c.create_oval(cx - 17 + shake, eye_y - 6, cx - 7 + shake, eye_y + 6, fill="#4a3728", outline="")
            c.create_oval(cx + 7 + shake, eye_y - 6, cx + 17 + shake, eye_y + 6, fill="#4a3728", outline="")

        # 眉毛（不耐烦/生气）
        if self.mood >= 2:
            c.create_line(cx - 18 + shake, eye_y - 12, cx - 6 + shake, eye_y - 8, fill="#4a3728", width=2)
            c.create_line(cx + 6 + shake, eye_y - 8, cx + 18 + shake, eye_y - 12, fill="#4a3728", width=2)

        # 嘴
        mouth_y = cy + 10
        if self.mood == 0:      # 开心：微笑
            c.create_arc(cx - 12 + shake, mouth_y - 8, cx + 12 + shake, mouth_y + 12,
                         start=180, extent=180, style="arc", outline="#4a3728", width=2)
        elif self.mood == 1:    # 好奇：小 O
            c.create_oval(cx - 3 + shake, mouth_y - 3, cx + 3 + shake, mouth_y + 3,
                          fill="#4a3728", outline="")
        elif self.mood == 2:    # 不耐烦：直线
            c.create_line(cx - 8 + shake, mouth_y, cx + 8 + shake, mouth_y,
                          fill="#4a3728", width=2)
        else:                   # 生气/暴怒：倒弧 + 咬牙
            c.create_arc(cx - 12 + shake, mouth_y - 4, cx + 12 + shake, mouth_y + 12,
                         start=0, extent=180, style="arc", outline="#4a3728", width=2)
            if self.mood >= 4:
                for dx in (-5, 0, 5):
                    c.create_line(cx + dx + shake, mouth_y + 4, cx + dx + shake, mouth_y + 9,
                                  fill="#4a3728", width=1)

    def _draw_bubble(self, c, w, h):
        if not self.bubble_text or time.time() > self._bubble_until:
            return
        text = self.bubble_text
        bx, by, bw, bh = 8, 8, w - 16, 46
        c.create_oval(bx, by, bx + 14, by + 14, fill="white", outline="#888888")
        c.create_oval(bx + bw - 14, by, bx + bw, by + 14, fill="white", outline="#888888")
        c.create_oval(bx, by + bh - 14, bx + 14, by + bh, fill="white", outline="#888888")
        c.create_oval(bx + bw - 14, by + bh - 14, bx + bw, by + bh, fill="white", outline="#888888")
        c.create_rectangle(bx + 7, by, bx + bw - 7, by + bh, fill="white", outline="#888888")
        c.create_rectangle(bx, by + 7, bx + bw, by + bh - 7, fill="white", outline="#888888")
        c.create_text(bx + bw / 2, by + bh / 2, text=text, width=bw - 16,
                      fill="#333333", font=("Microsoft YaHei UI", 9))