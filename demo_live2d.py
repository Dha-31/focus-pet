# -*- coding: utf-8 -*-
"""Live2D 桌宠演示：显示猫模型，每 5 秒自动切换情绪 + 播放动作。关闭窗口即退出。"""
import os, sys, threading
sys.path.insert(0, os.getcwd())
import webview

INDEX = os.path.abspath("ui/live2d/assets/index.html")
window = webview.create_window(
    "Focus Pet Live2D", url=INDEX,
    width=480, height=480, frameless=True, transparent=True, on_top=True, easy_drag=True)

moods = [0, 1, 2, 3, 4, 3, 2, 1]
i = 0

def on_started():
    def cycle():
        global i
        m = moods[i % len(moods)]
        print("情绪:", ["开心", "好奇", "不耐烦", "生气", "暴怒"][m])
        window.evaluate_js(f"window.setMood({m})")
        if m >= 3:
            window.evaluate_js("window.playMotion()")
        i += 1
        threading.Timer(4, cycle).start()
    threading.Timer(3, cycle).start()

print("Live2D 桌宠启动，关闭窗口退出")
webview.start(on_started, debug=False)
