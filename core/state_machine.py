"""core/state_machine.py：事件→状态→动画 状态机（v3.5）。

借鉴 clawd-on-desk 的"事件→状态→动画"三层映射设计（AGPL，仅借鉴思路，独立实现）。

- 情绪状态：由情绪温度计 mood 0..4 映射
    happy / curious / annoyed / angry / furious
- 瞬时状态：celebrate（完成/成就）、error（出错），播完自动回到情绪状态
- 持续状态：sleep（人不在/睡觉），可随时开关

每个状态对应主题资源包里的一张图（见 core/theme.py）；没有图就用程序化小猫。
"""
import time

# 情绪 mood(0..4) -> 状态名
MOOD_TO_STATE = ["happy", "curious", "annoyed", "angry", "furious"]
# 瞬时状态（自动过期）
TRANSIENT_STATES = {"celebrate", "error"}


class PetStateMachine:
    def __init__(self):
        self.mood = 0
        self.sleeping = False
        self._transient = None  # (state, until_ts)

    def set_mood(self, mood):
        mood = int(max(0, min(4, mood)))
        self.mood = mood
        # 情绪更新不打断瞬时状态（动画播完自然回到新情绪）
        if self._transient and time.time() >= self._transient[1]:
            self._transient = None

    def set_sleeping(self, on):
        self.sleeping = bool(on)

    def play(self, state, seconds=3.0):
        """播放瞬时状态（celebrate/error），可打断正在播的。"""
        if state not in TRANSIENT_STATES:
            return
        self._transient = (state, time.time() + max(0.5, seconds))

    def current(self, now=None):
        now = time.time() if now is None else now
        if self._transient:
            if now < self._transient[1]:
                return self._transient[0]
            self._transient = None
        if self.sleeping:
            return "sleep"
        return MOOD_TO_STATE[self.mood]

    @property
    def is_transient(self):
        return bool(self._transient) and time.time() < self._transient[1]
