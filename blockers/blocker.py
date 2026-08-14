"""分级阻断执行器。

Lv1 提醒    -> 宠物气泡："该学习啦！"
Lv2 遮挡    -> 宠物放大挡在屏幕中间
Lv3 最小化  -> 把分心窗口最小化
Lv4 强制关闭 -> 倒计时后发送 WM_CLOSE（默认关闭，需用户在配置里开启）

只在阻断级别升高时执行一次；回到学习（tier 0）时自动复位。
"""
from sensors.window_monitor import minimize_window, post_close


class Blocker:
    def __init__(self, pet, config):
        self.pet = pet
        self.config = config
        self.active_tier = 0
        self.pending_close = None  # {"hwnd": int, "remaining": float}

    def handle(self, tier, hwnd, title=""):
        """按当前阻断级别处理（由监督循环每轮调用）。"""
        if tier > self.active_tier:
            self._execute(tier, hwnd, title)
        self.active_tier = max(self.active_tier, tier) if tier > 0 else 0

    def _execute(self, tier, hwnd, title):
        if tier >= 1:
            self.pet.say("该学习啦！" + (f"（{title[:12]}）" if title else ""))
        if tier >= 2:
            self.pet.block(True)
        if tier >= 3:
            minimize_window(hwnd)
            self.pet.say("哼，我把它收起来了！")
        if tier >= 4:
            self._start_force_close(hwnd)

    def _start_force_close(self, hwnd):
        if not self.config["blocking"]["force_close_enabled"]:
            self.pet.say("要是开启强制关闭，我早就把它关掉了！")
            return
        if self.pending_close is None:
            self.pending_close = {
                "hwnd": hwnd,
                "remaining": float(self.config["blocking"]["save_warning_seconds"]),
            }

    def tick(self, dt=1.0):
        """强制关闭倒计时（由监督循环每轮调用）。"""
        if not self.pending_close:
            return
        self.pending_close["remaining"] -= dt
        remaining = max(0, int(self.pending_close["remaining"]))
        self.pet.say(f"{remaining} 秒后关闭，快保存！")
        if self.pending_close["remaining"] <= 0:
            hwnd = self.pending_close["hwnd"]
            post_close(hwnd)
            self.pending_close = None
            self.pet.say("关掉了。回来学习吧。")
            self.pet.block(False)

    def reset(self):
        """回到学习状态：撤销倒计时、收起遮挡。"""
        self.active_tier = 0
        self.pending_close = None
        self.pet.block(False)