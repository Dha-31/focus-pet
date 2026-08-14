"""tools/clean_dataset.py：清理数据集中的误标/模棱两可样本。

根据 OCR 内容把明显有问题的样本移到 dataset/_rejected/（不删除，可复查）：
- "分心"里出现终端 / Office / 纯学习内容 -> 拒收（标错了）
- 学习词与分心词同时命中（多标签页混合截图）-> 拒收（标签污染）
- "学习"里 OCR 读不到内容 -> 拒收（可能是空白图）

用法：python tools/clean_dataset.py
"""
import glob
import os
import shutil
import sys

import numpy as np
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from rapidocr_onnxruntime import RapidOCR  # noqa: E402

REJECT_DIR = os.path.join(PROJECT_ROOT, "dataset", "_rejected")

TERMINAL_MARKS = [
    "powershell", "ps c:", "copyright (c) microsoft", "cmd.exe",
    "command prompt", "windows terminal",
]
OFFICE_MARKS = [
    "officeplus", "microsoft word", "word 文档", "正文 字体", "段落",
    "引用 邮件 审阅", "文件 编辑 视图", "自动保存", "outage", "defective",
]
STUDY_HINTS = [
    "目录", "摘要", "讲义", "课件", "笔记", "作业", "课程", "考试", "复习",
    "参考文献", "第一章", "代码", "编程", "算法", "单词", "词汇", "阅读",
    "import", "def ", "class ", "function", "numpy", "print", "pdf",
    "lecture", "tutorial", "homework", "exam", "study", "chapter", "math",
]
DISTR_HINTS = [
    "直播", "视频", "播放", "弹幕", "点赞", "投币", "关注", "订阅", "评论",
    "游戏", "攻略", "抽卡", "购物车", "下单", "秒杀", "热搜", "bilibili",
    "哔哩哔哩", "flor.io", "play", "watch", "live", "stream", "game",
    "score", "video",
]


def _ocr_text(img):
    w, h = img.size
    if w > 960:
        img = img.resize((960, int(h * 960 / w)))
    out, _ = RapidOCR()(np.asarray(img.convert("RGB")))
    if not out:
        return "", 0, 0
    texts = [str(x[1]) for x in out]
    joined = " ".join(texts)
    low = joined.lower()
    sh = sum(1 for k in STUDY_HINTS if k in low)
    dh = sum(1 for k in DISTR_HINTS if k in low)
    return joined, sh, dh


def main():
    os.makedirs(REJECT_DIR, exist_ok=True)
    rejected = []
    kept = {"study": 0, "distraction": 0}

    for label in ("study", "distraction"):
        for path in sorted(glob.glob(os.path.join(PROJECT_ROOT, "dataset", label, "real_*.png"))):
            name = os.path.basename(path)
            try:
                text, sh, dh = _ocr_text(Image.open(path))
            except Exception as exc:
                print(f"  [出错] {name}: {exc}")
                continue
            low = text.lower()
            reason = None

            # 严格规则：任何模棱两可（学习/分心词同时出现、含终端、OCR 无内容）都拒收
            if any(m in low for m in TERMINAL_MARKS):
                reason = "含终端窗口"
            elif not text.strip():
                reason = "OCR 无内容（可能空白图）"
            elif sh > 0 and dh > 0:
                reason = "学习/分心词混合（多标签页）"
            elif label == "distraction" and sh > 0:
                reason = "出现学习词（可能标错）"
            elif label == "study" and dh > 0:
                reason = "出现分心词（可能标错）"

            if reason:
                dest = os.path.join(REJECT_DIR, f"{label}__{name}")
                shutil.move(path, dest)
                rejected.append((label, name, reason))
                print(f"  [拒收] {label}/{name} -> {reason} | 文字: {text[:40]!r}")
            else:
                kept[label] += 1

    print(f"\n清理完成：拒收 {len(rejected)} 张，保留 study={kept['study']} distraction={kept['distraction']}")
    print(f"拒收的样本在 dataset/_rejected/ 可复查；确认无误后可直接删除该文件夹")


if __name__ == "__main__":
    main()