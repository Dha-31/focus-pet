# -*- coding: utf-8 -*-
"""重写 demo_electron_pet.py：开机自启回调、退出走 on_exit、删除打工功能。"""
import os
import sys
import threading
import time

sys.path.insert(0, os.getcwd())

from ui.web_pet.pet_electron import ElectronPetWindow
from core import autostart


def main():
    win = ElectronPetWindow(on_exit=lambda: os._exit(0))

    def toggle_autostart():
        if autostart.is_enabled():
            autostart.disable()
            win.say("已关闭开机自启")
        else:
            ok = autostart.enable()
            win.say("已开启开机自启" if ok else "开机自启设置失败")

    win.callbacks.update({
        "start_study": lambda: win.say("开始学习啦（演示）"),
        "end_study": lambda: win.say("学习结束（演示）"),
        "pet": lambda: win.say("好舒服～（摸头演示）"),
        "feed": lambda: win.say("这个真好吃～（投喂演示）"),
        "checkin": lambda: win.say("打卡成功～（演示）"),
        "toggle_dnd": lambda: win.say("免打扰（演示）"),
        "toggle_mini": lambda: win.say("切换迷你（演示）"),
        "menu_toggle_autostart": toggle_autostart,
    })

    moods = [0, 1, 2, 3, 4, 3, 2, 1]
    texts = ["你好呀，我是会动的小黄猫～", "你在干嘛呢？", "专心一点哦！", "我有点生气啦！", "快回来学习！！"]
    idx = [0]

    def cycle():
        i = idx[0] % len(moods)
        m = moods[i]
        win.set_mood(m)
        win.say(texts[m], 3.2)
        idx[0] += 1
        threading.Timer(3.6, cycle).start()

    win.start()
    threading.Timer(1.0, cycle).start()
    print("Electron 桌宠已启动，关闭窗口或 Ctrl+C 退出")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        win.destroy()


if __name__ == "__main__":
    main()
