"""sensors/screen_analyzer.py：屏幕截图画面分析（v2.5 增强版）。

多信号融合：
1. OCR 文字识别（RapidOCR，离线中文）——直接读画面文字，命中"学习词"或"分心词"
2. 图案/结构分析——视频播放器特征（暗背景+中央亮区+底部进度条）、文档排版（文字行多+白底）
3. 颜色/亮度统计
4. 可选：加载训练好的分类器 models/screen_classifier.pkl（tools/train_classifier.py 训练）

决策是保守的：信号不足时返回 unknown（不拦也不计专注），避免误伤。

隐私：截图只在内存中处理，不保存、不上传。
"""
import os
import re
import threading

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
CLASSIFIER_PATH = os.path.join(MODELS_DIR, "screen_classifier.pkl")

STUDY_KEYWORDS = [
    "目录", "摘要", "参考文献", "关键词", "讲义", "课件", "笔记", "作业", "试卷",
    "课本", "教程", "练习题", "第一章", "第二章", "第1章", "第2章", "引言", "绪论",
    "课程", "考试", "复习", "知识点", "公式", "定理", "证明", "实验报告",
    "pdf", "lecture", "course", "tutorial", "homework", "exam", "study",
    "notes", "chapter", "abstract", "references", "introduction", "conclusion",
    "import ", "def ", "class ", "function", "return", "numpy", "pandas",
    "torch", "print", "代码", "编程", "算法", "程序", "数据结构",
    "阅读", "训练", "单词", "词汇", "答案", "六级", "四级", "真题", "语法",
]
DISTRACTION_KEYWORDS = [
    "直播", "视频", "播放", "弹幕", "点赞", "投币", "收藏", "关注", "订阅", "评论",
    "观看", "追番", "电竞", "游戏", "攻略", "抽卡", "氪金", "开箱", "赛季", "段位",
    "排位", "匹配", "副本", "装备", "开始游戏", "购物车", "下单", "包邮", "秒杀",
    "优惠券", "热搜", "八卦", "明星", "吃瓜", "搞笑", "段子",
    "play", "watch", "live", "stream", "subscribe", "game", "score",
    "video", "entertainment", "cart", "checkout", "discount",
    "血量", "金币", "钻石", "战力", "皮肤", "英雄", "排行榜", "大厅",
    "热门", "番剧", "剧集", "追剧", "首页推荐",
]
CODE_PATTERN = re.compile(
    r"\b(def|class|import|function|return|int|void|public|private|const|var|let|"
    r"if|else|for|while|printf|print|console\.log|lambda|self)\b",
    re.IGNORECASE,
)

_classifier = None
_classifier_loaded = False
_tls = threading.local()


# ---------- OCR ----------
def _get_ocr():
    """线程本地 OCR 引擎：训练时多线程并行提取特征不互卡。"""
    engine = getattr(_tls, "engine", None)
    if engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR()
            _tls.engine = engine
        except Exception:
            engine = False
            _tls.engine = False
    return engine or None


def ocr_analyze(img):
    """对截图做 OCR，返回 {text, lines, coverage, study_hits, distraction_hits, has_code}。"""
    result = {
        "text": "", "lines": 0, "coverage": 0.0,
        "study_hits": 0, "distraction_hits": 0, "has_code": False,
    }
    engine = _get_ocr()
    if engine is None:
        return result
    try:
        import numpy as np
        # 压到合理尺寸加速 OCR
        w, h = img.size
        max_w = 1280
        if w > max_w:
            img = img.resize((max_w, int(h * max_w / w)))
        arr = np.asarray(img.convert("RGB"))
        ocr_out, _ = engine(arr)
        if not ocr_out:
            return result
        texts = [str(item[1]) for item in ocr_out]
        joined = " ".join(texts)
        result["text"] = joined[:500]
        result["lines"] = len(texts)

        # 文字覆盖度（文本框面积 / 画面面积）
        try:
            area = float(arr.shape[0] * arr.shape[1])
            box_area = 0.0
            for item in ocr_out:
                box = item[0]
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                bw = max(xs) - min(xs)
                bh = max(ys) - min(ys)
                box_area += max(0, bw) * max(0, bh)
            result["coverage"] = round(min(1.0, box_area / area), 4)
        except Exception:
            pass

        low = joined.lower()
        result["study_hits"] = sum(1 for k in STUDY_KEYWORDS if k.lower() in low)
        result["distraction_hits"] = sum(1 for k in DISTRACTION_KEYWORDS if k.lower() in low)
        result["has_code"] = bool(CODE_PATTERN.search(joined))
    except Exception:
        pass
    return result


# ---------- 视觉统计 ----------
def visual_stats(img):
    try:
        import numpy as np
        small = img.convert("RGB").resize((160, 120))
        arr = np.asarray(small, dtype=np.float32)
        hsv = np.asarray(img.convert("HSV").resize((160, 120)), dtype=np.float32)
        gray = np.asarray(img.convert("L").resize((160, 120)), dtype=np.float32)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        stats = {
            "brightness": round(float(arr.mean()), 1),
            "saturation": round(float(hsv[:, :, 1].mean()), 1),
            "whiteness": round(float(((r > 230) & (g > 230) & (b > 230)).mean()), 4),
            "darkness": round(float(((r < 40) & (g < 40) & (b < 40)).mean()), 4),
            "edge": round(float(np.abs(np.diff(gray, axis=1)).mean()
                              + np.abs(np.diff(gray, axis=0)).mean()), 1),
        }
        return stats
    except Exception:
        return {"brightness": 0, "saturation": 0, "whiteness": 0, "darkness": 0, "edge": 0}


# ---------- 视频播放器图案特征 ----------
def video_pattern(img):
    """暗背景 + 中央亮区 + 底部细条（进度条）→ 疑似视频播放器。"""
    try:
        import numpy as np
        arr = np.asarray(img.convert("L").resize((160, 120)), dtype=np.float32)
        h, w = arr.shape
        overall = float(arr.mean())
        if overall > 120:  # 亮画面不太可能是视频播放器（背景应偏暗）
            return False
        center = float(arr[h // 4:3 * h // 4, w // 4:3 * w // 4].mean())
        bottom = arr[int(h * 0.92):h, :]
        bright_bottom = float((bottom > 100).mean())
        return center > overall + 12 and bright_bottom > 0.25
    except Exception:
        return False


def code_editor_pattern(img):
    """深色编辑器（VS Code 深色主题等）：暗背景 + 低饱和 + 高边缘密度。"""
    try:
        import numpy as np
        arr = np.asarray(img.convert("RGB").resize((160, 120)), dtype=np.float32)
        hsv = np.asarray(img.convert("HSV").resize((160, 120)), dtype=np.float32)
        gray = np.asarray(img.convert("L").resize((160, 120)), dtype=np.float32)
        brightness = float(arr.mean())
        saturation = float(hsv[:, :, 1].mean())
        edge = float(np.abs(np.diff(gray, axis=1)).mean()
                     + np.abs(np.diff(gray, axis=0)).mean())
        return brightness < 75 and saturation < 45 and edge > 6
    except Exception:
        return False

# ---------- 特征向量（训练与运行时共用） ----------
def make_feature_vector(stats, ocr, vp):
    return [
        stats["brightness"], stats["saturation"], stats["whiteness"],
        stats["darkness"], stats["edge"],
        float(ocr["study_hits"]), float(ocr["distraction_hits"]),
        float(min(ocr["lines"], 50)) / 50.0, ocr["coverage"],
        float(vp), float(ocr["has_code"]),
    ]


def _get_classifier():
    global _classifier, _classifier_loaded
    if not _classifier_loaded:
        _classifier_loaded = True
        if os.path.exists(CLASSIFIER_PATH):
            try:
                import joblib
                _classifier = joblib.load(CLASSIFIER_PATH)
            except Exception:
                _classifier = None
    return _classifier


# ---------- 入口 ----------
def analyze_image(img):
    """分析截图，返回 {"category", "confidence", "reasons", "stats", "ocr_summary", "ml"}。"""
    if img is None:
        return {"category": "unknown", "confidence": 0.0,
                "reasons": ["无法截取画面"], "stats": {}, "ocr_summary": {}, "ml": None}
    stats = visual_stats(img)
    ocr = ocr_analyze(img)
    vp = video_pattern(img)
    feats = make_feature_vector(stats, ocr, vp)

    ml = None
    clf = _get_classifier()
    if clf is not None:
        try:
            proba = clf.predict_proba([feats])[0]
            ml = {"distraction": round(float(proba[0]), 3), "study": round(float(proba[1]), 3)}
        except Exception:
            ml = None

    study_score = 0.0
    dist_score = 0.0
    reasons = []

    # OCR 文字信号
    if ocr["study_hits"] >= 2:
        study_score += 0.7
    elif ocr["study_hits"] == 1:
        study_score += 0.35
    if ocr["distraction_hits"] >= 2:
        dist_score += 0.7
    elif ocr["distraction_hits"] == 1:
        dist_score += 0.35
    if ocr["has_code"]:
        study_score += 0.6
    if code_editor_pattern(img):
        study_score += 0.5
        reasons.append("像代码编辑器")
    if ocr["study_hits"] > 0 and ocr["distraction_hits"] == 0 and ocr["lines"] >= 6:
        study_score += 0.3
    if ocr["distraction_hits"] > 0 and ocr["study_hits"] == 0:
        dist_score += 0.2

    # 图案/结构信号
    if vp:
        dist_score += 0.6
        reasons.append("像视频播放器")
    if ocr["lines"] >= 8 and stats["whiteness"] > 0.25:
        study_score += 0.4
        reasons.append("文字多+白底，像文档")
    if stats["saturation"] > 85 and stats["darkness"] < 0.25:
        dist_score += 0.4
        reasons.append("高饱和彩色")

    # 机器学习信号
    if ml:
        study_score += ml["study"] * 0.8
        dist_score += ml["distraction"] * 0.8

    category = "unknown"
    confidence = 0.0
    if study_score >= 0.6 and study_score > dist_score:
        category = "study"
        confidence = study_score / (study_score + dist_score)
        reasons.append("倾向学习")
    elif dist_score >= 0.6 and dist_score > study_score:
        category = "distraction"
        confidence = dist_score / (study_score + dist_score)
        reasons.append("倾向分心")
    else:
        # 启发式不够强时，让 ML 做裁决（阈值 0.75，避免误伤）
        if ml and ml["distraction"] >= 0.75 and ml["distraction"] > ml["study"]:
            category = "distraction"
            confidence = ml["distraction"]
            reasons.append("模型判定倾向分心")
        elif ml and ml["study"] >= 0.75 and ml["study"] > ml["distraction"]:
            category = "study"
            confidence = ml["study"]
            reasons.append("模型判定倾向学习")

    return {
        "category": category,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "stats": stats,
        "ocr_summary": {
            "lines": ocr["lines"], "coverage": ocr["coverage"],
            "study_hits": ocr["study_hits"], "distraction_hits": ocr["distraction_hits"],
            "has_code": ocr["has_code"],
        },
        "ml": ml,
    }


# ---------- 截图 ----------
def _window_rect(hwnd):
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
    try:
        from PIL import ImageGrab
        if hwnd:
            bbox = _window_rect(hwnd)
            if bbox:
                return ImageGrab.grab(bbox=bbox)
        return ImageGrab.grab()
    except Exception:
        return None


def analyze_foreground(hwnd=None):
    return analyze_image(capture_screen(hwnd))