"""ui/live2d/live2d_window.py：Live2D 桌宠窗口（pywebview + WebView2 渲染）。

v4.0.4 第一步：透明置顶无边框窗口，加载 Live2D 模型，支持情绪切表情、播放动作。
经典模式（Tk 小猫）保留为回退。
"""
import os
import threading

import webview

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
INDEX_PATH = os.path.join(ASSETS_DIR, "index.html")


class Live2DWindow:
    """一个独立的 Live2D 桌宠窗口。在独立线程启动。"""

    def __init__(self, size=(480, 480)):
        self.size = size
        self._window = None
        self._thread = None
        self._closed = threading.Event()

    # ---------- 启动 ----------
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            self._window = webview.create_window(
                "Focus Pet Live2D",
                url=INDEX_PATH,
                width=self.size[0],
                height=self.size[1],
                frameless=True,
                transparent=True,
                on_top=True,
                easy_drag=True,
            )
            webview.start(debug=False)
        finally:
            self._closed.set()

    # ---------- 控制 ----------
    def set_mood(self, mood):
        """设置情绪（0=开心，1=好奇，2=不耐烦，3=生气，4=暴怒）。"""
        self._eval(f"window.setMood && window.setMood({int(mood)})")

    def play_motion(self):
        """播放一个随机/默认动作。"""
        self._eval("window.playMotion && window.playMotion()")

    def _eval(self, js):
        if self._window is None:
            return
        try:
            self._window.evaluate_js(js)
        except Exception:
            pass

    def close(self):
        try:
            if self._window is not None:
                self._window.destroy()
        except Exception:
            pass
        self._closed.set()

