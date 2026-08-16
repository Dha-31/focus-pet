"""ui/rules_window.py：黑白名单编辑窗口。

- 黑名单：命中的网站/进程会被拦截或提醒（绝对不可用）
- 白名单：即使命中黑名单也放行（学习可用）
- 保存写 data/blacklist.json、data/whitelist.json，规则引擎热更新立即生效
"""
import json
import os
import tkinter as tk
from tkinter import messagebox

from core.config import DATA_DIR
from ui.theme_ui import add_header, accent_button, style_window


def _load(path):
    data = {"urls": [], "processes": [], "titles": []}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data.update(loaded)
        except (json.JSONDecodeError, OSError):
            pass
    return data


class RulesWindow:
    def __init__(self, parent):
        self.blacklist_path = os.path.join(DATA_DIR, "blacklist.json")
        self.whitelist_path = os.path.join(DATA_DIR, "whitelist.json")
        self.root = tk.Toplevel(parent)
        self.root.title("黑白名单设置")
        self.root.geometry("1500x900")
        style_window(self.root)
        self._build()
        # 确保窗口可正常输入：置前 + 聚焦第一个文本框
        try:
            self.root.lift()
            self.root.focus_force()
            self.root.after(100, lambda: self._bl_urls.focus_set())
        except Exception:
            pass

    @staticmethod
    def _lines(text_widget):
        return [ln.strip() for ln in text_widget.get("1.0", "end").splitlines() if ln.strip()]

    def _make_area(self, parent, title, sub):
        """返回 (frame, urls_text, procs_text)。"""
        frame = tk.Frame(parent, bg="#fdf6f0")
        tk.Label(frame, text=title, font=("Microsoft YaHei UI", 12, "bold"),
                 bg="#fdf6f0", fg="#e06f8f").pack(anchor="w")
        tk.Label(frame, text=sub, font=("Microsoft YaHei UI", 9),
                 bg="#fdf6f0", fg="#888").pack(anchor="w", pady=(0, 4))
        tk.Label(frame, text="网站 URL（每行一个，子串匹配）",
                 bg="#fdf6f0", fg="#555", font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        urls = tk.Text(frame, height=10, width=42, font=("Microsoft YaHei UI", 10),
                       relief="solid", bd=1)
        urls.pack(fill="both", expand=True, pady=(0, 6))
        tk.Label(frame, text="进程名（每行一个，如 steam.exe）",
                 bg="#fdf6f0", fg="#555", font=("Microsoft YaHei UI", 9)).pack(anchor="w")
        procs = tk.Text(frame, height=4, width=42, font=("Microsoft YaHei UI", 10),
                        relief="solid", bd=1)
        procs.pack(fill="both", expand=True)
        return frame, urls, procs

    def _build(self):
        add_header(self.root, "黑白名单设置",
                  "白名单优先于黑名单；保存立即生效，无需重启。").pack(padx=14, pady=(12, 0), anchor="w")
        cols = tk.Frame(self.root)
        cols.pack(fill="both", expand=True, padx=12, pady=8)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        self._bl_frame, self._bl_urls, self._bl_procs = self._make_area(
            cols, "🚫 黑名单（绝对不可用）", "命中这些网站/进程会被提醒或阻断")
        self._wl_frame, self._wl_urls, self._wl_procs = self._make_area(
            cols, "✅ 白名单（学习可用）", "即使命中黑名单也放行")
        self._bl_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._wl_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        bl = _load(self.blacklist_path)
        wl = _load(self.whitelist_path)
        self._bl_urls.insert("1.0", "\n".join(bl.get("urls", [])))
        self._bl_procs.insert("1.0", "\n".join(bl.get("processes", [])))
        self._wl_urls.insert("1.0", "\n".join(wl.get("urls", [])))
        self._wl_procs.insert("1.0", "\n".join(wl.get("processes", [])))

        bar = tk.Frame(self.root)
        bar.pack(pady=8)
        accent_button(bar, "💾 保存并应用", self._save).pack(side="left", padx=5)
        tk.Button(bar, text="关闭", width=8, command=self.root.destroy).pack(side="left", padx=5)
        tk.Label(self.root, text="提示：白名单优先于黑名单；「教宠物」学到的内容会自动进入白名单。",
                 fg="#888", font=("Microsoft YaHei UI", 9)).pack(pady=(0, 10))

    def _save(self):
        bl = _load(self.blacklist_path)
        wl = _load(self.whitelist_path)
        bl["urls"] = self._lines(self._bl_urls)
        bl["processes"] = self._lines(self._bl_procs)
        wl["urls"] = self._lines(self._wl_urls)
        wl["processes"] = self._lines(self._wl_procs)
        with open(self.blacklist_path, "w", encoding="utf-8") as f:
            json.dump(bl, f, ensure_ascii=False, indent=2)
        with open(self.whitelist_path, "w", encoding="utf-8") as f:
            json.dump(wl, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("已保存", "黑白名单已保存，立即生效。", parent=self.root)

