"""core/sounds.py：提示音效（v3.6）。

- 用 winsound.Beep 合成简单旋律（零依赖，不打包音频文件）
- set_muted()：免打扰时整体静音（全局标志，主程序/桌宠都能读到）
- play(kind)：后台线程播放，不阻塞主线程；失败静默

音效种类：start（开始学习）/ celebrate（完成/成就）/ alert（提醒）/
          error（出错）/ break（番茄钟休息）
"""
import threading
import time

try:
    import winsound
    _HAS_WINSOUND = True
except Exception:
    _HAS_WINSOUND = False

_muted = False

# 音效 -> [(频率Hz, 时长ms), ...]
_MELODIES = {
    "start":     [(660, 100), (880, 150)],
    "celebrate": [(523, 100), (659, 100), (784, 200)],
    "alert":     [(880, 90), (880, 90)],
    "error":     [(220, 200), (165, 300)],
    "break":     [(440, 120), (550, 120), (660, 160)],
}


def set_muted(on):
    global _muted
    _muted = bool(on)


def is_muted():
    return _muted


def play(kind):
    """后台线程播放音效；静音时直接跳过。"""
    if not _HAS_WINSOUND or _muted:
        return
    notes = _MELODIES.get(kind)
    if not notes:
        return

    def _run():
        try:
            for freq, dur in notes:
                winsound.Beep(int(freq), int(dur))
                time.sleep(0.03)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
