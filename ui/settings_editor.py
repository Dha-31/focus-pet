"""ui/settings_editor.py：集中配置编辑器（数据驱动）。

所有可调参数定义在 core/settings_schema.py 的清单里，
编辑器自动按清单生成输入界面——以后加新参数，只需在清单加一条，
编辑器自动多出对应输入框（不用改编辑器代码）。

- 开发者参数（settings.json）：汇率 / 阻断阈值 / 经验表 / 商店价格 / 关键词
- 应用配置（config.json）：番茄钟 / 锁定 / 扩展 / 摄像头 / 截图分析
- 保存即热更新，全项目实时生效；支持导出/导入（备份与分享）
"""
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.config import CONFIG_PATH, load_config, save_config
from core.settings import SETTINGS_PATH, settings
from core.settings_schema import CONFIG_SCHEMA, DEFAULTS, SETTINGS_SCHEMA
from ui.theme_ui import add_header, style_window


def _categories(schema):
    seen = []
    for entry in schema:
        cat = entry.get("category", "其他")
        if cat not in seen:
            seen.append(cat)
    return seen


class SettingsEditor:
    def __init__(self, parent, pet=None):
        self.pet = pet
        self.root = tk.Toplevel(parent)
        self.root.title("集中配置编辑器")
        self.root.geometry("640x720")
        self.root.resizable(False, False)
        style_window(self.root)
        self._rows = []  # (entry, getter, setter)
        self._build()

    # ---------- 界面 ----------
    def _build(self):
        add_header(self.root, "集中配置编辑器",
                  "所有参数集中一处：改一个值全项目生效（保存即热更新，无需重启）").pack(padx=14, pady=(12, 0), anchor="w")
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=6)
        self._build_tab(nb, "开发者参数", SETTINGS_SCHEMA)
        self._build_tab(nb, "应用配置", CONFIG_SCHEMA)

        bar = tk.Frame(self.root)
        bar.pack(pady=8)
        tk.Button(bar, text="💾 保存并应用", width=14, bg="#5cb85c", fg="white",
                  command=self._save).pack(side="left", padx=5)
        tk.Button(bar, text="恢复默认", width=10, command=self._restore_defaults).pack(side="left", padx=5)
        tk.Button(bar, text="导出配置", width=10, command=self._export).pack(side="left", padx=5)
        tk.Button(bar, text="导入配置", width=10, command=self._import).pack(side="left", padx=5)
        tk.Button(bar, text="关闭", width=8, command=self.root.destroy).pack(side="left", padx=5)
        tk.Label(self.root, text="保存后实时生效（无需重启）；导出/导入用于备份与分享",
                 fg="#888", font=("Microsoft YaHei UI", 9)).pack(pady=(0, 8))

    def _build_tab(self, nb, tab_name, schema):
        tab = tk.Frame(nb)
        nb.add(tab, text=tab_name)
        canvas = tk.Canvas(tab, highlightthickness=0)
        scroll = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for cat in _categories(schema):
            tk.Label(inner, text=f"— {cat} —", font=("Microsoft YaHei UI", 11, "bold"),
                     fg="#5a7fb0").pack(anchor="w", padx=10, pady=(8, 2))
            for entry in schema:
                if entry.get("category", "其他") != cat:
                    continue
                self._add_row(inner, entry)

    def _add_row(self, parent, entry):
        row = tk.Frame(parent, padx=10, pady=3)
        row.pack(fill="x")
        label = tk.Label(row, text=entry["label"], width=16, anchor="w",
                         font=("Microsoft YaHei UI", 10))
        label.pack(side="left")
        wtype = entry["type"]
        if wtype == "bool":
            var = tk.BooleanVar()
            widget = tk.Checkbutton(row, variable=var)
            widget.pack(side="left")
            getter = var.get
            setter = var.set
        elif wtype == "int" or wtype == "float":
            widget = tk.Spinbox(row, width=10, from_=entry.get("min", 0),
                                to=entry.get("max", 1000),
                                increment=entry.get("step", 1))
            widget.pack(side="left")
            getter = lambda w=widget, t=wtype: (int(w.get()) if t == "int" else float(w.get()))
            setter = lambda v, w=widget: w.delete(0, "end") or w.insert(0, str(v))
        elif wtype == "str":
            widget = tk.Entry(row, width=20)
            widget.pack(side="left")
            getter = lambda w=widget: w.get().strip()
            setter = lambda v, w=widget: w.delete(0, "end") or w.insert(0, str(v))
        elif wtype == "list":
            widget = tk.Entry(row, width=22)
            widget.pack(side="left")
            getter = lambda w=widget: [int(x.strip()) for x in w.get().split(",") if x.strip()]
            setter = lambda v, w=widget: w.delete(0, "end") or w.insert(0, ",".join(str(x) for x in v))
        elif wtype == "textlist":
            widget = tk.Text(row, width=26, height=entry.get("height", 4), font=("Microsoft YaHei UI", 9))
            widget.pack(side="left")
            getter = lambda w=widget: [x.strip() for x in w.get("1.0", "end").splitlines() if x.strip()]
            setter = lambda v, w=widget: (w.delete("1.0", "end"), w.insert("1.0", "\n".join(str(x) for x in v)))
        else:
            widget = tk.Label(row, text=f"(未知类型 {wtype})", fg="#999")
            widget.pack(side="left")
            return
        desc = entry.get("desc", "")
        if desc:
            tk.Label(row, text=desc, fg="#999", font=("Microsoft YaHei UI", 8)).pack(side="left", padx=6)

        # 载入当前值
        value = self._load_value(entry)
        try:
            setter(value if value is not None else self._default_for(wtype, entry))
        except Exception:
            pass
        self._rows.append((entry, getter, setter))

    @staticmethod
    def _default_for(wtype, entry):
        if wtype == "bool":
            return False
        if wtype == "int":
            return 0
        if wtype == "float":
            return 0.0
        if wtype == "list":
            return []
        return ""

    def _load_value(self, entry):
        path = entry["path"]
        if entry["file"] == "settings":
            return settings.get(path)
        # config.json
        cfg = load_config()
        node = cfg
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node

    # ---------- 保存 / 恢复 / 导出 / 导入 ----------
    def _save(self):
        for entry, getter, _ in self._rows:
            try:
                value = getter()
            except Exception:
                messagebox.showwarning("集中配置", f"「{entry['label']}」的值格式不对，请检查", parent=self.root)
                return
            if entry["file"] == "settings":
                settings.set(entry["path"], value)
            else:
                cfg = load_config()
                node = cfg
                parts = entry["path"].split(".")
                for part in parts[:-1]:
                    node = node.setdefault(part, {})
                node[parts[-1]] = value
                save_config(cfg)
        if self.pet is not None:
            try:
                self.pet.reload_skin()
            except Exception:
                pass
        messagebox.showinfo("集中配置", "已保存，实时生效！", parent=self.root)

    def _restore_defaults(self):
        if not messagebox.askyesno("恢复默认", "确定把所有参数恢复为默认值吗？", parent=self.root):
            return
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, ensure_ascii=False, indent=2)
        settings.reload()
        from core.config import DEFAULTS as CFG_DEFAULTS
        cfg = load_config()
        for key, value in CFG_DEFAULTS.items():
            cfg[key] = json.loads(json.dumps(value))
        save_config(cfg)
        self.root.destroy()
        SettingsEditor(self.root.master if self.root.master else None, pet=self.pet)
        messagebox.showinfo("集中配置", "已恢复默认。", parent=self.root)

    def _export(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="导出配置", defaultextension=".json",
            initialfile="focus_pet_settings_backup.json",
            filetypes=[("JSON", "*.json")])
        if not path:
            return
        data = {"settings": settings.get_dict() if hasattr(settings, "get_dict") else None,
                "config": load_config()}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("导出", f"已导出到：\n{path}", parent=self.root)

    def _import(self):
        path = filedialog.askopenfilename(
            parent=self.root, title="导入配置", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("导入", f"文件解析失败：{exc}", parent=self.root)
            return
        if isinstance(data.get("settings"), dict):
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(data["settings"], f, ensure_ascii=False, indent=2)
            settings.reload()
        if isinstance(data.get("config"), dict):
            save_config(data["config"])
        messagebox.showinfo("导入", "导入成功，已实时生效。", parent=self.root)
        self.root.destroy()
        SettingsEditor(self.root.master if self.root.master else None, pet=self.pet)


def run(parent, pet=None):
    SettingsEditor(parent, pet=pet)