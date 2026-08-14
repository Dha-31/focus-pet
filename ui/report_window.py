"""ui/report_window.py：专注数据报表。

用 matplotlib 把 focus_log.json（会话）和 events.json（分心事件）
可视化：每日专注柱状图 + 每日分心柱状图 + 最近分心明细。
图表是本地生成，不保存上传（PNG 存到 data/ 供展示）。
"""
import json
import os
import tkinter as tk

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: E402
    from matplotlib import font_manager  # noqa: E402
    HAS_MPL = True
except Exception:
    HAS_MPL = False   # 精简版客户端未打包 matplotlib 时优雅降级

from core.config import DATA_DIR  # noqa: E402
from ui.theme_ui import accent_button, add_header, style_window  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _setup_font():
    for path in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        if os.path.exists(path):
            try:
                font_manager.fontManager.addfont(path)
                name = font_manager.FontProperties(fname=path).get_name()
                plt.rcParams["font.sans-serif"] = [name]
                break
            except Exception:
                pass
    plt.rcParams["axes.unicode_minus"] = False


def _load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _daily_counts(records, field, date_field="start"):
    daily = {}
    for rec in records:
        raw = rec.get(date_field) or ""
        day = raw[:10]
        if not day:
            continue
        daily[day] = daily.get(day, 0) + float(rec.get(field, 0) or 0)
    return daily


def _bar_chart(daily, title, color, out_name):
    fig, ax = plt.subplots(figsize=(5.4, 2.5), dpi=100)
    days = sorted(daily)
    vals = [daily[d] for d in days]
    ax.bar(range(len(days)), vals, color=color)
    ax.set_title(title, fontsize=11)
    ax.set_xticks(range(len(days)))
    ax.set_xticklabels([d[5:] for d in days], rotation=30, fontsize=8)
    ax.set_ylabel("分钟" if "专注" in title else "次")
    fig.tight_layout()
    out = os.path.join(DATA_DIR, out_name)
    fig.savefig(out)
    plt.close(fig)
    return out


class ReportWindow:
    def __init__(self, parent):
        self.root = tk.Toplevel(parent)
        self.root.title("专注数据报表")
        self.root.geometry("600x660")
        self.root.attributes("-topmost", True)
        self.root.transient(parent)
        self.root.grab_set()
        style_window(self.root)
        self._build()

    def _build(self):
        _setup_font()
        sessions = _load_json("focus_log.json")
        events = _load_json("events.json")
        dist_events = [e for e in events if e.get("kind") == "distraction"]

        total_focus = sum(float(s.get("focus_minutes", 0) or 0) for s in sessions)
        total_distract = sum(float(s.get("distract_minutes", 0) or 0) for s in sessions)
        avg_focus = total_focus / len(sessions) if sessions else 0

        tk.Label(self.root, text="专注数据报表",
                 font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(10, 2))
        tk.Label(self.root,
                 text=f"会话 {len(sessions)} 次 ｜ 累计专注 {total_focus:.0f} 分钟 ｜ "
                      f"累计分心 {total_distract:.0f} 分钟 ｜ 平均每次 {avg_focus:.0f} 分钟",
                 font=("Microsoft YaHei UI", 10), fg="#555").pack()

        # 图表1：每日专注
        daily_focus = _daily_counts(sessions, "focus_minutes")
        if not HAS_MPL:
            tk.Label(self.root, text="（图表功能需要 matplotlib，本体验版未打包；文字统计仍可用）",
                     fg="#e07a2f", font=("Microsoft YaHei UI", 9)).pack(pady=4)
        if daily_focus and HAS_MPL:
            p1 = _bar_chart(daily_focus, "每日专注时长", "#5cb85c", "report_daily_focus.png")
            self._show_image(p1)
        else:
            tk.Label(self.root, text="（暂无专注数据，先去学习一会儿吧）",
                     fg="#999").pack(pady=6)

        # 图表2：每日分心次数
        daily_dist = _daily_counts(dist_events, "times", date_field="time")
        if not daily_dist:
            for e in dist_events:
                day = (e.get("time") or "")[:10]
                if day:
                    daily_dist[day] = daily_dist.get(day, 0) + 1
        if daily_dist and HAS_MPL:
            p2 = _bar_chart(daily_dist, "每日分心次数", "#d9534f", "report_daily_distract.png")
            self._show_image(p2)

        # 最近分心明细
        if dist_events:
            tk.Label(self.root, text="最近分心记录：", font=("Microsoft YaHei UI", 10)).pack(anchor="w", padx=14)
            box = tk.Text(self.root, width=72, height=7, font=("Microsoft YaHei UI", 9))
            box.pack(padx=10, pady=4)
            for e in dist_events[-8:]:
                box.insert("end", f"{e.get('time', '')}  {e.get('detail', '')}\n")
            box.config(state="disabled")

        tk.Button(self.root, text="关闭", width=12, command=self.root.destroy).pack(pady=8)

    def _show_image(self, path):
        try:
            img = tk.PhotoImage(file=path)
            label = tk.Label(self.root, image=img)
            label.image = img  # 防止被回收
            label.pack(pady=4)
        except Exception as exc:
            tk.Label(self.root, text=f"图表生成失败：{exc}", fg="#999").pack()