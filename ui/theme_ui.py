"""ui/theme_ui.py：轻量 UI 统一风格（v3.5）。

- 统一配色/字体常量
- style_window()：窗口底色
- add_header()：顶部标题条
- accent_button()：粉色系现代按钮（无边框、圆润）

只做"轻量统一样式"，不引入任何依赖。
"""
import tkinter as tk

ACCENT = "#ff8fab"
ACCENT_DARK = "#e06f8f"
ACCENT_LIGHT = "#ffe3ec"
BG = "#fdf6f0"
CARD = "#ffffff"
TEXT = "#333333"
MUTED = "#888888"
BORDER = "#f0e0d8"

FONT = ("Microsoft YaHei UI", 10)
# 辅助窗口统一初始尺寸（接近正方形，可自由拉大）
AUX_SIZE = (760, 680)
FONT_SMALL = ("Microsoft YaHei UI", 9)
FONT_BOLD = ("Microsoft YaHei UI", 10, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 13, "bold")


def style_window(win, title=None, bg=BG):
    win.configure(bg=bg)
    if title:
        win.title(title)


def add_header(parent, text, sub=None, bg=BG, fg=ACCENT):
    """顶部标题条：返回一个 Frame，调用方 pack 即可。"""
    bar = tk.Frame(parent, bg=bg)
    tk.Label(bar, text=text, bg=bg, fg=fg, font=FONT_TITLE).pack(anchor="w")
    if sub:
        tk.Label(bar, text=sub, bg=bg, fg=MUTED, font=FONT_SMALL).pack(anchor="w")
    return bar


def accent_button(parent, text, command, width=None, padx=12, pady=5):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=ACCENT, fg="white",
        activebackground=ACCENT_DARK, activeforeground="white",
        relief="flat", bd=0, padx=padx, pady=pady, cursor="hand2",
        font=FONT)
    if width:
        btn.configure(width=width)
    return btn


def card(parent, bg=CARD, **kwargs):
    """卡片容器（浅色圆角感：用高亮色块）。"""
    frame = tk.Frame(parent, bg=bg, highlightbackground=BORDER,
                     highlightthickness=1, **kwargs)
    return frame
