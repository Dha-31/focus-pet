"""tools/collect_dataset.py：采集你的真实屏幕数据（提升准确率的关键）。

用法：python tools/collect_dataset.py
流程：
1. 打开一个"学习"窗口（文档/代码/网课），回车 -> 输入 s 保存为学习
2. 打开一个"分心"窗口（游戏/直播/购物），回车 -> 输入 d 保存为分心
3. q 退出。每种最好采 20-50 张。
采集完后运行: python tools/train_classifier.py 重新训练。
"""
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from PIL import ImageGrab  # noqa: E402

from sensors.screen_analyzer import capture_screen  # noqa: E402
from sensors.window_monitor import get_foreground_info  # noqa: E402


def save_screenshot(label):
    folder = os.path.join(PROJECT_ROOT, "dataset", label)
    os.makedirs(folder, exist_ok=True)
    n = len([f for f in os.listdir(folder) if f.endswith(".png")])
    info = get_foreground_info()
    img = capture_screen(info["hwnd"] if info else None)
    if img is None:
        print("  截图失败，跳过")
        return
    if img.height > 120:
        img = img.crop((0, 56, img.width, img.height))  # 裁掉标题栏/标签栏
    path = os.path.join(folder, f"real_{n + 1:03d}.png")
    img.save(path)
    print(f"  已保存: {path}")


def main():
    print("真实数据采集器")
    print("  s = 保存为【学习】  d = 保存为【分心】  q = 退出")
    print("每次：先切到目标窗口（别挡屏幕），再回来按 s/d")
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "q":
            print("采集结束。运行 python tools/train_classifier.py 重新训练")
            break
        elif cmd == "s":
            save_screenshot("study")
        elif cmd == "d":
            save_screenshot("distraction")
        else:
            print("请输入 s / d / q")
        time.sleep(0.3)


if __name__ == "__main__":
    main()