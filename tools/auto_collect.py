"""tools/auto_collect.py：半自动采集真实屏幕数据（自动打标签）。

原理：用"快速通道"（窗口标题 + 进程名 + 浏览器 URL）自动判定当前窗口：
- 判定为 study      -> 存到 dataset/study/
- 判定为 distraction -> 存到 dataset/distraction/
- 判定不了时，用截图分析（OCR+图案）再试一次；还是不确定就跳过

用法：
  python tools/auto_collect.py [采集秒数，默认 360] [每类目标张数，默认 30]

运行期间正常使用电脑：
- 前半段打开你的【学习】软件/网页（文档、代码编辑器、网课、笔记）
- 后半段打开你的【分心】软件/网页（视频、直播、游戏、购物、社交）
采集完运行 python tools/train_classifier.py 重新训练。
"""
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.config import load_config  # noqa: E402
from core.rules import RuleEngine  # noqa: E402
from sensors.window_monitor import get_foreground_info  # noqa: E402
from sensors.screen_analyzer import analyze_foreground  # noqa: E402


def _frame_diff(a, b):
    import numpy as np
    ga = np.asarray(a.convert("L").resize((64, 48)), dtype=np.float32)
    gb = np.asarray(b.convert("L").resize((64, 48)), dtype=np.float32)
    return float(np.abs(ga - gb).mean())


def _save(cat, img, counts):
    folder = os.path.join(PROJECT_ROOT, "dataset", cat)
    os.makedirs(folder, exist_ok=True)
    n = len([f for f in os.listdir(folder) if f.endswith(".png")])
    path = os.path.join(folder, f"real_{n + 1:03d}.png")
    img.save(path)
    counts[cat] += 1
    return path


def main():
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 360
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    cfg = load_config()
    rules = RuleEngine()

    # 浏览器 URL（如果启用了扩展桥接，标签页判定更准）
    bridge = None
    if cfg["extension"]["enabled"]:
        try:
            from bridge.server import start_bridge, get_latest_url
            bridge = start_bridge(rules, port=int(cfg["extension"]["port"]))
            print("[采集] 已启动本地桥接（可获取浏览器标签页 URL）")
        except Exception as exc:
            print("[采集] 桥接启动失败（不影响采集，只是浏览器标签页判定会弱一些）：", exc)

    counts = {"study": 0, "distraction": 0}
    last_img = None
    last_save_ts = 0.0
    start = time.time()
    print(f"自动采集开始：{duration} 秒，目标每类 {target} 张")
    print("现在正常使用电脑：先开【学习】软件，再开【分心】软件…（Ctrl+C 可提前结束）")

    while time.time() - start < duration:
        info = get_foreground_info()
        if info:
            url = None
            if bridge:
                latest = get_latest_url(bridge)
                if latest and (time.time() - latest["ts"]) < 5:
                    url = latest["url"]
            cat = rules.classify(title=info["title"], process=info["process"], url=url)
            proc_low = (info["process"] or "").lower()
            if proc_low in ("windowsterminal.exe", "powershell.exe", "cmd.exe", "conhost.exe"):
                cat = "skip"  # 终端模棱两可，跳过
            if cat == "unknown":
                # 快速通道判定不了，用截图分析兜底
                try:
                    res = analyze_foreground(info["hwnd"])
                    if res["category"] in ("study", "distraction"):
                        cat = res["category"]
                except Exception:
                    pass

            now = time.time()
            if cat in ("study", "distraction") and now - last_save_ts >= 5.0:

                from sensors.screen_analyzer import capture_screen
                img = capture_screen(info["hwnd"])
                if img is not None and img.height > 120:
                    img = img.crop((0, 56, img.width, img.height))  # 裁掉标题栏/标签栏
                if img is not None:
                    if last_img is None or _frame_diff(img, last_img) > 6:
                        last_img = img
                        path = _save(cat, img, counts)
                        last_save_ts = now
                        print(f"  [{cat}] {path} | {info['process']} | {info['title'][:30]}")

        elapsed = int(time.time() - start)
        if elapsed % 30 == 0 and elapsed > 0:
            print(f"  进度 {elapsed}/{duration} 秒 | 学习 {counts['study']} / 分心 {counts['distraction']}")
        if counts["study"] >= target and counts["distraction"] >= target:
            print("已达成目标数量，提前结束")
            break
        time.sleep(2.0)

    print(f"\n采集结束：学习 {counts['study']} 张 / 分心 {counts['distraction']} 张")
    if counts["study"] >= 5 and counts["distraction"] >= 5:
        print("运行 python tools/train_classifier.py 重新训练！")
    else:
        print("数据偏少：建议再采集一轮，或手动 python tools/collect_dataset.py 补采")
        print("然后运行 python tools/train_classifier.py 重新训练")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n手动停止。运行 python tools/train_classifier.py 重新训练")