"""配置加载与保存：data/config.json 为基础，用户改动优先。"""
import copy
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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