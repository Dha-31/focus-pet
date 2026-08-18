# -*- coding: utf-8 -*-
"""ui/web_pet/pet_electron.py：Electron 桌宠窗口（正式版，v4.0.4）。

- 主窗口：Electron 透明桌宠（HTML），透明+置顶+鼠标穿透。
- 辅助窗口/对话框：隐藏在 Tk root（self.root）上打开，接口对齐 PetApp，
  main.py 可无感切换（Electron 优先，失败回退 Tk）。
- 本地 HTTP（127.0.0.1 动态端口）与 Electron 主进程通信：
    GET  /pet/outbox   Python 待推状态（Electron 轮询）
    POST /pet/command  前端菜单命令上报（Electron -> Python）
"""
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ELECTRON_EXE = os.path.join(PROJECT_ROOT, "tools", "electron", "runtime", "electron.exe")
DESKTOP_DIR = os.path.join(PROJECT_ROOT, "desktop")

# 前端命令 -> (回调名, 参数)。特殊命令单独处理。
_SIMPLE_CMDS = {
    "menu_end_study": ("end_study", ()),
    "menu_toggle_pomodoro": ("toggle_pomodoro", ()),
    "menu_pet": ("pet", ()),
    "menu_checkin": ("checkin", ()),
    "menu_mode_daily": ("mode", ("daily",)),
    "menu_mode_exam": ("mode", ("exam",)),
    "menu_mode_relaxed": ("mode", ("relaxed",)),
    "menu_mode_custom": ("mode", ("custom",)),
    "menu_toggle_dnd": ("toggle_dnd", ()),
    "menu_toggle_mini": ("toggle_mini", ()),
    "menu_open_settings": ("open_settings", ()),
    "menu_open_rules": ("open_rules", ()),
    "menu_open_help": ("open_help", ()),
    "menu_open_report": ("open_report", ()),
    "menu_open_achievements": ("open_achievements", ()),
}
_SPECIAL_CMDS = {"menu_start_study", "menu_feed", "menu_toggle_autostart",
                 "menu_open_space", "menu_open_shop", "menu_exit"}


class _Handler(BaseHTTPRequestHandler):
    server_version = "FocusPetPet/0.1"

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self._send(200, {})

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/pet/outbox":
            self._send(200, self.server.pet.take_outbox())
        elif path == "/api/settings":
            try:
                from core.config import load_config
                from core.settings import settings as _sm
                self._send(200, {"config": load_config(), "settings": _sm.get_dict()})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/schema":
            try:
                from core.settings_schema import CONFIG_SCHEMA, SETTINGS_SCHEMA
                self._send(200, {"config_schema": CONFIG_SCHEMA, "settings_schema": SETTINGS_SCHEMA})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/help":
            try:
                from core import help_data
                self._send(200, {"version": help_data.VERSION, "features": help_data.FEATURES,
                                 "hotkeys": help_data.hotkeys_help(), "settings": help_data.settings_help()})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/achievements":
            try:
                from core.achievements import ACHIEVEMENTS, AchievementManager
                from core.medals import MEDALS, TYPE_NAMES, MedalManager
                am = AchievementManager()
                mm = MedalManager()
                mm.evaluate()
                self._send(200, {"achievements": ACHIEVEMENTS, "unlocked": am.unlocked,
                                 "medals": MEDALS, "medal_types": TYPE_NAMES,
                                 "medal_status": mm.status(), "stats": mm.period_stats()})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/rules":
            try:
                import json as _j, os as _o
                from core.config import DATA_DIR
                def _read(name):
                    fp = _o.path.join(DATA_DIR, name)
                    if _o.path.exists(fp):
                        try:
                            with open(fp, "r", encoding="utf-8-sig") as f:
                                return _j.load(f)
                        except Exception:
                            pass
                    return {"urls": [], "processes": [], "titles": []}
                self._send(200, {"whitelist": _read("whitelist.json"),
                                 "blacklist": _read("blacklist.json"),
                                 "learned": _read("learned.json")})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/report":
            try:
                import json as _j, os as _o
                from core.config import DATA_DIR
                def _read(name):
                    fp = _o.path.join(DATA_DIR, name)
                    if _o.path.exists(fp):
                        try:
                            with open(fp, "r", encoding="utf-8-sig") as f:
                                return _j.load(f)
                        except Exception:
                            pass
                    return []
                sessions = _read("focus_log.json") or []
                events = _read("events.json") or []
                dist = [e for e in events if isinstance(e, dict) and e.get("kind") == "distraction"]
                total_focus = sum(s.get("focus_minutes", 0) for s in sessions if isinstance(s, dict))
                total_dist = sum(s.get("distract_minutes", 0) for s in sessions if isinstance(s, dict))
                self._send(200, {
                    "total_focus": round(total_focus, 1),
                    "total_distract": round(total_dist, 1),
                    "session_count": len(sessions),
                    "distract_count": len(dist),
                    "recent_distract": dist[-8:],
                    "sessions": sessions[-14:],
                })
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/shop":
            try:
                from core import shop as _shop
                from core.economy import Inventory
                inv = Inventory()
                items = [dict(it, price=_shop.price_of(it)) for it in _shop.FURNITURE]
                self._send(200, {"furniture": items, "scenes": _shop.FURNITURE_SCENES,
                                 "inventory": {"coins": round(inv.coins, 1),
                                               "owned_furniture": inv.owned_furniture,
                                               "placed_furniture": inv.placed_furniture}})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/space":
            try:
                from core import shop as _shop
                from core.economy import Inventory
                from ui.space_window import load_layout, SCENES, DEFAULT_SCENE
                inv = Inventory()
                furn_pos, pet_pos = load_layout("")
                import json as _j, os as _o
                from core.config import DATA_DIR
                scene = DEFAULT_SCENE
                try:
                    with open(_o.path.join(DATA_DIR, "space.json"), "r", encoding="utf-8-sig") as f:
                        scene = _j.load(f).get("scene", DEFAULT_SCENE)
                except Exception:
                    pass
                self._send(200, {"scene": scene if scene in SCENES else DEFAULT_SCENE,
                                 "scenes": {k: v["name"] for k, v in SCENES.items()},
                                 "furniture_pos": furn_pos, "pet_pos": list(pet_pos),
                                 "placed": inv.placed_furniture,
                                 "furniture": _shop.FURNITURE})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/status":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/pet/command":
            data = self._json_body()
            self.server.pet.on_command(data.get("name"), data.get("args") or [])
            self._send(200, {"ok": True})
        elif path == "/api/settings":
            try:
                from core.config import save_config
                from core.settings import SETTINGS_PATH, settings as _sm
                data = self._json_body()
                if isinstance(data.get("config"), dict):
                    save_config(data["config"])
                if isinstance(data.get("settings"), dict):
                    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                        json.dump(data["settings"], f, ensure_ascii=False, indent=2)
                    _sm.reload()
                self._send(200, {"ok": True})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/rules":
            try:
                import json as _j, os as _o
                from core.config import DATA_DIR
                data = self._json_body()
                for key, fname in (("whitelist", "whitelist.json"), ("blacklist", "blacklist.json")):
                    val = data.get(key)
                    if isinstance(val, dict):
                        clean = {k: list(v) for k, v in val.items() if isinstance(v, list)}
                        with open(_o.path.join(DATA_DIR, fname), "w", encoding="utf-8") as f:
                            _j.dump(clean, f, ensure_ascii=False, indent=2)
                self._send(200, {"ok": True})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/shop/buy":
            try:
                from core import shop as _shop
                from core.economy import Inventory
                data = self._json_body()
                inv = Inventory()
                it = _shop.get_furniture(data.get("id", ""))
                if it is None:
                    self._send(404, {"error": "no such furniture"})
                elif inv.buy(it):
                    self._send(200, {"ok": True, "coins": round(inv.coins, 1)})
                else:
                    self._send(200, {"ok": False, "reason": "coins"})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/shop/place":
            try:
                from core import shop as _shop
                from core.economy import Inventory
                data = self._json_body()
                inv = Inventory()
                it = _shop.get_furniture(data.get("id", ""))
                if it is None:
                    self._send(404, {"error": "no such furniture"})
                elif inv.place(it["id"], scene=it.get("scene", "cozy")):
                    self._send(200, {"ok": True})
                else:
                    self._send(200, {"ok": False, "reason": "not owned"})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        elif path == "/api/space":
            try:
                import json as _j, os as _o
                from core.config import DATA_DIR
                data = self._json_body()
                with open(_o.path.join(DATA_DIR, "space.json"), "w", encoding="utf-8") as f:
                    _j.dump(data, f, ensure_ascii=False, indent=2)
                self._send(200, {"ok": True})
            except Exception as exc:
                self._send(500, {"error": str(exc)})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass


class ElectronPetWindow:
    """Electron 桌宠窗口。say/set_mood 等线程安全；辅助窗口用 self.root（隐藏 Tk）。"""

    def __init__(self, width=520, height=380, callbacks=None, x=100, y=100,
                 on_exit=None, inventory=None, mode="daily"):
        self.width = width
        self.height = height
        self.callbacks = callbacks or {}
        self._on_exit = on_exit
        self._outbox = []
        self._seq = 0
        self._lock = threading.Lock()
        self._server = None
        self._proc = None
        self._started = False
        self._x = x
        self._y = y
        # 与 PetApp 兼容的属性
        self.dnd = False
        self.tray_enabled = False
        self.on_skin_changed = None
        self.skin = "default"
        self.mood = 0
        self.level = 1
        self.skin_face = None
        self._t = 0.0
        self.closed = False
        self.mode = mode
        self.root = None          # 隐藏 Tk root（辅助窗口/对话框宿主）
        self.inventory = inventory
        self._space_win = None
        self.latest_info = None

    # ---------- 对外接口（对齐 PetApp） ----------
    def say(self, text, seconds=4):
        self._push({"say": text, "seconds": float(seconds)})

    def set_mood(self, mood):
        self.mood = int(mood)
        self._push({"mood": self.mood})

    def set_sleeping(self, on):
        self._push({"sleep": bool(on)})

    def set_mini(self, on):
        self._push({"mini": bool(on)})

    def set_activity(self, cat, focus_streak):
        self._push({"activity": cat, "focusStreak": float(focus_streak)})

    def set_level(self, level):
        self.level = int(level)
        self._push({"level": self.level})

    def set_mode(self, mode):
        self.mode = mode
        self._push({"mode": mode})

    def set_work(self, active, remaining=0):
        self._push({"work": {"active": bool(active), "remaining": float(remaining)}})

    def set_dnd(self, on):
        self.dnd = bool(on)
        self._push({"dnd": self.dnd})

    def set_pomodoro_enabled(self, enabled):
        self._push({"pomodoro": bool(enabled)})

    def update_info(self, info):
        self.latest_info = info
        self._push({"info": info})

    def block(self, on):
        self._push({"block": bool(on)})

    def play_state(self, state, seconds=3.0):
        self._push({"state": state, "seconds": float(seconds)})

    def celebrate(self, text=None, seconds=3.5):
        if text:
            self.say(text, max(4, seconds + 0.5))
        self.play_state("celebrate", seconds)

    def show_error(self, text=None, seconds=3.0):
        if text:
            self.say(text, max(4, seconds + 1.0))
        self.play_state("error", seconds)

    def toggle_visible(self):
        self._push({"_action": "toggle_visible"})

    def open_window(self, name):
        """让 Electron 打开一个 HTML 辅助窗口（settings/rules/help/space/shop/report/achievements）。"""
        self._push({"_action": "open_window", "window": name})

    def hide(self):
        self._push({"_action": "toggle_visible"})

    def show(self):
        self._push({"_action": "toggle_visible"})

    # ---------- 内部 ----------
    def _push(self, state):
        with self._lock:
            self._seq += 1
            self._outbox.append({"seq": self._seq, "state": state})

    def take_outbox(self):
        with self._lock:
            if not self._outbox:
                return {"seq": 0, "state": {}}
            merged = {}
            seq = 0
            for item in self._outbox:
                merged.update(item["state"])
                seq = item["seq"]
            self._outbox.clear()
            return {"seq": seq, "state": merged}

    # ---------- 菜单命令 ----------
    def on_command(self, name, args):
        def run():
            if name in _SPECIAL_CMDS:
                self._special(name)
            elif name in _SIMPLE_CMDS:
                key, cargs = _SIMPLE_CMDS[name]
                fn = self.callbacks.get(key)
                if fn:
                    try:
                        fn(*cargs)
                    except Exception as exc:
                        print(f"[pet_electron] cmd {name} error:", exc)
        if self.root is not None:
            self.root.after(0, run)
        else:
            run()

    def _special(self, name):
        if name == "menu_start_study":
            self._menu_start_study()
        elif name == "menu_feed":
            self._menu_feed()
        elif name == "menu_toggle_autostart":
            self._toggle_autostart()
        elif name == "menu_open_space":
            self._open_space()
        elif name == "menu_open_shop":
            self._open_shop()
        elif name == "menu_exit":
            # 前端已最小化到托盘，这里仅通知（保存/清理），不真正退出
            fn = self.callbacks.get("exit")
            if fn:
                try:
                    fn()
                except Exception as exc:
                    print("[pet_electron] exit cb error:", exc)

    def _menu_start_study(self):
        if self.callbacks.get("start_study") is None:
            return
        from tkinter import simpledialog
        goal = simpledialog.askstring("开始学习", "今天学什么？", parent=self.root)
        if goal is None:
            return
        minutes = simpledialog.askstring("学习时长", "这次学多久？\n（分钟，留空 = 不限时长）", parent=self.root)
        try:
            minutes = int(minutes) if minutes and int(minutes) > 0 else None
        except ValueError:
            minutes = None
        self.callbacks["start_study"](goal.strip() or "学习", minutes)

    def _menu_feed(self):
        if self.callbacks.get("feed") is None:
            return
        from core import settings as _s
        items = _s.settings.get("feed.items") or []
        if not items:
            self.say("没有食物了…")
            return
        opts = [(it.get("id"), f"{it.get('name')}（{it.get('price')} 币，+{it.get('affinity')} 好感）")
                for it in items]
        pick = self._choice_dialog("投喂", "选一个喂给宠物（花专注币加好感）：", opts)
        if not pick:
            return
        for it in items:
            if it.get("id") == pick:
                self.callbacks["feed"](it)
                return

    def _toggle_autostart(self):
        from core import autostart
        if autostart.is_enabled():
            autostart.disable()
            self.say("已关闭开机自启")
        else:
            ok = autostart.enable()
            self.say("已开启开机自启" if ok else "开机自启设置失败")

    def _choice_dialog(self, title, prompt, options):
        import tkinter as tk
        from ui import window_manager
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("520x320")
        try:
            dlg.attributes("-topmost", True)
        except tk.TclError:
            pass
        window_manager.open(dlg)
        result = [None]
        tk.Label(dlg, text=prompt, font=("Microsoft YaHei UI", 11), justify="left",
                 wraplength=480).pack(padx=16, pady=(16, 10))

        def choose(v):
            result[0] = v
            dlg.destroy()

        for v, label in options:
            tk.Button(dlg, text=label, font=("Microsoft YaHei UI", 11),
                      command=lambda v=v: choose(v)).pack(fill="x", padx=40, pady=4)
        tk.Button(dlg, text="取消", command=dlg.destroy).pack(pady=6)
        dlg.grab_set()
        self.root.wait_window(dlg)
        return result[0]

    # ---------- 商店 / 空间（辅助窗口，Tk 宿主） ----------
    def _open_shop(self):
        from ui import window_manager
        from ui.shop_window import ShopWindow
        win = ShopWindow(self.root, self.inventory,
                         on_place=lambda fid: self.refresh_space(),
                         skin=self.skin)
        window_manager.open(win.root)

    def _open_space(self):
        from ui import window_manager
        from ui.space_window import SpaceWindow
        self._space_win = SpaceWindow(self.root, self.inventory, self)
        window_manager.open(self._space_win.root)

    def refresh_space(self):
        win = getattr(self, "_space_win", None)
        if win is not None:
            try:
                win._draw()
            except Exception:
                pass

    def _image_for(self, state):
        """从主题加载状态图（Tk PhotoImage），用于辅助窗口/空间。"""
        try:
            from core import theme as theme_mod
            path = theme_mod.resolve_image_file(self.skin, state)
            if path:
                import tkinter as tk
                return tk.PhotoImage(file=path)
        except Exception:
            pass
        return None

    # ---------- 启动 / 销毁 ----------
    def start(self, on_started=None):
        if self._started:
            return
        self._started = True
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Focus Pet 辅助")
        try:
            self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
            self._server.pet = self
            threading.Thread(target=self._server.serve_forever, daemon=True).start()
            port = self._server.server_address[1]
            print(f"[pet_electron] 本地桥接端口 {port}", flush=True)
            env = dict(os.environ)
            env["FOCUS_PET_PORT"] = str(port)
            env["FOCUS_PET_X"] = str(int(self._x))
            env["FOCUS_PET_Y"] = str(int(self._y))
            self._proc = subprocess.Popen(
                [ELECTRON_EXE, DESKTOP_DIR], env=env, cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,   # stderr 继承父进程，便于捕获渲染 console
            )
        except Exception as exc:
            print("[pet_electron] start error:", exc)
            self._started = False
            raise
        threading.Thread(target=self._watch_proc, daemon=True).start()
        if on_started:
            on_started()

    def _watch_proc(self):
        if self._proc is None:
            return
        print("[pet_electron] watch: waiting electron exit", flush=True)
        try:
            self._proc.wait()
        except Exception:
            pass
        print("[pet_electron] watch: electron exited, cleaning", flush=True)
        self._proc = None
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None
        if self.root is not None:
            # 切到 Tk 主线程退出 mainloop（后台线程直接 quit 不生效）
            try:
                self.root.after(0, self.root.quit)
            except Exception:
                try:
                    self.root.quit()
                except Exception:
                    pass
        if self._on_exit:
            try:
                self._on_exit()
            except Exception as exc:
                print("[pet_electron] on_exit error:", exc)

    def destroy(self):
        if self._proc is not None and self._proc.poll() is None:
            try:
                subprocess.run(["taskkill", "/PID", str(self._proc.pid), "/T", "/F"],
                               capture_output=True)
            except Exception:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
            self._proc = None
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass
            self._server = None
