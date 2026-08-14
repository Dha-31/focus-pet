"""tools/make_synthetic_data.py：生成合成训练数据（快速打底）。

用法：python tools/make_synthetic_data.py [每类数量，默认 80]
生成到 dataset/study/ 和 dataset/distraction/。

说明：合成数据只是"种子"，真实准确率要靠 tools/collect_dataset.py
采集你自己的真实屏幕数据来提升。
"""
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(PROJECT_ROOT, "dataset")
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"

STUDY_DOC_LINES = [
    "第一章 绪论", "1.1 研究背景与意义", "1.2 国内外研究现状",
    "机器学习是人工智能的核心方向。", "本章介绍课题的研究目的与内容安排。",
    "近年来深度学习在图像识别领域取得重大进展。", "参考文献 [1] 周志华. 机器学习.",
    "摘要 本文提出了一种新的方法。", "关键词 深度学习；图像识别；分类",
    "结论 实验结果表明该方法有效。", "第2章 相关工作", "2.1 监督学习概述",
]
STUDY_CODE_LINES = [
    "import numpy as np", "def train_model(x, y):", "    model = LinearRegression()",
    "    model.fit(x, y)", "    return model", "class DataLoader:",
    "    def __init__(self, path):", "        self.path = path",
    "for i in range(10):", "    print(f\"epoch {i}\")", "result = predict(test_x)",
    "if __name__ == \"__main__\":", "    main()",
]
STUDY_SLIDE_LINES = [
    "机器学习导论", "主讲：李老师", "目录", "一、什么是机器学习", "二、监督学习",
    "三、无监督学习", "四、总结与作业", "谢谢观看",
]
VIDEO_TEXTS = ["直播中", "弹幕 666", "关注 点赞 投币", "正在播放", "观看人数 12万",
               "推荐视频", "全屏", "倍速 1.5x"]
GAME_TEXTS = ["开始游戏", "攻略", "抽卡", "金币 +100", "段位 钻石", "排位赛",
              "装备强化", "背包", "设置", "匹配中"]
SOCIAL_TEXTS = ["热搜", "点赞 12万", "评论 3456", "分享", "明星八卦", "吃瓜",
                "搞笑视频", "关注", "转发", "话题 #今日份快乐"]


def _font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _save(img, folder, name):
    os.makedirs(os.path.join(DATASET, folder), exist_ok=True)
    img.save(os.path.join(DATASET, folder, name))


def make_document():
    w, h = 640, 480
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    y = 20
    for line in random.sample(STUDY_DOC_LINES, k=random.randint(6, len(STUDY_DOC_LINES))):
        d.text((30, y), line, fill="black", font=_font(random.randint(18, 24)))
        y += random.randint(34, 48)
    return img


def make_code():
    w, h = 640, 480
    img = Image.new("RGB", (w, h), (30, 30, 36))
    d = ImageDraw.Draw(img)
    colors = [(200, 200, 200), (120, 200, 120), (200, 160, 120), (120, 160, 220)]
    y = 16
    for line in random.sample(STUDY_CODE_LINES, k=random.randint(7, len(STUDY_CODE_LINES))):
        d.text((24, y), line, fill=random.choice(colors), font=_font(random.randint(16, 20)))
        y += random.randint(30, 38)
    return img


def make_slide():
    w, h = 640, 480
    img = Image.new("RGB", (w, h), (250, 250, 245))
    d = ImageDraw.Draw(img)
    d.text((40, 30), random.choice(STUDY_SLIDE_LINES), fill=(30, 30, 90), font=_font(30))
    y = 110
    for line in random.sample(STUDY_SLIDE_LINES[2:], k=random.randint(4, 6)):
        d.ellipse((52, y + 4, 60, y + 12), fill=(70, 110, 200))
        d.text((72, y), line, fill="black", font=_font(22))
        y += 42
    d.rectangle((40, h - 40, 200, h - 34), fill=(70, 110, 200))
    return img


def make_video():
    w, h = 640, 480
    img = Image.new("RGB", (w, h), (18, 18, 22))
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2
    bw, bh = random.randint(360, 480), random.randint(220, 300)
    d.rectangle((cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2),
                fill=tuple(random.randint(60, 180) for _ in range(3)))
    # 进度条
    d.rectangle((cx - bw // 2, h - 36, cx + bw // 2, h - 26), fill=(90, 90, 95))
    d.rectangle((cx - bw // 2, h - 36, cx - bw // 2 + random.randint(30, 200), h - 26),
                fill=(230, 60, 60))
    # 视频 UI 文字
    y = 16
    for line in random.sample(VIDEO_TEXTS, k=random.randint(3, 5)):
        d.text((24, y), line, fill=(235, 235, 235), font=_font(random.randint(18, 26)))
        y += 34
    return img


def make_game():
    """更接近真实游戏画面：深色场景 + 彩色色块 + HUD 面板 + 技能栏。"""
    w, h = 640, 480
    img = Image.new("RGB", (w, h), (22, 26, 42))  # 深色游戏背景
    d = ImageDraw.Draw(img)
    # 场景色块（彩色但不过曝）
    for _ in range(14):
        x0 = random.randint(0, w - 130)
        y0 = random.randint(40, h - 130)
        x1 = x0 + random.randint(60, 170)
        y1 = y0 + random.randint(40, 120)
        d.rectangle((x0, y0, x1, y1), fill=tuple(random.randint(70, 220) for _ in range(3)))
    # 左上 HUD 面板 + 游戏文字
    d.rectangle((14, 14, 230, 120), fill=(34, 34, 46))
    y = 26
    for line in random.sample(GAME_TEXTS, k=random.randint(4, 6)):
        d.text((26, y), line, fill=(235, 235, 235), font=_font(random.randint(20, 26)))
        y += 30
    # 底部技能栏
    for i in range(6):
        d.rectangle((w // 2 - 160 + i * 52, h - 74, w // 2 - 118 + i * 52, h - 32),
                    outline=(255, 255, 255), width=2)
    # 准星
    cx, cy = w // 2, h // 2
    d.line((cx - 12, cy, cx + 12, cy), fill=(255, 255, 255), width=2)
    d.line((cx, cy - 12, cx, cy + 12), fill=(255, 255, 255), width=2)
    return img


def make_social():
    w, h = 640, 480
    img = Image.new("RGB", (w, h), (240, 240, 245))
    d = ImageDraw.Draw(img)
    y = 14
    for line in random.sample(SOCIAL_TEXTS, k=random.randint(4, 6)):
        d.rounded_rectangle((20, y, w - 20, y + 74), radius=12,
                            fill=tuple(random.randint(200, 255) for _ in range(3)))
        d.text((34, y + 10), line, fill=(40, 40, 40), font=_font(random.randint(20, 26)))
        y += 92
    return img


MAKERS = {
    "study": [make_document, make_code, make_slide],
    "distraction": [make_video, make_game, make_social],
}


def main():
    per_class = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    random.seed(2026)
    counts = {"study": 0, "distraction": 0}
    for label, makers in MAKERS.items():
        for i in range(per_class):
            maker = random.choice(makers)
            _save(maker(), label, f"syn_{i:03d}.png")
            counts[label] += 1
    print(f"合成数据生成完成: {counts}")


if __name__ == "__main__":
    main()