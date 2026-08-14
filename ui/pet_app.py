"""桌宠窗口：透明置顶小窗 + Canvas 程序化形象（v3 增强）。

功能：
- 上下浮动、眨眼、按情绪切换表情（开心/好奇/不耐烦/生气/暴怒）
- 生气时脸红、抖动；说话气泡自动消失
- 可拖拽移动；右键菜单：开始学习 / 结束学习 / 多档模式 / 更换形象 / 教宠物 / 退出
- 养成外观：随等级长大，Lv.4 戴皇冠，Lv.6 金色描边，显示 Lv 角标
- 阻断 Lv2 时放大挡在屏幕中间
- 皮肤系统：skins/<名字>/pet.png 存在则用图片形象；右键"更换形象"可切换/导入新图

线程安全：监督线程通过消息队列 -> 主线程 after() 轮询，不直接操作 Tk 控件。
"""
import json
import math
import os
import queue
import shutil
import time
import tkinter as tk
from tkinter import filedialog, simpledialog

from core.economy import Inventory
from ui import pet_renderer
from ui.skin_face import detect_face_meta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS_DIR = os.path.join(PROJECT_ROOT, "skins")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "config.json")

TRANSPARENT_BG = "#010203"
NORMAL_SIZE = (170, 170)
BLOCK_SIZE = (460, 320)

BODY_NORMAL = "#ffe0b3"
BODY_ANGRY = "#f7b9b9"
OUTLINE_NORMAL = "#e8a95b"
OUTLINE_ANGRY = "#d9534f"
OUTLINE_GOLD = "#d4a017"
BLUSH = "#ffb3b3"


class PetApp:
    def __init__(self, config, mode="daily", inventory=None, on_teach=None,
                 on_start_study=None, on_end_study=None, on_toggle_pomodoro=None,
                 on_mode_change=None, on_exit=None, on_open_achievements=None,
                 on_open_report=None, on_open_settings=None):
        self.on_teach = on_teach
        self.on_start_study = on_start_study
        self.on_end_study = on_end_study
        self.on_toggle_pomodoro = on_toggle_pomodoro
        self.on_mode_change = on_mode_change
        self.on_exit = on_exit
        self.on_open_achievements = on_open_achievements
        self.on_open_report = on_open_report
        self.on_open_settings = on_open_settings

        self.mood = 0
        self.block_mode = False
        self.level = 1
        self.mode = mode if mode in ("daily", "exam") else "daily"
        self.pomodoro_enabled = bool(config["pomodoro"]["enabled"])
        self.bubble_text = ""
        self._bubble_until = 0.0
        self._t = 0.0
        self._blink_period = 3.0
        self.latest_info = None
        self.closed = False

        self._queue = queue.Queue()
        self.image_skin = self._load_skin(config)
        self._skin_disp = None  # 缩放后的显示用图片（防止被垃圾回收）
        self.inventory = inventory if inventory is not None else Inventory()
        self.accessory = self.inventory.equipped_accessory
        self.skin_face = self._load_skin_face(config)
        self._space_win = None
        # "你在看我吗"状态
        self._looking = False
        self._look_dx = 0.0
        self._look_dy = 0.0
        self._looking_since = None
        self._last_look_msg = 0.0

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

    def reload_skin(self):
        """按当前配置重新加载皮肤（更换形象后调用）。"""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            return
        self.image_skin = self._load_skin(cfg)
        self._skin_disp = None

    def _load_skin_face(self, config):
        """读取皮肤的人脸元数据（导入时自动检测生成）。"""
        name = config["pet"]["skin"]
        if name and name != "default":
            path = os.path.join(SKINS_DIR, name, "pet.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                    return data.get("face") or data
                except Exception:
                    pass
        return None

    def _list_skins(self):
        """返回可用皮肤名列表（含 default）。"""
        names = ["default"]
        if os.path.isdir(SKINS_DIR):
            for entry in sorted(os.listdir(SKINS_DIR)):
                d = os.path.join(SKINS_DIR, entry)
                if os.path.isdir(d) and os.path.exists(os.path.join(d, "pet.png")):
                    names.append(entry)
        return names

    def _set_skin(self, name):
        if name not in self._list_skins():
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        cfg.setdefault("pet", {})["skin"] = name
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        self.reload_skin()
        self.say("形象已更换！")

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

        # 多档模式（轻松/日常/考试/自定义）
        mode_menu = tk.Menu(menu, tearoff=0)
        self._mode_var = tk.StringVar(value=self.mode)
        mode_menu.add_radiobutton(label="轻松模式", value="relaxed",
                                  variable=self._mode_var,
                                  command=lambda: self._menu_mode("relaxed"))
        mode_menu.add_radiobutton(label="日常自习", value="daily",
                                  variable=self._mode_var,
                                  command=lambda: self._menu_mode("daily"))
        mode_menu.add_radiobutton(label="考试冲刺", value="exam",
                                  variable=self._mode_var,
                                  command=lambda: self._menu_mode("exam"))
        mode_menu.add_radiobutton(label="自定义", value="custom",
                                  variable=self._mode_var,
                                  command=lambda: self._menu_mode("custom"))
        menu.add_cascade(label="多档模式", menu=mode_menu)

        # 番茄钟
        label = "番茄钟：开启" if not self.pomodoro_enabled else "番茄钟：关闭"
        menu.add_command(label=label, command=self._menu_toggle_pomodoro)
        menu.add_separator()

        menu.add_command(label="更换形象…", command=self._open_skin_dialog)
        menu.add_command(label="商店…", command=self._open_shop)
        menu.add_command(label="我的空间…", command=self._open_space)
        menu.add_command(label="成就…", command=self._menu_achievements)
        menu.add_command(label="数据报表…", command=self._menu_report)
        menu.add_command(label="设置…", command=self._menu_settings)
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

    def _menu_mode(self, mode):
        self.mode = mode
        if self.on_mode_change:
            self.on_mode_change(mode)
        self._build_menu()

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

    # ---------- 成就 / 报表 ----------
    def _menu_achievements(self):
        if self.on_open_achievements:
            self.on_open_achievements()

    def _menu_report(self):
        if self.on_open_report:
            self.on_open_report()

    def _menu_settings(self):
        if self.on_open_settings:
            self.on_open_settings()

    # ---------- 商店 / 个人空间 ----------
    def _open_shop(self):
        from ui.shop_window import ShopWindow
        ShopWindow(self.root, self.inventory,
                   on_equip=lambda aid: self.equip_accessory(aid),
                   on_place=lambda fid: self.refresh_space())

    def _open_space(self):
        from ui.space_window import SpaceWindow
        self._space_win = SpaceWindow(self.root, self.inventory, self)

    def equip_accessory(self, aid):
        self.accessory = aid
        self.say("好看！")

    def refresh_space(self):
        win = getattr(self, "_space_win", None)
        if win is not None:
            try:
                win._draw()
            except Exception:
                pass

    # ---------- 更换形象对话框 ----------
    def _open_skin_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("更换形象")
        dialog.geometry("360x440")
        dialog.attributes("-topmost", True)
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="选择形象：", font=("Microsoft YaHei UI", 10)).pack(pady=(10, 2))

        self._skin_preview = tk.Label(dialog, bg="#f0f0f0", width=160, height=120)
        self._skin_preview.pack(pady=4)

        listbox = tk.Listbox(dialog, width=30, height=8, font=("Microsoft YaHei UI", 10))
        listbox.pack(padx=10, pady=4, fill="both", expand=True)
        for name in self._list_skins():
            listbox.insert("end", name)

        def preview(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            name = listbox.get(sel[0])
            self._preview_skin(name, dialog)

        listbox.bind("<<ListboxSelect>>", preview)

        btn_bar = tk.Frame(dialog)
        btn_bar.pack(pady=6)
        tk.Button(btn_bar, text="导入新图片…", command=lambda: self._import_skin(listbox)).pack(side="left", padx=4)
        tk.Button(btn_bar, text="使用", command=lambda: self._use_skin(listbox, dialog)).pack(side="left", padx=4)
        tk.Button(btn_bar, text="关闭", command=dialog.destroy).pack(side="left", padx=4)

        if listbox.size() > 0:
            listbox.selection_set(0)
            preview()

    def _preview_skin(self, name, parent):
        try:
            if name == "default":
                img = None
            else:
                path = os.path.join(SKINS_DIR, name, "pet.png")
                img = tk.PhotoImage(file=path)
            if img is None:
                self._skin_preview.configure(image="", text="（程序化小猫）")
                self._skin_preview_ref = None
            else:
                iw, ih = img.width(), img.height()
                scale = min(1.0, 150 / iw, 110 / ih)
                if scale < 1.0:
                    factor_x = max(1, int(1 / scale))
                    img = img.subsample(factor_x, factor_x)
                self._skin_preview_ref = img
                self._skin_preview.configure(image=img, text="")
        except Exception:
            self._skin_preview.configure(image="", text="无法预览")

    def _use_skin(self, listbox, dialog):
        sel = listbox.curselection()
        if not sel:
            return
        name = listbox.get(sel[0])
        self._set_skin(name)
        dialog.destroy()

    def _import_skin(self, listbox):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="选择宠物图片（PNG 优先）",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.bmp *.webp"), ("所有文件", "*.*")],
        )
        if not path:
            return
        name = os.path.splitext(os.path.basename(path))[0] or "mypet"
        out_dir = os.path.join(SKINS_DIR, name)
        base = out_dir
        i = 1
        while os.path.exists(os.path.join(out_dir, "pet.png")):
            out_dir = f"{base}_{i}"
            i += 1
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "pet.png")
        try:
            from tools.make_skin import build_skin
            method = build_skin(path, out_path)
        except Exception:
            shutil.copy(path, out_path)
            method = "copy"
        if method == "rembg":
            print("[pet] 新形象已生成（AI 抠图）")
        elif method == "pillow":
            print("[pet] 新形象已生成（白色去底）")
        else:
            print("[pet] 新形象已导入（原图）")
        # 识别人脸位置 -> 装饰品/表情自动适配
        meta = detect_face_meta(out_path)
        if meta:
            with open(os.path.join(out_dir, "pet.json"), "w", encoding="utf-8") as f:
                json.dump({"face": meta}, f, ensure_ascii=False, indent=2)
            print("[pet] 已识别人脸位置，装饰品/表情会自动适配")
        self._set_skin(os.path.basename(out_dir))
        listbox.delete(0, "end")
        for n in self._list_skins():
            listbox.insert("end", n)
        self.say("新形象来了！")

    # ---------- 监督线程 -> 主线程 ----------
    def say(self, text, seconds=4):
        self._queue.put(("say", (text, seconds)))

    def set_mood(self, mood):
        self._queue.put(("mood", (int(max(0, min(4, mood))),)))

    def block(self, on):
        self._queue.put(("block", (bool(on),)))

    def set_pomodoro_enabled(self, enabled):
        self._queue.put(("pomodoro", (bool(enabled),)))

    def set_level(self, level):
        self._queue.put(("level", (int(max(1, level)),)))

    def set_mode(self, mode):
        self._queue.put(("mode", (mode,)))

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
                elif kind == "level":
                    self.level = args[0]
                elif kind == "mode":
                    self.mode = args[0]
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
        self._update_looking()
        self._draw()
        self.root.after(33, self._anim)

    def _mouse_pos(self):
        try:
            import ctypes
            from ctypes import wintypes
            pt = wintypes.POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return pt.x, pt.y
        except Exception:
            pass
        return None

    def _update_looking(self):
        """鼠标靠近宠物 => 宠物盯着你看（瞳孔跟随 + 偶尔搭话）。"""
        if self.block_mode:
            self._looking = False
            return
        pos = self._mouse_pos()
        if pos is None:
            self._looking = False
            return
        wx = self.root.winfo_x()
        wy = self.root.winfo_y()
        cw = self.canvas.winfo_width() or NORMAL_SIZE[0]
        ch = self.canvas.winfo_height() or NORMAL_SIZE[1]
        cx = wx + cw / 2.0
        cy = wy + ch / 2.0
        dx = pos[0] - cx
        dy = pos[1] - cy
        dist = math.hypot(dx, dy)
        if dist < 150:
            self._looking = True
            self._look_dx = max(-1.0, min(1.0, dx / 60.0))
            self._look_dy = max(-1.0, min(1.0, dy / 60.0))
            if self._looking_since is None:
                self._looking_since = time.time()
            if (time.time() - self._looking_since > 2.0
                    and time.time() - self._last_look_msg > 15.0):
                self._last_look_msg = time.time()
                self.say("你在看我呀？(◕ᴗ◕)")
        else:
            self._looking = False
            self._look_dx = 0.0
            self._look_dy = 0.0
            self._looking_since = None

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
            lean = self._look_dx * 3 if self._looking else 0.0
            pet_renderer.draw_procedural_pet(
                c, cx + lean, cy + bob, shake, self.mood, self.level,
                accessory=self.accessory, t=self._t, show_level=True,
                look=(self._look_dx, self._look_dy) if self._looking else None)
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
        disp = self._skin_disp
        dw, dh = disp.width(), disp.height()
        c.create_image(cx + shake, cy, image=disp)

        # 装饰品/表情自动适配（依据人脸元数据）
        if self.accessory or self.mood >= 1:
            meta = self.skin_face
            if meta:
                hx = cx + shake - dw / 2 + meta["cx"] * dw
                hy = cy - dh / 2 + meta["cy"] * dh
                hr = max(8, meta["r"] * dw)
            else:
                hx, hy, hr = cx + shake, cy - dh * 0.35, max(8, dw * 0.18)
            if self.accessory:
                pet_renderer.draw_accessory(c, hx, hy, hr, self.accessory)
            if self.mood >= 1:
                pet_renderer.draw_expression_overlay(c, hx, hy, hr, self.mood)

    def _draw_procedural(self, c, cx, cy, shake):
        s = 1.0 + min(0.4, (self.level - 1) * 0.08)
        angry = self.mood >= 3
        body = BODY_ANGRY if angry else BODY_NORMAL
        outline = OUTLINE_ANGRY if angry else OUTLINE_NORMAL
        if self.level >= 6:
            outline = OUTLINE_GOLD

        # 耳朵
        ear_l = [(cx - 30 * s + shake, cy - 34 * s),
                 (cx - 18 * s + shake, cy - 52 * s),
                 (cx - 6 * s + shake, cy - 32 * s)]
        ear_r = [(cx + 6 * s + shake, cy - 32 * s),
                 (cx + 18 * s + shake, cy - 52 * s),
                 (cx + 30 * s + shake, cy - 34 * s)]
        c.create_polygon(ear_l, fill=body, outline=outline, width=2)
        c.create_polygon(ear_r, fill=body, outline=outline, width=2)

        # 身体
        c.create_oval(cx - 40 * s + shake, cy - 40 * s, cx + 40 * s + shake, cy + 40 * s,
                      fill=body, outline=outline, width=3)

        # 腮红
        if self.mood >= 1:
            blush = "#ff8080" if self.mood >= 3 else BLUSH
            c.create_oval(cx - 34 * s + shake, cy + 6 * s, cx - 22 * s + shake, cy + 16 * s,
                          fill=blush, outline="")
            c.create_oval(cx + 22 * s + shake, cy + 6 * s, cx + 34 * s + shake, cy + 16 * s,
                          fill=blush, outline="")

        # 眼睛（眨眼）
        blinking = (self._t % self._blink_period) < 0.18
        eye_y = cy - 10 * s
        if blinking:
            c.create_line(cx - 16 * s + shake, eye_y, cx - 8 * s + shake, eye_y, fill="#4a3728", width=2)
            c.create_line(cx + 8 * s + shake, eye_y, cx + 16 * s + shake, eye_y, fill="#4a3728", width=2)
        else:
            c.create_oval(cx - 17 * s + shake, eye_y - 6 * s, cx - 7 * s + shake, eye_y + 6 * s,
                          fill="#4a3728", outline="")
            c.create_oval(cx + 7 * s + shake, eye_y - 6 * s, cx + 17 * s + shake, eye_y + 6 * s,
                          fill="#4a3728", outline="")

        # 眉毛（不耐烦/生气）
        if self.mood >= 2:
            c.create_line(cx - 18 * s + shake, eye_y - 12 * s, cx - 6 * s + shake, eye_y - 8 * s,
                          fill="#4a3728", width=2)
            c.create_line(cx + 6 * s + shake, eye_y - 8 * s, cx + 18 * s + shake, eye_y - 12 * s,
                          fill="#4a3728", width=2)

        # 嘴
        mouth_y = cy + 10 * s
        if self.mood == 0:      # 开心：微笑
            c.create_arc(cx - 12 * s + shake, mouth_y - 8 * s, cx + 12 * s + shake, mouth_y + 12 * s,
                         start=180, extent=180, style="arc", outline="#4a3728", width=2)
        elif self.mood == 1:    # 好奇：小 O
            c.create_oval(cx - 3 * s + shake, mouth_y - 3 * s, cx + 3 * s + shake, mouth_y + 3 * s,
                          fill="#4a3728", outline="")
        elif self.mood == 2:    # 不耐烦：直线
            c.create_line(cx - 8 * s + shake, mouth_y, cx + 8 * s + shake, mouth_y,
                          fill="#4a3728", width=2)
        else:                   # 生气/暴怒：倒弧 + 咬牙
            c.create_arc(cx - 12 * s + shake, mouth_y - 4 * s, cx + 12 * s + shake, mouth_y + 12 * s,
                         start=0, extent=180, style="arc", outline="#4a3728", width=2)
            if self.mood >= 4:
                for dx in (-5 * s, 0, 5 * s):
                    c.create_line(cx + dx + shake, mouth_y + 4 * s, cx + dx + shake, mouth_y + 9 * s,
                                  fill="#4a3728", width=1)

        # 皇冠（Lv>=4）
        if self.level >= 4:
            top = cy - 52 * s
            pts = [(cx - 14 * s + shake, top), (cx - 9 * s + shake, top - 14 * s),
                   (cx - 4 * s + shake, top - 6 * s), (cx + 4 * s + shake, top - 6 * s),
                   (cx + 9 * s + shake, top - 14 * s), (cx + 14 * s + shake, top),
                   (cx - 14 * s + shake, top)]
            c.create_polygon(pts, fill="#ffd700", outline="#c9a400", width=1)

        # 等级角标
        c.create_text(cx + shake, cy + 40 * s + 14, text=f"Lv.{self.level}",
                      fill="#777777", font=("Microsoft YaHei UI", 8))

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