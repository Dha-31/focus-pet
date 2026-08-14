"""core/settings.py：集中配置管理器（开发者参数）。

所有可调参数（汇率/价格/阈值/经验表/关键词…）统一存放在 data/settings.json。
- 热更新：文件被修改后，下一次 get() 自动重新加载（与规则引擎一致）
- get(path)：如 settings.get("economy.coin_per_minute")
- set(path, value)：写入并保存，全项目实时生效
- 编辑器（ui/settings_editor.py）改的就是这个文件
"""
import copy
import json
import os

from .config import DATA_DIR
from .settings_schema import DEFAULTS

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")


def _deep_merge(base, override):
    for key, value in (override or {}).items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)


class SettingsManager:
    def __init__(self):
        self._data = copy.deepcopy(DEFAULTS)
        self._mtime = 0
        self._load(force=True)

    def _load(self, force=False):
        if not os.path.exists(SETTINGS_PATH):
            return
        try:
            mtime = os.path.getmtime(SETTINGS_PATH)
        except OSError:
            mtime = 0
        if not force and mtime == self._mtime:
            return
        self._mtime = mtime
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
                user = json.load(f)
            merged = copy.deepcopy(DEFAULTS)
            _deep_merge(merged, user)
            self._data = merged
        except (json.JSONDecodeError, OSError):
            pass

    def refresh(self):
        self._load()

    def reload(self):
        """强制重新从磁盘加载（恢复默认/导入后调用）。"""
        self._load(force=True)

    def get_dict(self):
        """返回完整配置的深拷贝。"""
        self._load()
        return copy.deepcopy(self._data)

    def get(self, path, default=None):
        """按点分路径取值，如 'economy.coin_per_minute'。"""
        self._load()
        node = self._data
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, path, value):
        node = self._data
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = copy.deepcopy(value)
        self.save()

    def save(self):
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        try:
            self._mtime = os.path.getmtime(SETTINGS_PATH)
        except OSError:
            pass


# 全局单例
settings = SettingsManager()