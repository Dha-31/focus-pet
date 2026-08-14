"""ui/pet_renderer.py：共享宠物绘制（桌宠窗口与个人空间共用）。

- draw_procedural_pet：程序化小猫（表情/等级/装饰品）
- draw_accessory：在"头部框架"（中心+半径）上画装饰品 —— 程序化形象和
  自定义图片形象都能用（图片形象的人脸由 pet.json 元数据提供）
- draw_expression_overlay：给自定义图片形象叠加表情标记（生气眉/腮红/汗滴），
  不修改照片本身（要真的改变照片表情需要 Live2D 骨骼绑定，属远期）
"""
import math

BODY_NORMAL = "#ffe0b3"
BODY_ANGRY = "#f7b9b9"
OUTLINE_NORMAL = "#e8a95b"
OUTLINE_ANGRY = "#d9534f"
OUTLINE_GOLD = "#d4a017"
BLUSH = "#ffb3b3"


def draw_procedural_pet(c, cx, cy, shake, mood, level, accessory=None,
                        t=0.0, show_level=True, blink_period=3.0):
    """画一只会变表情的程序化小猫。"""
    s = 1.0 + min(0.4, (level - 1) * 0.08)
    angry = mood >= 3
    body = BODY_ANGRY if angry else BODY_NORMAL
    outline = OUTLINE_ANGRY if angry else OUTLINE_NORMAL
    if level >= 6:
        outline = OUTLINE_GOLD

    # 耳朵
    ear_l = [(cx - 30 * s + shake, cy - 34 * s),
             (cx - 18 * s + shake, cy - 52 * s),
             (cx - 6 * s + shake, cy - 32 * s)]
    ear_r = [(cx + 6 * s + shake, cy - 32 * s),
             (cx + 18 * s + shake, cy - 52 * s),
             (cx + 30 * s + shake, cy - 34 * s)]
    c.create_polygon(ear_l, fill=body, outline=outline, width=2)
    c.create_polygon(ear_r, fill=body, outline=outline, width=2)

    # 身体
    c.create_oval(cx - 40 * s + shake, cy - 40 * s, cx + 40 * s + shake, cy + 40 * s,
                  fill=body, outline=outline, width=3)

    # 腮红
    if mood >= 1:
        blush = "#ff8080" if mood >= 3 else BLUSH
        c.create_oval(cx - 34 * s + shake, cy + 6 * s, cx - 22 * s + shake, cy + 16 * s,
                      fill=blush, outline="")
        c.create_oval(cx + 22 * s + shake, cy + 6 * s, cx + 34 * s + shake, cy + 16 * s,
                      fill=blush, outline="")

    # 眼睛（眨眼）
    blinking = (t % blink_period) < 0.18
    eye_y = cy - 10 * s
    if blinking:
        c.create_line(cx - 16 * s + shake, eye_y, cx - 8 * s + shake, eye_y, fill="#4a3728", width=2)
        c.create_line(cx + 8 * s + shake, eye_y, cx + 16 * s + shake, eye_y, fill="#4a3728", width=2)
    else:
        c.create_oval(cx - 17 * s + shake, eye_y - 6 * s, cx - 7 * s + shake, eye_y + 6 * s,
                      fill="#4a3728", outline="")
        c.create_oval(cx + 7 * s + shake, eye_y - 6 * s, cx + 17 * s + shake, eye_y + 6 * s,
                      fill="#4a3728", outline="")

    # 眉毛（不耐烦/生气）
    if mood >= 2:
        c.create_line(cx - 18 * s + shake, eye_y - 12 * s, cx - 6 * s + shake, eye_y - 8 * s,
                      fill="#4a3728", width=2)
        c.create_line(cx + 6 * s + shake, eye_y - 8 * s, cx + 18 * s + shake, eye_y - 12 * s,
                      fill="#4a3728", width=2)

    # 嘴
    mouth_y = cy + 10 * s
    if mood == 0:      # 开心：微笑
        c.create_arc(cx - 12 * s + shake, mouth_y - 8 * s, cx + 12 * s + shake, mouth_y + 12 * s,
                     start=180, extent=180, style="arc", outline="#4a3728", width=2)
    elif mood == 1:    # 好奇：小 O
        c.create_oval(cx - 3 * s + shake, mouth_y - 3 * s, cx + 3 * s + shake, mouth_y + 3 * s,
                      fill="#4a3728", outline="")
    elif mood == 2:    # 不耐烦：直线
        c.create_line(cx - 8 * s + shake, mouth_y, cx + 8 * s + shake, mouth_y,
                      fill="#4a3728", width=2)
    else:              # 生气/暴怒：倒弧 + 咬牙
        c.create_arc(cx - 12 * s + shake, mouth_y - 4 * s, cx + 12 * s + shake, mouth_y + 12 * s,
                     start=0, extent=180, style="arc", outline="#4a3728", width=2)
        if mood >= 4:
            for dx in (-5 * s, 0, 5 * s):
                c.create_line(cx + dx + shake, mouth_y + 4 * s, cx + dx + shake, mouth_y + 9 * s,
                              fill="#4a3728", width=1)

    # 等级皇冠（Lv>=4）
    if level >= 4:
        top = cy - 52 * s
        pts = [(cx - 14 * s + shake, top), (cx - 9 * s + shake, top - 14 * s),
               (cx - 4 * s + shake, top - 6 * s), (cx + 4 * s + shake, top - 6 * s),
               (cx + 9 * s + shake, top - 14 * s), (cx + 14 * s + shake, top),
               (cx - 14 * s + shake, top)]
        c.create_polygon(pts, fill="#ffd700", outline="#c9a400", width=1)

    # 等级角标
    if show_level:
        c.create_text(cx + shake, cy + 40 * s + 14, text=f"Lv.{level}",
                      fill="#777777", font=("Microsoft YaHei UI", 8))

    # 装饰品（戴在头上）
    if accessory:
        hr = 24 * s
        draw_accessory(c, cx + shake, cy - 10 * s, hr, accessory)


def draw_accessory(c, hx, hy, hr, kind):
    """在"头部框架"（hx,hy 中心 + hr 半径）上画装饰品。"""
    if kind == "hat":      # 小红帽
        c.create_rectangle(hx - hr * 1.2, hy - hr * 1.15, hx + hr * 1.2, hy - hr * 0.9,
                           fill="#e05050", outline="#b03030")
        c.create_arc(hx - hr * 0.9, hy - hr * 2.0, hx + hr * 0.9, hy - hr * 0.6,
                     start=180, extent=180, fill="#e05050", outline="#b03030")
    elif kind == "bow":    # 蝴蝶结（耳朵旁）
        c.create_polygon(hx - hr * 1.15, hy - hr * 1.4, hx - hr * 0.35, hy - hr * 1.15,
                         hx - hr * 1.15, hy - hr * 0.9, fill="#ff9ec7", outline="#e0709a")
        c.create_polygon(hx + hr * 1.15, hy - hr * 1.4, hx + hr * 0.35, hy - hr * 1.15,
                         hx + hr * 1.15, hy - hr * 0.9, fill="#ff9ec7", outline="#e0709a")
        c.create_oval(hx - hr * 0.28, hy - hr * 1.28, hx + hr * 0.28, hy - hr * 1.02,
                      fill="#e0709a", outline="")
    elif kind == "glasses":  # 眼镜
        c.create_oval(hx - hr * 0.95, hy - hr * 0.55, hx - hr * 0.1, hy + hr * 0.25,
                      outline="#444444", width=2)
        c.create_oval(hx + hr * 0.1, hy - hr * 0.55, hx + hr * 0.95, hy + hr * 0.25,
                      outline="#444444", width=2)
        c.create_line(hx - hr * 0.1, hy - hr * 0.15, hx + hr * 0.1, hy - hr * 0.15,
                      fill="#444444", width=2)
        c.create_line(hx - hr * 0.95, hy - hr * 0.15, hx - hr * 1.25, hy - hr * 0.3,
                      fill="#444444", width=2)
        c.create_line(hx + hr * 0.95, hy - hr * 0.15, hx + hr * 1.25, hy - hr * 0.3,
                      fill="#444444", width=2)
    elif kind == "scarf":  # 围巾
        c.create_rectangle(hx - hr * 0.95, hy + hr * 0.55, hx + hr * 0.95, hy + hr * 1.15,
                           fill="#5aa0e0", outline="#3a70a8")
        c.create_rectangle(hx - hr * 0.95, hy + hr * 0.55, hx - hr * 0.45, hy + hr * 1.5,
                           fill="#5aa0e0", outline="#3a70a8")
    elif kind == "flower":  # 小花
        for dx, dy in ((1, 0), (0.3, 0.95), (-0.8, 0.6), (-0.8, -0.6), (0.3, -0.95)):
            px = hx + dx * hr * 0.5
            py = hy - hr * 1.5 + dy * hr * 0.5
            c.create_oval(px - hr * 0.25, py - hr * 0.25, px + hr * 0.25, py + hr * 0.25,
                          fill="#ffd166", outline="#e0a020")
        c.create_oval(hx - hr * 0.18, hy - hr * 1.5 - hr * 0.18, hx + hr * 0.18,
                      hy - hr * 1.5 + hr * 0.18, fill="#e0709a", outline="")
    elif kind == "crown":  # 金皇冠
        pts = [(hx - hr * 0.9, hy - hr * 1.3), (hx - hr * 0.55, hy - hr * 2.0),
               (hx - hr * 0.25, hy - hr * 1.5), (hx + hr * 0.25, hy - hr * 1.5),
               (hx + hr * 0.55, hy - hr * 2.0), (hx + hr * 0.9, hy - hr * 1.3),
               (hx - hr * 0.9, hy - hr * 1.3)]
        c.create_polygon(pts, fill="#ffd700", outline="#c9a400", width=1)


def draw_expression_overlay(c, hx, hy, hr, mood):
    """给自定义图片形象叠加表情标记（不修改照片本身）。"""
    width = max(2, int(hr * 0.08))
    if mood >= 2:  # 生气眉毛
        c.create_line(hx - hr * 0.8, hy - hr * 0.7, hx - hr * 0.15, hy - hr * 0.45,
                      fill="#4a3728", width=width)
        c.create_line(hx + hr * 0.15, hy - hr * 0.45, hx + hr * 0.8, hy - hr * 0.7,
                      fill="#4a3728", width=width)
    if mood >= 1:  # 腮红
        blush = "#ff8080" if mood >= 3 else BLUSH
        c.create_oval(hx - hr * 1.0, hy + hr * 0.3, hx - hr * 0.5, hy + hr * 0.7,
                      fill=blush, outline="")
        c.create_oval(hx + hr * 0.5, hy + hr * 0.3, hx + hr * 1.0, hy + hr * 0.7,
                      fill=blush, outline="")
    if mood >= 3:  # 生气符号
        c.create_line(hx - hr * 1.2, hy - hr * 0.35, hx - hr * 0.9, hy - hr * 0.1,
                      fill="#e05050", width=width)
        c.create_line(hx + hr * 0.9, hy - hr * 0.35, hx + hr * 1.2, hy - hr * 0.1,
                      fill="#e05050", width=width)