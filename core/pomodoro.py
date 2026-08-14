"""番茄钟（可开关）：
- 开：自动进入 专注/休息 循环；休息窗口内解除阻断，宠物切萌宠催你休息
- 关：持续监督模式
"""
import time


class Pomodoro:
    IDLE = "idle"
    FOCUS = "focus"
    BREAK = "break"

    def __init__(self, enabled=False, focus_minutes=25, break_minutes=5):
        self.enabled = bool(enabled)
        self.focus_seconds = float(focus_minutes) * 60.0
        self.break_seconds = float(break_minutes) * 60.0
        self.state = self.IDLE
        self.remaining = 0.0
        self.on_state_change = None  # 回调 fn(state)

    def start(self):
        if not self.enabled or self.state != self.IDLE:
            return
        self.state = self.FOCUS
        self.remaining = self.focus_seconds
        self._notify()

    def tick(self, dt=1.0):
        if not self.enabled or self.state == self.IDLE:
            return
        self.remaining -= dt
        if self.remaining <= 0.0:
            if self.state == self.FOCUS:
                self.state = self.BREAK
                self.remaining = self.break_seconds
            else:
                self.state = self.FOCUS
                self.remaining = self.focus_seconds
            self._notify()

    def is_break(self):
        """休息窗口内为 True（阻断解除）。"""
        return self.enabled and self.state == self.BREAK

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        if not self.enabled:
            self.state = self.IDLE

    def _notify(self):
        if self.on_state_change:
            try:
                self.on_state_change(self.state)
            except Exception:
                pass

    @property
    def minutes_left(self):
        return max(0, int(self.remaining // 60))