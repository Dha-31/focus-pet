"""配置加载与保存：data/config.json 为基础，用户改动优先。"""
import copy
import json
import os

from . import paths as _paths
DATA_DIR = os.path.join(_paths.user_data_dir(), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULTS = {
    "pomodoro": {
        "enabled": False,
        "focus_minutes": 25,
        "break_minutes": 5,
    },
    "blocking": {
        "force_close_enabled": False,
        "save_warning_seconds": 10,
        "tiers_seconds": [5, 15, 30, 60],
        "custom_tiers": [5, 15, 30, 60],
    },
    "supervision": {
        "poll_interval_seconds": 1,
        "camera_enabled": False,
    },
    "lock": {
        "enabled": False,
        "exit_code": "1234",
    },
    "pet": {
        "skin": "default",
        "mini_mode": False,          # 迷你模式（v3.6）
    },
    "dnd": {
        "enabled": False,            # 免打扰：宠物闭嘴静音，监督照常（v3.6）
    },
    "sound": {
        "enabled": True,             # 提示音效开关（v3.6）
    },
    "hotkeys": {
        "enabled": True,             # 全局快捷键开关（v3.6）
    },
    "first_run": {
        "done": False,               # 首次启动帮助（v3.7）
    },
    "focus_assist": {
        "enabled": True,               # 学习时自动屏蔽系统通知（专注助手，v3.7.1）
    },
    "extension": {
        "enabled": False,
        "port": 18765,
    },
    "camera": {
        "enabled": False,
        "device_index": 0,
        "interval_seconds": 1,
    },
    "screen_analysis": {
        "enabled": True,
        "interval_seconds": 10,
    },
}


def _deep_merge(base, override):
    """把 override 递归合并进 base（base 会被就地修改）。"""
    for key, value in (override or {}).items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)


def load_config(path=CONFIG_PATH):
    """读取配置；缺失的字段用默认值补齐。"""
    cfg = copy.deepcopy(DEFAULTS)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                user_cfg = json.load(f)
            _deep_merge(cfg, user_cfg)
        except (json.JSONDecodeError, OSError) as exc:
            print("[config] 配置文件解析失败，使用默认值：", exc)
    return cfg


def save_config(cfg, path=CONFIG_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)