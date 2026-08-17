"""ui/pet_renderer.py：共享宠物绘制（桌宠窗口与个人空间共用）。

- draw_procedural_pet：程序化小猫（表情/等级/装饰品）
- draw_expression_overlay：给自定义图片形象叠加表情标记（生气眉/腮红/汗滴），
  不修改照片本身（要真的改变照片表情需要 Live2D 骨骼绑定，属远期）
"""
import math

def fit_photo(img, tw, th):
    """把 PhotoImage 缩放到目标区域（保持比例，居中不裁切）。

    Tk 的 PhotoImage 只能整数倍 subsample（缩小）/ zoom（放大），
    这里用"整数倍 + 微调"近似任意缩放。
    """
    if img is None:
        return None
    try:
        iw, ih = img.width(), img.height()
        if iw <= 0 or ih <= 0:
            return img
        scale = min(tw / iw, th / ih)
        if 0.99 <= scale <= 1.01:
            return img
        if scale < 1.0:
            factor = max(1, int(1.0 / scale))
            return img.subsample(factor, factor)
        # 放大：先整数倍 zoom，再 subsample 微调
        zoom = max(1, int(scale))
        fine = scale / zoom
        out = img.zoom(zoom, zoom)
        if fine < 0.98:
            factor = max(1, int(1.0 / fine))
            out = out.subsample(factor, factor)
        return out
    except Exception:
        return img


BODY_NORMAL = "#ffe0b3"
BODY_ANGRY = "#f7b9b9"
OUTLINE_NORMAL = "#e8a95b"
OUTLINE_ANGRY = "#d9534f"
OUTLINE_GOLD = "#d4a017"
BLUSH = "#ffb3b3"


def draw_procedural_pet(c, cx, cy, shake, mood, level,
                        t=0.0, show_level=True, blink_period=3.0, look=None,
                        view_scale=1.0, napping=False):
    """画一只会变表情的程序化小猫。"""
    s = view_scale * (1.0 + min(0.4, (level - 1) * 0.08))
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

    # 眼睛（眨眼 + 跟随"你在看我吗"）
    blinking = (t % blink_period) < 0.18 or napping
    eye_y = cy - 10 * s
    if blinking:
        c.create_line(cx - 16 * s + shake, eye_y, cx - 8 * s + shake, eye_y, fill="#4a3728", width=2)
        c.create_line(cx + 8 * s + shake, eye_y, cx + 16 * s + shake, eye_y, fill="#4a3728", width=2)
    elif look is not None:
        # 白色眼球 + 瞳孔朝鼠标方向移动
        for ex in (-12 * s, 12 * s):
            c.create_oval(cx + ex - 8 * s + shake, eye_y - 8 * s,
                          cx + ex + 8 * s + shake, eye_y + 8 * s,
                          fill="white", outline="#4a3728")
            px = cx + ex + look[0] * 4 * s + shake
            py = eye_y + look[1] * 3 * s
            c.create_oval(px - 3.5 * s, py - 3.5 * s, px + 3.5 * s, py + 3.5 * s,
                          fill="#4a3728", outline="")
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
# ---------- v3.5：状态特效（庆祝/错误/睡眠/阴影） ----------


def draw_shadow(c, cx, cy, r):
    """宠物脚下柔和的影子，让悬浮感更自然。"""
    for i in range(4, 0, -1):
        alpha = "#e8e8e8" if i == 1 else f"#{200 - i * 20:02x}{200 - i * 20:02x}{200 - i * 20:02x}"
        c.create_oval(cx - r * (0.6 + i * 0.08), cy + r * (0.75 + i * 0.04),
                      cx + r * (0.6 + i * 0.08), cy + r * (0.9 + i * 0.04),
                      fill=alpha, outline="")


def draw_celebrate_effects(c, cx, cy, t, r=40.0):
    """完成/成就庆祝：彩带 + 星光（随时间旋转飘散）。"""
    import math
    n = 10
    for i in range(n):
        a = t * 2.2 + i * (math.pi * 2 / n)
        dist = r * (1.0 + 0.25 * math.sin(t * 3 + i))
        x = cx + math.cos(a) * dist
        y = cy - r * 0.4 + math.sin(a) * dist * 0.6
        colors = ["#ffd166", "#ff6b6b", "#6bc9ff", "#95e06c", "#ff9ec7"]
        size = 3 + (i % 3)
        c.create_oval(x - size, y - size, x + size, y + size, fill=colors[i % 5], outline="")
        # 小星星
        if i % 3 == 0:
            c.create_text(x + 8, y - 6, text="✦", fill="#ffd166",
                          font=("Microsoft YaHei UI", 9))


def draw_error_effects(c, cx, cy, t, r=40.0):
    """出错反馈：红色感叹号 + 抖动汗滴。"""
    import math
    shake = math.sin(t * 30) * 2
    x = cx + shake
    # 感叹号
    c.create_rectangle(x - 4, cy - r * 0.9 - 14, x + 4, cy - r * 0.9 - 2,
                       fill="#e05050", outline="")
    c.create_oval(x - 4, cy - r * 0.9 + 2, x + 4, cy - r * 0.9 + 10,
                  fill="#e05050", outline="")
    # 汗滴
    c.create_oval(cx - r * 0.9, cy - r * 0.7, cx - r * 0.9 + 7, cy - r * 0.7 + 10,
                  fill="#6bc9ff", outline="")


def draw_sleep_effects(c, cx, cy, t, r=40.0):
    """睡觉：飘浮的 z Z Z。"""
    base = t % 3.0
    for i, ch in enumerate(("z", "Z", "Z")):
        phase = (base - i * 0.8) % 3.0
        if phase > 2.2:
            continue
        y = cy - r * 1.1 - i * 14 - phase * 8
        x = cx + r * 0.75 + i * 7
        c.create_text(x, y, text=ch, fill="#7a9bd4",
                      font=("Microsoft YaHei UI", 10 + i * 2))
