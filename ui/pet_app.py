"""桌宠窗口：透明置顶小窗 + Canvas 程序化形象（v3.5 状态机 + 主题资源包）。

v3.5 升级：
- 事件→状态→动画 状态机（core/state_machine.py）：情绪状态 happy/curious/annoyed/
  angry/furious + 瞬时状态 celebrate/error + 持续状态 sleep
- 主题资源包（core/theme.py）：皮肤目录里每个状态一张图（angry.png/furious.png/
  celebrate.png/error.png/sleep.png…），没有就回退 pet.png / 程序化小猫
- 完成庆祝动画、出错反馈动画、睡觉 Zzz、脚下阴影
- 位置记忆：记住宠物放在哪，重启后回到原位
- 导入主题包 zip（右键菜单）
- 托盘联动：可隐藏到托盘（托盘在 main.py 创建）

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

from core import theme as theme_mod
from core.economy import Inventory
from core.state_machine import PetStateMachine
from ui import pet_renderer
from ui.theme_ui import accent_button, add_header
from ui.skin_face import detect_face_meta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS_DIR = os.path.join(PROJECT_ROOT, "skins")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "config.json")

TRANSPARENT_BG = "#010203"
NORMAL_SIZE = (170, 170)
BLOCK_SIZE = (460, 320)


class PetApp:
    def __init__(self, config, mode="daily", inventory=None, on_teach=None,
                 on_start_study=None, on_end_study=None, on_toggle_pomodoro=None,
                 on_mode_change=None, on_exit=None, on_open_achievements=None,
                 on_open_report=None, on_open_settings=None, tray_enabled=False):
        self.on_teach = on_teach
        self.on_start_study = on_start_study
        self.on_end_study = on_end_study
        self.on_toggle_pomodoro = on_toggle_pomodoro
        self.on_mode_change = on_mode_change
        self.on_exit = on_exit
        self.on_open_achievements = on_open_achievements
        self.on_open_report = on_open_report
        self.on_open_settings = on_open_settings

        self.sm = PetStateMachine()          # 事件->状态->动画 状态机
        self.mood = 0                        # 兼容字段（情绪值）
        self.block_mode = False
        self.level = 1
        self.mode = mode if mode in ("daily", "exam", "relaxed", "custom") else "daily"
        self.pomodoro_enabled = bool(config["pomodoro"]["enabled"])
        self.bubble_text = ""
        self._bubble_until = 0.0
        self._t = 0.0
        self._blink_period = 3.0
        self.latest_info = None
        self.closed = False
        self.tray_enabled = bool(tray_enabled)

        self._queue = queue.Queue()
        self.theme_name = config.get("pet", {}).get("skin", "default")
        self._skin_img_cache = {}            # 状态 -> PhotoImage
        self._skin_disp = {}                 # 状态 -> 缩放后的显示图
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

        # 位置记忆：从配置恢复上次位置
        self._normal_pos = None
        try:
            _wx = config.get("pet", {}).get("window_x")
            _wy = config.get("pet", {}).get("window_y")
            if isinstance(_wx, (int, float)) and isinstance(_wy, (int, float)):
                self._normal_pos = (int(_wx), int(_wy))
        except Exception:
            pass
        self._set_geometry(NORMAL_SIZE)

        self.canvas = tk.Canvas(self.root, bg=TRANSPARENT_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._setup_drag()
        self._build_menu()
        self._poll_queue()
        self._anim()

    # ---------- 皮肤 / 主题 ----------
    @staticmethod
    def _load_skin(config):
        """兼容旧接口：返回兜底 pet.png 的 PhotoImage（不再使用）。"""
        name = config.get("pet", {}).get("skin", "default")
        if name and name != "default":
            path = os.path.join(SKINS_DIR, name, "pet.png")
            if os.path.exists(path):
                try:
                    return tk.PhotoImage(file=path)
                except Exception:
                    pass
        return None

    def reload_skin(self):
        """按当前配置重新加载主题（更换形象/导入主题包后调用）。"""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            return
        self.theme_name = cfg.get("pet", {}).get("skin", "default")
        self._skin_img_cache.clear()
        self._skin_disp.clear()
        self.skin_face = self._load_skin_face(cfg)

    def _image_for(self, state):
        """按状态取主题图（带缓存）；没有返回 None。"""
        if self.theme_name == "default":
            return None
        if state in self._skin_img_cache:
            return self._skin_img_cache[state]
        path = theme_mod.resolve_image_file(self.theme_name, state)
        if not path:
            self._skin_img_cache[state] = None
            return None
        try:
            img = tk.PhotoImage(file=path)
        except Exception as exc:
            print("[pet] 主题图加载失败（", path, "）:", exc)
            img = None
        self._skin_img_cache[state] = img
        return img

    def _load_skin_face(self, config):
        """读取皮肤的人脸元数据（导入时自动检测生成）。"""
        return theme_mod.face_meta(config.get("pet", {}).get("skin", "default"))

    def _list_skins(self):
        return theme_mod.iter_skins()

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

    # ---------- 窗口几何 / 位置记忆 ----------
    def _set_geometry(self, size):
        w, h = size
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if self._normal_pos:
            x, y = self._normal_pos
            x = max(0, min(int(x), max(0, sw - w)))
            y = max(0, min(int(y), max(0, sh - h)))
        else:
            x = sw - w - 40
            y = sh - h - 120
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        if size == NORMAL_SIZE:
            self._normal_pos = (x, y)

    def _save_position(self):
        """把当前位置写回配置（位置记忆）。"""
        if self._normal_pos is None:
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        cfg.setdefault("pet", {})["window_x"] = int(self._normal_pos[0])
        cfg.setdefault("pet", {})["window_y"] = int(self._normal_pos[1])
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def _center_for_block(self):
        w, h = BLOCK_SIZE
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def hide(self):
        """隐藏到托盘（托盘双击/菜单可唤回）。"""
        try:
            self.root.withdraw()
        except Exception:
            pass

    def show(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
        except Exception:
            pass

    def toggle_visible(self):
        try:
            if self.root.state() == "withdrawn" or not self.root.winfo_viewable():
                self.show()
            else:
                self.hide()
        except Exception:
            self.show()

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
        self._save_position()   # 位置记忆

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
        menu.add_command(label="导入主题包…", command=self._import_theme_zip)
        menu.add_command(label="商店…", command=self._open_shop)
        menu.add_command(label="我的空间…", command=self._open_space)
        menu.add_command(label="成就…", command=self._menu_achievements)
        menu.add_command(label="数据报表…", command=self._menu_report)
        menu.add_command(label="设置…", command=self._menu_settings)
        menu.add_command(label="这个是学习用的！", command=self._menu_teach)
        if self.tray_enabled:
            menu.add_command(label="隐藏到托盘", command=self.hide)
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
            self._save_position()   # 位置记忆
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
        dialog.geometry("360x460")
        dialog.attributes("-topmost", True)
        dialog.transient(self.root)
        dialog.grab_set()

        add_header(dialog, "更换形象", "选一个形象，或导入你自己的图片 / 主题包").pack(padx=14, pady=(10, 0), anchor="w")

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
        tk.Button(btn_bar, text="导入主题包…", command=lambda: self._import_theme_zip(listbox)).pack(side="left", padx=4)
        accent_button(btn_bar, "使用", lambda: self._use_skin(listbox, dialog)).pack(side="left", padx=4)
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
        # 生成主题清单：所有状态先回退 pet.png，之后可逐状态替换
        self._write_theme_json(out_dir, name)
        # 识别人脸位置 -> 装饰品/表情自动适配
        meta = detect_face_meta(out_path)
        if meta:
            with open(os.path.join(out_dir, "pet.json"), "w", encoding="utf-8") as f:
                json.dump({"face": meta}, f, ensure_ascii=False, indent=2)
            print("[pet] 已识别人脸位置，装饰品/表情会自动适配")
        self._set_skin(os.path.basename(out_dir))
        if listbox is not None:
            listbox.delete(0, "end")
            for n in self._list_skins():
                listbox.insert("end", n)
        self.say("新形象来了！")

    @staticmethod
    def _write_theme_json(out_dir, name):
        manifest = {
            "name": name,
            "fallback": "pet.png",
            "states": {},
            "说明": "把 happy.png / angry.png / furious.png / celebrate.png / error.png / sleep.png 放进本目录即可单独换该状态的表情。",
        }
        with open(os.path.join(out_dir, "theme.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _import_theme_zip(self, listbox=None):
        path = filedialog.askopenfilename(
            parent=self.root,
            title="选择主题包（zip）",
            filetypes=[("主题包", "*.zip"), ("所有文件", "*.*")],
        )
        if not path:
            return
        ok, msg = theme_mod.import_theme_zip(path)
        if not ok:
            from tkinter import messagebox
            messagebox.showerror("导入失败", msg, parent=self.root)
            return
        print("[pet]", msg)
        # 自动切换到新主题
        skin_name = msg.split(": ")[-1]
        if listbox is not None:
            listbox.delete(0, "end")
            for n in self._list_skins():
                listbox.insert("end", n)
        self._set_skin(skin_name)
        self.say("主题包已导入！")

    # ---------- 监督线程 -> 主线程 ----------
    def say(self, text, seconds=4):
        self._queue.put(("say", (text, seconds)))

    def set_mood(self, mood):
        mood = int(max(0, min(4, mood)))
        self.mood = mood
        self.sm.set_mood(mood)
        self._queue.put(("mood", (mood,)))

    def play_state(self, state, seconds=3.0):
        """播放瞬时状态（celebrate/error）。"""
        self._queue.put(("state", (state, float(seconds))))

    def set_sleeping(self, on):
        self._queue.put(("sleep", (bool(on),)))

    def celebrate(self, text=None, seconds=3.5):
        if text:
            self.say(text, max(4, seconds + 0.5))
        self.play_state("celebrate", seconds)

    def show_error(self, text=None, seconds=3.0):
        if text:
            self.say(text, max(4, seconds + 1.0))
        self.play_state("error", seconds)

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
                elif kind == "state":
                    state, seconds = args
                    self.sm.play(state, seconds)
                elif kind == "sleep":
                    self.sm.set_sleeping(args[0])
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
        state = self.sm.current()
        bob = math.sin(self._t * 2.5) * 4.0
        shake = math.sin(self._t * 40.0) * 3.0 if (self.mood >= 3 or self.block_mode) else 0.0
        # 脚下阴影
        pet_renderer.draw_shadow(c, cx, cy + bob, 40.0)
        # 宠物本体（按状态选图；没有图走程序化小猫）
        img = self._image_for(state)
        if img is not None:
            self._draw_image(c, cx, cy + bob, shake, state)
        else:
            lean = self._look_dx * 3 if self._looking else 0.0
            pet_renderer.draw_procedural_pet(
                c, cx + lean, cy + bob, shake, self.mood, self.level,
                accessory=self.accessory, t=self._t, show_level=True,
                look=(self._look_dx, self._look_dy) if self._looking else None)
        # 状态特效
        if state == "celebrate":
            pet_renderer.draw_celebrate_effects(c, cx, cy + bob, self._t)
        elif state == "error":
            pet_renderer.draw_error_effects(c, cx, cy + bob, self._t)
        elif state == "sleep":
            pet_renderer.draw_sleep_effects(c, cx, cy + bob, self._t)
        self._draw_bubble(c, w, h)

    def _draw_image(self, c, cx, cy, shake, state):
        if state not in self._skin_disp:
            base = self._image_for(state)
            if base is None:
                return
            iw, ih = base.width(), base.height()
            w = c.winfo_width() or NORMAL_SIZE[0]
            h = c.winfo_height() or NORMAL_SIZE[1]
            if iw > w or ih > h:
                factor_x = iw // w + (1 if iw % w else 0)
                factor_y = ih // h + (1 if ih % h else 0)
                factor = max(1, max(factor_x, factor_y))
                self._skin_disp[state] = base.subsample(factor, factor)
            else:
                self._skin_disp[state] = base
        disp = self._skin_disp[state]
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

    def _draw_bubble(self, c, w, h):
        if not self.bubble_text or time.time() > self._bubble_until:
            return
        text = self.bubble_text
        bx, by, bw, bh = 8, 8, min(w - 16, 220), 46
        r = 10
        # 圆角气泡
        c.create_oval(bx, by, bx + 2 * r, by + 2 * r, fill="white", outline="#dddddd")
        c.create_oval(bx + bw - 2 * r, by, bx + bw, by + 2 * r, fill="white", outline="#dddddd")
        c.create_oval(bx, by + bh - 2 * r, bx + 2 * r, by + bh, fill="white", outline="#dddddd")
        c.create_oval(bx + bw - 2 * r, by + bh - 2 * r, bx + bw, by + bh, fill="white", outline="#dddddd")
        c.create_rectangle(bx + r, by, bx + bw - r, by + bh, fill="white", outline="#dddddd")
        c.create_rectangle(bx, by + r, bx + bw, by + bh - r, fill="white", outline="#dddddd")
        # 小尾巴
        c.create_polygon(bx + 24, by + bh - 2, bx + 34, by + bh + 10,
                         bx + 44, by + bh - 2, fill="white", outline="")
        c.create_text(bx + bw / 2, by + bh / 2, text=text, width=bw - 16,
                      fill="#333333", font=("Microsoft YaHei UI", 9))
