"""ui/help_window.py：使用帮助中心（v3.7）。

- 数据全部来自 core/help_data.py（数据驱动，随版本自动更新，不会过期）
- 分页：功能一览 / 快捷键 / 设置项 / 常见问题 / 关于
- 功能条目带"本版新增"标签（按 added_in == VERSION 高亮）
- welcome=True 时显示"首次启动欢迎"横幅 + "下次不再显示"勾选

打开方式：右键桌宠 →「使用帮助…」；首次启动自动弹出。
"""
import json
import os
import tkinter as tk
from tkinter import ttk

from core import help_data
from core.config import CONFIG_PATH
from ui.theme_ui import (ACCENT, ACCENT_LIGHT, BG, CARD, MUTED, TEXT,
                         accent_button, add_header, style_window)

FAQ = [
    ("摄像头没画面 / 检测不到人？",
     "① 设置 → 摄像头开关打开；② 运行 python main.py --camera-setup 选一台能看到自己脸的设备；"
     "③ 确认已装 opencv-python mediapipe 并运行 python tools/fetch_models.py 下载模型。"
     "画面只在本地处理，不上传。"),
    ("浏览器扩展显示「未连接」？",
     "① 确认 Focus Pet 正在运行；② 设置 → 浏览器扩展桥接 = 开（默认端口 18765）；"
     "③ 改完重启桌宠；④ 扩展里点刷新/重新加载。"),
    ("打开学习网站却被拦了（误判）？",
     "右键桌宠 →「这个是学习用的！」，宠物会记住这个窗口/网站，以后不再拦。"
     "浏览器里也可以点拦截页上的「标记为学习」。"),
    ("拦截页反复跳转？",
     "白名单要用精确链接（子串匹配）。例如 B 站上课：黑名单填 bilibili.com，"
     "白名单填你上课视频的完整链接。"),
    ("强制关闭会不会丢东西？",
     "强制关闭默认关闭；开启后带保存倒计时（默认 10 秒），只在确定是分心内容时触发，"
     "文档类永远不会被强制关闭。"),
    ("怎么让它不打扰我？",
     "右键 →「免打扰：开启」：宠物闭嘴静音，但监督照常（仍检测/记录/阻断）。"
     "想完全不监督就右键「结束学习」或退出。"),
    ("怎么退出 / 藏起来？",
     "退出：右键 → 退出，或托盘右键 → 退出（有退出锁时需输入退出码）。"
     "隐藏：托盘左键双击，或 Ctrl+Alt+H。"),
    ("用了自己的图片当桌宠，会不会不兼容？",
     "不会。一张图自动适配所有状态/装饰/托盘；想更生动可再放 angry.png / celebrate.png "
     "等单独状态图（见 tools/theme_scaffold.py）。"),
    ("什么是主题包？怎么用？",
     "主题包 = 一个 zip，里面可放多张状态图（生气/暴怒/庆祝/睡觉…）。"
     "右键桌宠 → 形象 → 导入主题包… 选 zip 即可；比单张图更生动。"
     "也可以用 python tools/theme_scaffold.py 你的图.png 名字 把一张图自动生成主题骨架。"),
    ("怎么屏蔽微信/QQ 等软件的通知？",
     "开始学习时会自动开启 Windows 专注助手（设置 → 通知屏蔽 可关）："
     "其他应用不弹通知、任务栏不闪烁、不响铃；结束学习自动恢复原样。"),
]


class HelpWindow:
    def __init__(self, parent, welcome=False):
        self.welcome = welcome
        self.root = tk.Toplevel(parent)
        self.root.title("Focus Pet 使用帮助")
        self.root.geometry("760x680")
        self._welcome_var = tk.BooleanVar(value=True)
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- 界面 ----------
    def _build(self):
        style_window(self.root)
        if self.welcome:
            banner = tk.Frame(self.root, bg=ACCENT_LIGHT)
            banner.pack(fill="x", padx=14, pady=(12, 0))
            tk.Label(banner, text="🎉 欢迎使用 Focus Pet！", bg=ACCENT_LIGHT,
                     fg=ACCENT, font=("Microsoft YaHei UI", 15, "bold")).pack(pady=(10, 0))
            tk.Label(banner, text="一只陪你学习、也监督你学习的桌宠。平时卖萌，你摸鱼时逐级变生气管住你。",
                     bg=ACCENT_LIGHT, fg=TEXT, font=("Microsoft YaHei UI", 10)).pack(pady=(2, 10))
        else:
            add_header(self.root, f"Focus Pet 使用帮助",
                       f"本帮助随版本自动更新，不会过期。当前版本：v{help_data.VERSION}").pack(
                padx=16, pady=(12, 0), anchor="w")

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=12, pady=10)
        self._build_features_tab(nb)
        self._build_hotkeys_tab(nb)
        self._build_settings_tab(nb)
        self._build_faq_tab(nb)
        self._build_about_tab(nb)

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(pady=(0, 10))
        if self.welcome:
            tk.Checkbutton(bar, text="下次启动不再显示欢迎（仍可从右键「使用帮助…」打开）",
                           variable=self._welcome_var, bg=BG,
                           font=("Microsoft YaHei UI", 9)).pack(side="left", padx=10)
        accent_button(bar, "知道了", self._on_close).pack(side="left", padx=10)

    def _scrolled(self, parent, bg=CARD):
        canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=bg)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return inner

    def _build_features_tab(self, nb):
        tab = tk.Frame(nb, bg=CARD)
        nb.add(tab, text="功能一览")
        inner = self._scrolled(tab)
        for f in help_data.FEATURES:
            row = tk.Frame(inner, bg=CARD, padx=12, pady=6)
            row.pack(fill="x")
            is_new = f["added_in"] == help_data.VERSION
            tk.Label(row, text=f["name"], bg=CARD, fg=ACCENT,
                     font=("Microsoft YaHei UI", 11, "bold"), anchor="w").pack(anchor="w")
            if is_new:
                tk.Label(row, text="【本版新增】", bg=ACCENT, fg="white",
                         font=("Microsoft YaHei UI", 8, "bold")).pack(anchor="w")
            tk.Label(row, text=f"在哪开：{f['where']}", bg=CARD, fg=TEXT,
                     font=("Microsoft YaHei UI", 9), anchor="w", justify="left").pack(anchor="w", fill="x")
            tk.Label(row, text=f"干什么：{f['what']}", bg=CARD, fg=MUTED,
                     font=("Microsoft YaHei UI", 9), anchor="w", justify="left").pack(anchor="w", fill="x")

    def _build_hotkeys_tab(self, nb):
        tab = tk.Frame(nb, bg=CARD)
        nb.add(tab, text="快捷键")
        inner = self._scrolled(tab)
        hotkeys = help_data.hotkeys_help()
        if not hotkeys:
            tk.Label(inner, text="（未启用全局快捷键，可在 设置 → 全局快捷键 打开）",
                     bg=CARD, fg=MUTED, font=("Microsoft YaHei UI", 10)).pack(pady=20)
        for h in hotkeys:
            row = tk.Frame(inner, bg=CARD, padx=12, pady=8)
            row.pack(fill="x")
            tk.Label(row, text=h["combo"], bg=ACCENT_LIGHT, fg=ACCENT,
                     font=("Microsoft YaHei UI", 11, "bold"), padx=8, pady=2).pack(side="left")
            tk.Label(row, text=h["desc"], bg=CARD, fg=TEXT,
                     font=("Microsoft YaHei UI", 10)).pack(side="left", padx=10)

    def _build_settings_tab(self, nb):
        tab = tk.Frame(nb, bg=CARD)
        nb.add(tab, text="设置项")
        inner = self._scrolled(tab)
        items = help_data.settings_help()
        by_cat = {}
        for it in items:
            by_cat.setdefault(it["category"], []).append(it)
        for cat, entries in by_cat.items():
            tk.Label(inner, text=f"— {cat} —", bg=CARD, fg=ACCENT,
                     font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
            for e in entries:
                txt = e["label"] + (f"：{e['desc']}" if e.get("desc") else "")
                tk.Label(inner, text="・" + txt, bg=CARD, fg=TEXT, anchor="w", justify="left",
                         font=("Microsoft YaHei UI", 9)).pack(anchor="w", fill="x", padx=16, pady=1)

    def _build_faq_tab(self, nb):
        tab = tk.Frame(nb, bg=CARD)
        nb.add(tab, text="常见问题")
        inner = self._scrolled(tab)
        for q, a in FAQ:
            tk.Label(inner, text="❓ " + q, bg=CARD, fg=ACCENT,
                     font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 1))
            tk.Label(inner, text=a, bg=CARD, fg=TEXT, anchor="w", justify="left",
                     font=("Microsoft YaHei UI", 9)).pack(anchor="w", fill="x", padx=18, pady=1)

    def _build_about_tab(self, nb):
        tab = tk.Frame(nb, bg=CARD)
        nb.add(tab, text="关于")
        inner = self._scrolled(tab)
        about = [
            ("版本", f"Focus Pet v{help_data.VERSION}"),
            ("定位", "陪你学习、也监督你学习的桌面养成宠物"),
            ("隐私承诺", "摄像头画面、截图、窗口信息全部本地处理，不保存、不上传；"
                         "浏览器扩展只连 127.0.0.1 本地桥接。"),
            ("开源", "项目开源，文档见 docs/ 目录（README / 设计文档 / 总结文档）"),
            ("开发者", "打开集中配置编辑器：右键桌宠 → 设置…，或 python main.py --settings"),
        ]
        for k, v in about:
            row = tk.Frame(inner, bg=CARD, padx=12, pady=8)
            row.pack(fill="x")
            tk.Label(row, text=k, bg=CARD, fg=ACCENT,
                     font=("Microsoft YaHei UI", 10, "bold"), width=8, anchor="w").pack(side="left")
            tk.Label(row, text=v, bg=CARD, fg=TEXT, anchor="w", justify="left",
                     font=("Microsoft YaHei UI", 9), wraplength=460).pack(side="left", fill="x", expand=True)

    # ---------- 关闭 ----------
    def _on_close(self):
        if self.welcome and self._welcome_var.get():
            self._mark_first_run_done()
        self.root.destroy()

    @staticmethod
    def _mark_first_run_done():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            cfg.setdefault("first_run", {})["done"] = True
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
