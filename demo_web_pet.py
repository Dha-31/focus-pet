# -*- coding: utf-8 -*-
"""demo_web_pet.py：v4.0.4 交互界面升级——HTML 桌宠主窗口演示。"""
import os
import sys
import threading

sys.path.insert(0, os.getcwd())

from ui.web_pet.pet_window import WebPetWindow


def main():
    win = WebPetWindow(width=520, height=380)
    win.callbacks.update({
        "start_study": lambda: win.say("开始学习啦（演示）"),
        "end_study": lambda: win.say("学习结束（演示）"),
        "pet": lambda: win.say("好舒服～（摸头演示）"),
        "feed": lambda: win.say("这个真好吃～（投喂演示）"),
        "checkin": lambda: win.say("打卡成功～（演示）"),
        "toggle_dnd": lambda: win.say("免打扰（演示）"),
        "toggle_mini": lambda: win.say("切换迷你（演示）"),
        "exit": lambda: win.destroy(),
    })

    moods = [0, 1, 2, 3, 4, 3, 2, 1]
    idx = [0]

    def on_started():
        def cycle():
            i = idx[0] % len(moods)
            m = moods[i]
            win.set_mood(m)
            texts = ["你好呀，我是会动的小黄猫～", "你在干嘛呢？", "专心一点哦！", "我有点生气啦！", "快回来学习！！"]
            win.say(texts[m], 3.2)
            idx[0] += 1
            threading.Timer(3.6, cycle).start()
        threading.Timer(0.6, cycle).start()

    win.start(on_started)


if __name__ == "__main__":
    main()
