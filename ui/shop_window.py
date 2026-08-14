"""ui/shop_window.py：商店——用专注币兑换装饰品和家具。"""
import tkinter as tk
from tkinter import messagebox, ttk

from core import shop
from ui.theme_ui import accent_button, add_header, style_window


class ShopWindow:
    def __init__(self, parent, inventory, on_equip=None, on_place=None):
        self.inventory = inventory
        self.on_equip = on_equip or (lambda aid: None)
        self.on_place = on_place or (lambda fid: None)
        self.root = tk.Toplevel(parent)
        self.root.title("商店 - 专注币兑换")
        self.root.geometry("640x580")
        style_window(self.root)
        self._items = {}
        self._build()
        self.refresh()

    def _build(self):
        self.coin_var = tk.StringVar()
        add_header(self.root, "商店", "学习赚专注币，给宠物买装饰、给房间添家具！").pack(padx=14, pady=(12, 0), anchor="w")
        tk.Label(self.root, textvariable=self.coin_var,
                 font=("Microsoft YaHei UI", 12, "bold"), fg="#e07a2f").pack(pady=(6, 2))

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=8, pady=6)
        tab_acc = tk.Frame(nb)
        tab_fur = tk.Frame(nb)
        nb.add(tab_acc, text="装饰品")
        nb.add(tab_fur, text="家具")
        self._build_tab(tab_acc, "accessory")
        self._build_tab(tab_fur, "furniture")

        accent_button(self.root, "关闭", self.root.destroy, width=10).pack(pady=(0, 10))

    def _build_tab(self, parent, kind):
        canvas = tk.Canvas(parent, highlightthickness=0)
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        items = shop.ACCESSORIES if kind == "accessory" else shop.FURNITURE
        for item in items:
            row = tk.Frame(inner, padx=8, pady=5)
            row.pack(fill="x")
            tk.Label(row, text=f"{item['name']}　💰{shop.price_of(item)}",
                     font=("Microsoft YaHei UI", 10), width=16, anchor="w").pack(side="left")
            btn = tk.Button(row, width=8)
            if kind == "accessory":
                btn.config(command=lambda it=item: self._click_accessory(it))
            else:
                btn.config(command=lambda it=item: self._click_furniture(it))
            btn.pack(side="left", padx=6)
            self._items[item["id"]] = btn

    def refresh(self):
        inv = self.inventory
        self.coin_var.set(f"专注币：{inv.coins:.0f}")
        for item in shop.ACCESSORIES:
            btn = self._items.get(item["id"])
            if btn is None:
                continue
            if item["id"] not in inv.owned_accessories:
                btn.config(text="购买", state="normal")
            elif item["id"] == inv.equipped_accessory:
                btn.config(text="已装备", state="disabled")
            else:
                btn.config(text="装备", state="normal")
        for item in shop.FURNITURE:
            btn = self._items.get(item["id"])
            if btn is None:
                continue
            btn.config(text="放置" if item["id"] in inv.owned_furniture else "购买",
                       state="normal")

    def _click_accessory(self, item):
        inv = self.inventory
        if item["id"] not in inv.owned_accessories:
            if not inv.can_afford(item["price"]):
                messagebox.showinfo("商店", "专注币不足！多学一会儿再来~", parent=self.root)
                return
            inv.buy(item)
            messagebox.showinfo("商店", f"已购买 {item['name']}！", parent=self.root)
        inv.equip(item["id"])
        self.on_equip(item["id"])
        self.refresh()

    def _click_furniture(self, item):
        inv = self.inventory
        if item["id"] not in inv.owned_furniture:
            if not inv.can_afford(item["price"]):
                messagebox.showinfo("商店", "专注币不足！多学一会儿再来~", parent=self.root)
                return
            inv.buy(item)
            messagebox.showinfo("商店", f"已购买 {item['name']}！", parent=self.root)
        if inv.place(item["id"]):
            self.on_place(item["id"])
            messagebox.showinfo("商店", f"{item['name']} 已摆进个人空间！", parent=self.root)
        else:
            messagebox.showinfo("商店", "空间满了（最多 6 件家具），先去空间移除一些", parent=self.root)
        self.refresh()