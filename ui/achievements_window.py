"""ui/achievements_window.py：成就徽章窗口。"""
import tkinter as tk

from core.achievements import ACHIEVEMENTS, AchievementManager


class AchievementsWindow:
    def __init__(self, parent, manager):
        self.manager = manager
        self.root = tk.Toplevel(parent)
        self.root.title("成就徽章")
        self.root.geometry("460x520")
        self.root.attributes("-topmost", True)
        self.root.transient(parent)
        self.root.grab_set()
        self._build()

    def _build(self):
        unlocked = len(self.manager.unlocked)
        total = len(ACHIEVEMENTS)
        tk.Label(self.root, text=f"成就徽章　已解锁 {unlocked}/{total}",
                 font=("Microsoft YaHei UI", 13, "bold")).pack(pady=(12, 4))
        tk.Label(self.root, text="解锁成就可获得 20 专注币奖励！",
                 fg="#888", font=("Microsoft YaHei UI", 9)).pack()

        canvas = tk.Canvas(self.root, highlightthickness=0)
        scroll = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=6)
        scroll.pack(side="right", fill="y", pady=6)

        for item in ACHIEVEMENTS:
            unlocked = item["id"] in self.manager.unlocked
            row = tk.Frame(inner, padx=8, pady=4)
            row.pack(fill="x")
            status = "✅" if unlocked else "🔒"
            color = "#333" if unlocked else "#999"
            tk.Label(row, text=f"{status} {item['icon']} {item['name']}",
                     font=("Microsoft YaHei UI", 11),
                     fg=color, width=16, anchor="w").pack(side="left")
            tk.Label(row, text=item["desc"], font=("Microsoft YaHei UI", 9),
                     fg="#666" if unlocked else "#bbb", anchor="w").pack(side="left", fill="x", expand=True)

        tk.Button(self.root, text="关闭", width=12, command=self.root.destroy).pack(pady=(0, 8))