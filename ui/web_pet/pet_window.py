# -*- coding: utf-8 -*-
"""ui/web_pet/pet_window.py：pywebview 版桌宠主窗口（v4.0.4 交互界面升级）。

- HTML/CSS/JS 渲染形象 + 气泡 + 自定义右键菜单 + 动效；
- 透明、无边框、置顶、可拖拽；
- 透明修复：pywebview 在 Windows 只把 WebView2 背景设为透明，
  这里补上承载 Form 的透明 + WS_EX_NOREDIRECTIONBITMAP，才能真透出桌面。
"""
import ctypes
import json
import os
import threading

import webview

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")


class _Api:
    """暴露给 JS 的 window.pywebview.api 方法（右键菜单回调）。"""

    def __init__(self, owner):
        self._owner = owner

    def _cb(self, name, *args):
        fn = self._owner.callbacks.get(name)
        if fn:
            try:
                fn(*args)
            except Exception as exc:
                print(f"[web_pet] callback {name} error:", exc)

    def menu_start_study(self): self._cb("start_study")
    def menu_end_study(self): self._cb("end_study")
    def menu_toggle_pomodoro(self): self._cb("toggle_pomodoro")
    def menu_pet(self): self._cb("pet")
    def menu_feed(self): self._cb("feed")
    def menu_work(self): self._cb("work")
    def menu_checkin(self): self._cb("checkin")
    def menu_mode_daily(self): self._cb("mode", "daily")
    def menu_mode_exam(self): self._cb("mode", "exam")
    def menu_mode_relaxed(self): self._cb("mode", "relaxed")
    def menu_mode_custom(self): self._cb("mode", "custom")
    def menu_toggle_dnd(self): self._cb("toggle_dnd")
    def menu_toggle_mini(self): self._cb("toggle_mini")
    def menu_open_settings(self): self._cb("open_settings")
    def menu_open_rules(self): self._cb("open_rules")
    def menu_open_help(self): self._cb("open_help")
    def menu_open_space(self): self._cb("open_space")
    def menu_open_shop(self): self._cb("open_shop")
    def menu_open_report(self): self._cb("open_report")
    def menu_open_achievements(self): self._cb("open_achievements")
    def menu_exit(self): self._cb("exit")


class WebPetWindow:
    """pywebview 桌宠窗口。say/set_mood 等方法线程安全，start 前调用会排队。"""

    def __init__(self, width=520, height=380, callbacks=None):
        self.width = width
        self.height = height
        self.callbacks = callbacks or {}
        self.window = None
        self.api = _Api(self)
        self._ready = False
        self._closed = False
        self._pending = []
        self._lock = threading.Lock()

    # ---------- 对外接口（对齐 PetApp） ----------
    def _enqueue(self, name, args):
        with self._lock:
            self._pending.append((name, args))
        self._flush()

    def _flush(self):
        if not self._ready or self.window is None:
            return
        with self._lock:
            items = self._pending
            self._pending = []
        for name, args in items:
            self._dispatch(name, args)

    def _dispatch(self, name, args):
        try:
            if name == "say":
                text, seconds = args
                self._js("window.pet.say({}, {})".format(
                    json.dumps(text), json.dumps(float(seconds))))
            elif name == "mood":
                self._js("window.pet.setMood({})".format(int(args[0])))
            elif name == "sleep":
                self._js("window.pet.setSleeping({})".format("true" if args[0] else "false"))
            elif name == "mini":
                self._js("window.pet.setMini({})".format("true" if args[0] else "false"))
            elif name == "activity":
                self._js("window.pet.setActivity({}, {})".format(
                    json.dumps(args[0]), json.dumps(float(args[1]))))
            elif name == "level":
                self._js("window.pet.setLevel({})".format(int(args[0])))
            elif name == "mode":
                self._js("window.pet.setMode({})".format(json.dumps(args[0])))
            elif name == "work":
                self._js("window.pet.setWork({}, {})".format(
                    "true" if args[0] else "false", json.dumps(float(args[1]))))
            elif name == "dnd":
                self._js("window.pet.setDnd({})".format("true" if args[0] else "false"))
            elif name == "pomodoro":
                self._js("window.pet.setPomodoro({})".format("true" if args[0] else "false"))
            elif name == "info":
                self._js("window.pet.updateInfo({})".format(json.dumps(args[0], ensure_ascii=False)))
            elif name == "block":
                self._js("window.pet.block({})".format("true" if args[0] else "false"))
            elif name == "state":
                self._js("window.pet.playState({}, {})".format(
                    json.dumps(args[0]), json.dumps(float(args[1]))))
        except Exception as exc:
            print("[web_pet] dispatch error:", exc)

    def _js(self, expr):
        if self.window is None:
            return
        try:
            self.window.evaluate_js(expr)
        except Exception as exc:
            print("[web_pet] evaluate_js error:", exc)

    # 与 PetApp 同名的方法（线程安全）
    def say(self, text, seconds=4):
        self._enqueue("say", (text, seconds))

    def set_mood(self, mood):
        self._enqueue("mood", (int(mood),))

    def set_sleeping(self, on):
        self._enqueue("sleep", (bool(on),))

    def set_mini(self, on):
        self._enqueue("mini", (bool(on),))

    def set_activity(self, cat, focus_streak):
        self._enqueue("activity", (cat, float(focus_streak)))

    def set_level(self, level):
        self._enqueue("level", (int(level),))

    def set_mode(self, mode):
        self._enqueue("mode", (mode,))

    def set_work(self, active, remaining=0):
        self._enqueue("work", (bool(active), float(remaining)))

    def set_dnd(self, on):
        self._enqueue("dnd", (bool(on),))

    def set_pomodoro_enabled(self, enabled):
        self._enqueue("pomodoro", (bool(enabled),))

    def update_info(self, info):
        self._enqueue("info", (info,))

    def block(self, on):
        self._enqueue("block", (bool(on),))

    def play_state(self, state, seconds=3.0):
        self._enqueue("state", (state, float(seconds)))

    def celebrate(self, text=None, seconds=3.5):
        if text:
            self.say(text, max(4, seconds + 0.5))
        self.play_state("celebrate", seconds)

    def show_error(self, text=None, seconds=3.0):
        if text:
            self.say(text, max(4, seconds + 1.0))
        self.play_state("error", seconds)

    # ---------- 透明修复 ----------
    def _apply_transparency(self):
        """pywebview 6.x 在 Windows 上需补 Form 透明 + 窗口样式才能真透明。"""
        try:
            from webview.platforms import winforms
            from System import Func, Object
            from System.Drawing import Color
            user32 = ctypes.windll.user32
            form = list(winforms.BrowserView.instances.values())[0]

            def do():
                try:
                    form.webview.DefaultBackgroundColor = Color.Transparent
                    form.BackColor = Color.Transparent
                    hwnd = int(form.Handle.ToInt32())
                    ex = user32.GetWindowLongW(hwnd, -20)
                    # WS_EX_NOREDIRECTIONBITMAP (0x00200000)：让 DWM 处理透明合成
                    user32.SetWindowLongW(hwnd, -20, ex | 0x00200000)
                    user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                        0x0002 | 0x0001 | 0x0004 | 0x0010 | 0x0020)
                except Exception as exc:
                    print("[web_pet] transparent fix inner error:", exc)
                return None

            form.webview.Invoke(Func[Object](do))
            print("[web_pet] transparency fix applied")
        except Exception as exc:
            print("[web_pet] transparency fix unavailable:", exc)

    # ---------- 启动 ----------
    def start(self, on_started=None):
        self.window = webview.create_window(
            "Focus Pet", url=INDEX, width=self.width, height=self.height,
            frameless=True, transparent=True, on_top=True, easy_drag=True,
            js_api=self.api)

        def _ready():
            # 等窗口真正创建（BrowserView.instances 填充）再执行透明修复
            try:
                self.window.events.shown.wait(15)
            except Exception:
                pass
            import time as _t
            try:
                from webview.platforms import winforms
                for _ in range(50):
                    if winforms.BrowserView.instances:
                        break
                    _t.sleep(0.1)
            except Exception:
                pass
            self._apply_transparency()
            self._ready = True
            self._flush()
            if on_started:
                on_started()

        # CEF 后端：透明窗口在集显/无独显机器上更可靠（v4.0.4 选型）
        webview.start(_ready, gui="cef")

    def destroy(self):
        self._closed = True
        if self.window is not None:
            try:
                self.window.destroy()
            except Exception:
                pass
