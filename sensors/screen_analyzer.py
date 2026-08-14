"""sensors/screen_analyzer.py：屏幕截图画面分析（v2.5）。

当"快速通道"（窗口标题 + 进程名 + URL）判定不了时，截取当前窗口画面，
用本地视觉特征判断它更像"学习"还是"分心"。

隐私：截图只在内存中分析，不保存、不上传。

判定依据（保守启发式，避免误伤）：
- 白底 + 低饱和 -> 像文档/阅读（判 study，计专注）
- 高饱和 / 暗 + 色彩丰富 -> 像游戏/视频（判 distraction，只提醒不暴力关）
- 都不符合 -> unknown（不拦也不计专注）
"""
import os


def _window_rect(hwnd):
    """取窗口在屏幕上的矩形区域；失败返回 None（退回全屏）。"""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
            w = right - left
            h = bottom - top
            if w > 50 and h > 50 and w < 5000 and h < 5000:
                return (left, top, right, bottom)
    except Exception:
        pass
    return None


def capture_screen(hwnd=None):
    """截取前台窗口区域（或全屏），返回 PIL Image；失败返回 None。"""
    try:
        from PIL import ImageGrab
        if hwnd:
            bbox = _window_rect(hwnd)
            if bbox:
                return ImageGrab.grab(bbox=bbox)
        return ImageGrab.grab()
    except Exception:
        return None


def analyze_image(img):
    """分析截图，返回 {"category", "reasons", "stats"}。

    category: "study" / "distraction" / "unknown"
    """
    if img is None:
        return {"category": "unknown", "reasons": ["无法截取画面"], "stats": {}}
    try:
        import numpy as np
        small_rgb = img.convert("RGB").resize((160, 120))
        arr = np.asarray(small_rgb, dtype=np.float32)
        small_hsv = np.asarray(img.convert("HSV").resize((160, 120)), dtype=np.float32)
        small_gray = np.asarray(img.convert("L").resize((160, 120)), dtype=np.float32)

        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        brightness = float(arr.mean())
        saturation = float(small_hsv[:, :, 1].mean())
        whiteness = float(((r > 230) & (g > 230) & (b > 230)).mean())
        darkness = float(((r < 40) & (g < 40) & (b < 40)).mean())
        # 边缘密度：文本/细节多则高
        gx = float(np.abs(np.diff(small_gray, axis=1)).mean())
        gy = float(np.abs(np.diff(small_gray, axis=0)).mean())
        edge = gx + gy

        reasons = []
        category = "unknown"
        if whiteness > 0.45 and saturation < 45:
            category = "study"
            reasons.append("白底低饱和，像文档/阅读")
        elif saturation > 85 or (brightness < 70 and saturation > 55):
            category = "distraction"
            reasons.append("色彩饱和度高，像游戏/视频")

        stats = {
            "brightness": round(brightness, 1),
            "saturation": round(saturation, 1),
            "whiteness": round(whiteness, 2),
            "darkness": round(darkness, 2),
            "edge": round(edge, 1),
        }
        return {"category": category, "reasons": reasons, "stats": stats}
    except Exception as exc:
        return {"category": "unknown", "reasons": [f"分析失败: {exc}"], "stats": {}}


def analyze_foreground(hwnd=None):
    """一步到位：截图 + 分析，返回分析结果 dict。"""
    return analyze_image(capture_screen(hwnd))