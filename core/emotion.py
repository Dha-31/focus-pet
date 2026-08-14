"""情绪温度计：由连续分心时长决定阻断级别；愤怒值决定表情。

- 分心时：streak 累加，愤怒值上升
- 学习时：streak 归零，愤怒值缓慢下降（逐渐消气，不瞬间原谅）
- 阻断级别 tier：0..4，由 streak 对照 tiers_seconds 得出
  （默认 5 秒→Lv1 提醒 / 15 秒→Lv2 遮挡 / 30 秒→Lv3 最小化 / 60 秒→Lv4 强制关闭）
- mood：0..4，用于桌宠表情（开心/好奇/不耐烦/生气/暴怒）
"""


class EmotionMeter:
    def __init__(self, tier_seconds=(5, 15, 30, 60)):
        self.tier_seconds = list(tier_seconds)
        self.streak = 0.0
        self.anger = 0.0
        self.current_tier = 0

    def update(self, is_distraction, dt=1.0):
        """每轮监督调用一次。返回当前阻断级别。"""
        if is_distraction:
            self.streak += dt
            self.anger = min(100.0, self.anger + 3.0 * dt)
        else:
            self.streak = 0.0
            self.anger = max(0.0, self.anger - 1.0 * dt)
        self.current_tier = self._tier_from_streak()
        return self.current_tier

    def _tier_from_streak(self):
        for i, threshold in enumerate(self.tier_seconds):
            if self.streak < threshold:
                return i
        return len(self.tier_seconds)

    @property
    def mood(self):
        if self.anger < 30:
            return 0
        if self.anger < 50:
            return 1
        if self.anger < 70:
            return 2
        if self.anger < 85:
            return 3
        return 4

    def reset(self):
        self.streak = 0.0
        self.anger = 0.0
        self.current_tier = 0