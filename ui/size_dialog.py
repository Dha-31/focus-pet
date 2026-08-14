"""ui/size_dialog.py：调整桌宠大小（v3.7.1）。

- 滑块（50% ~ 300%）自由调整桌宠大小
- 实时预览：按比例显示桌宠窗口大小 + 当前形象，直观看到"有多大"
- 点「应用」生效并保存；迷你模式不受影响（仍是固定小尺寸）
"""
import tkinter as tk

from ui import window_manager
from ui import pet_renderer
from ui.theme_ui import accent_button, add_header, style_window


class SizeDialog:
    def __init__(self, pet):
        self.pet = pet
        self.root = tk.Toplevel(pet.root)
        self.root.title("调整桌宠大小")
        self.root.geometry("1080x1000")
        window_manager.open(self.root)

        self._pct = 100          # 当前百分比（相对默认尺寸）
        self._build()
        self._update_preview()

    def _build(self):
        style_window(self.root)
        add_header(self.root, "调整桌宠大小",
                   "拖动滑块自由调整；预览区实时显示实际大小").pack(padx=14, pady=(12, 0), anchor="w")

        # 预览区（随窗口变大重绘）
        self.preview = tk.Canvas(self.root, bg="#fdf6f0",
                                 highlightbackground="#f0e0d8", highlightthickness=1)
        self.preview.pack(padx=14, pady=10, fill="both", expand=True)
        self.preview.bind("<Configure>", lambda e: self._update_preview())

        # 滑块
        row = tk.Frame(self.root)
        row.pack(pady=(0, 4))
        tk.Label(row, text="大小：", font=("Microsoft YaHei UI", 10)).pack(side="left")
        self.scale = tk.Scale(row, from_=50, to=300, orient="horizontal", length=220,
                              resolution=5, showvalue=False,
                              command=lambda v: self._on_slide(v))
        self.scale.set(100)
        self.scale.pack(side="left", padx=6)
        self.size_var = tk.StringVar()
        tk.Label(row, textvariable=self.size_var, font=("Microsoft YaHei UI", 10),
                 fg="#e07a2f", width=12).pack(side="left")

        bar = tk.Frame(self.root)
        bar.pack(pady=10)
        accent_button(bar, "应用", self._apply).pack(side="left", padx=6)
        tk.Button(bar, text="取消", command=self.root.destroy).pack(side="left", padx=6)

    # ---------- 预览 ----------
    def _target_size(self):
        base = self.pet.normal_size
        return (int(base[0] * self._pct / 100), int(base[1] * self._pct / 100))

    def _on_slide(self, value):
        self._pct = int(float(value))
        self._update_preview()

    def _update_preview(self):
        c = self.preview
        c.delete("all")
        pw = self.preview.winfo_width() or 620
        ph = self.preview.winfo_height() or 360
        tw, th = self._target_size()
        # 线性比例：100% 显示为 150px 的框，滑块变化按比例放大/缩小（可超出预览区，直观）
        base_w, base_h = self.pet.normal_size
        k = min(150.0 / base_w, 150.0 / base_h)
        box_w = max(24, int(tw * k))
        box_h = max(24, int(th * k))
        bx = (pw - box_w) / 2
        by = (ph - box_h) / 2 - 6
        # 窗口外框（虚线表示范围）
        c.create_rectangle(bx, by, bx + box_w, by + box_h, outline="#e07a2f",
                           width=2, dash=(4, 3))
        # 宠物（随框等比变化）
        img = self.pet._image_for("idle")
        cx, cy = bx + box_w / 2, by + box_h / 2
        if img is not None:
            iw, ih = img.width(), img.height()
            fit = min((box_w - 12) / iw, (box_h - 12) / ih)
            disp = img
            if fit < 1.0:
                factor = max(1, int(1.0 / fit))
                disp = img.subsample(factor, factor)
            c.create_image(cx, cy, image=disp)
            self._preview_ref = disp
        else:
            # 程序化小猫，随框等比
            vs = min((box_w - 12) / 170.0, (box_h - 12) / 170.0)
            pet_renderer.draw_procedural_pet(
                c, cx, cy + 6, 0, self.pet.mood, self.pet.level,
                accessory=self.pet.accessory, t=0.0, show_level=False,
                view_scale=vs)
        # 尺寸文字（框超出预览区时放顶部）
        ty = by + box_h + 14
        if ty > ph - 10:
            ty = 12
        c.create_text(pw / 2, ty, text=f"{tw} × {th} px",
                      fill="#e07a2f", font=("Microsoft YaHei UI", 10, "bold"))
        self.size_var.set(f"{tw}×{th}")

    # ---------- 应用 ----------
    def _apply(self):
        tw, th = self._target_size()
        self.pet.set_pet_size(tw, th)
        self.root.destroy()
