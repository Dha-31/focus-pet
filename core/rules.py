"""判定规则：黑名单为主 + 白名单特例 + 教宠物学习。

分类结果：
- "study"       学习类（放行，计专注时长）
- "tool"        工具类（默认放行，不计专注）
- "distraction" 分心类（黑名单命中，触发阻断）
- "unknown"     无法判定（保守放行，不计专注；v1.5 之后由截图分析补判）

优先级：白名单特例 / 教宠物学习 > 黑名单 > 学习关键词 > 工具进程 > unknown

热更新：blacklist/whitelist/learned 三个 json 文件被修改后，下次
classify() 会自动重新加载，无需重启桌宠。
"""
import json
import os

from .config import DATA_DIR

# 出现在窗口标题里就认为是学习内容的关键词（保守、可自行扩充）
STUDY_KEYWORDS = [
    "pdf", "word", "excel", "powerpoint", "ppt", "docx", "xlsx",
    "onenote", "notion", "obsidian", "typora",
    "vscode", "visual studio", "pycharm", "intellij", "android studio",
    "code", "jupyter", "colab", "leetcode", "github", "stack overflow",
    "课件", "讲义", "笔记", "作业", "课本", "课程", "试卷",
]

# 默认视为工具类、不拦也不计专注的进程
TOOL_PROCESSES = ["explorer.exe", "taskmgr.exe"]


class RuleEngine:
    _FILES = ("blacklist.json", "whitelist.json", "learned.json")

    def __init__(self):
        self._mtimes = {}
        self._data = {}
        self.blacklist = {}
        self.whitelist = {}
        self.learned = {}
        self._refresh(force=True)

    # ---------- 加载与热更新 ----------
    def _refresh(self, force=False):
        for name in self._FILES:
            path = os.path.join(DATA_DIR, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                mtime = 0
            if force or self._mtimes.get(name) != mtime:
                data = {"urls": [], "processes": [], "titles": []}
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8-sig") as f:
                            loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data.update(loaded)
                    except (json.JSONDecodeError, OSError):
                        pass
                self._data[name] = data
                self._mtimes[name] = mtime
        self.blacklist = self._data["blacklist.json"]
        self.whitelist = self._data["whitelist.json"]
        self.learned = self._data["learned.json"]

    # ---------- 匹配 ----------
    @staticmethod
    def _match(patterns, text):
        """子串匹配（不区分大小写）。空模式忽略。"""
        if not text:
            return False
        lower = text.lower()
        for pattern in patterns or []:
            p = (pattern or "").strip().lower()
            if p and p in lower:
                return True
        return False

    def _is_whitelisted(self, title, process, url):
        if url and self._match(self.whitelist["urls"], url):
            return True
        if self._match(self.whitelist["processes"], process):
            return True
        if self._match(self.whitelist["titles"], title):
            return True
        # 教宠物学习到的内容 = 隐式白名单
        if url and self._match(self.learned["urls"], url):
            return True
        if self._match(self.learned["processes"], process):
            return True
        if self._match(self.learned["titles"], title):
            return True
        return False

    def _is_blacklisted(self, title, process, url):
        if url and self._match(self.blacklist["urls"], url):
            return True
        if self._match(self.blacklist["processes"], process):
            return True
        if self._match(self.blacklist["titles"], title):
            return True
        return False

    # ---------- 判定 ----------
    def classify(self, title="", process="", url=None):
        """返回 study / tool / distraction / unknown 之一。"""
        self._refresh()
        if self._is_whitelisted(title, process, url):
            return "study"
        if self._is_blacklisted(title, process, url):
            return "distraction"
        if self._match(STUDY_KEYWORDS, title) or self._match(STUDY_KEYWORDS, process):
            return "study"
        if (process or "").lower() in [p.lower() for p in TOOL_PROCESSES]:
            return "tool"
        return "unknown"

    # ---------- 教宠物 ----------
    def learn(self, title="", process="", url=None):
        """教宠物：把当前内容记为学习用（持久化到 learned.json）。"""
        self._refresh()
        changed = False
        if url:
            self.learned["urls"].append(url)
            changed = True
        if process:
            self.learned["processes"].append(process)
            changed = True
        if title:
            self.learned["titles"].append(title)
            changed = True
        if changed:
            path = os.path.join(DATA_DIR, "learned.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.learned, f, ensure_ascii=False, indent=2)
            self._mtimes["learned.json"] = os.path.getmtime(path)
        return changed