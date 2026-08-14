"""core/focus_assist.py：Windows 专注助手（Focus Assist）控制（v3.7.1）。

专注模式下自动开启 Windows「专注助手」，屏蔽所有应用通知
（微信/QQ/浏览器等弹通知、任务栏图标闪烁、声音提示），
结束后恢复用户原来的设置。

实现：读写 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\QuietHours
  Enabled = 1（开启） / 0（关闭）
  Profile = 0（仅优先事项） / 1（仅闹钟）   —— 学习时用"仅闹钟"最安静

任何一步失败都静默：通知屏蔽是"尽力而为"，不阻塞桌宠。
"""
import ctypes
import sys
from ctypes import wintypes

KEY = r"Software\Microsoft\Windows\CurrentVersion\QuietHours"
HKCU = 0x80000001
KEY_READ = 0x20019
KEY_WRITE = 0x20006
REG_DWORD = 4

_prev = {"enabled": None, "profile": None}


def _read_dword(name):
    if sys.platform != "win32":
        return None
    try:
        advapi32 = ctypes.windll.advapi32
        hkey = wintypes.HKEY()
        if advapi32.RegOpenKeyExW(HKCU, KEY, 0, KEY_READ, ctypes.byref(hkey)) != 0:
            return None
        try:
            size = wintypes.DWORD(4)
            data = wintypes.DWORD(0)
            r = advapi32.RegQueryValueExW(hkey, name, None, None,
                                          ctypes.byref(data), ctypes.byref(size))
            if r == 0 and size.value == 4:
                return int(data.value)
            return None
        finally:
            advapi32.RegCloseKey(hkey)
    except Exception:
        return None


def _write_dword(name, value):
    if sys.platform != "win32":
        return False
    try:
        advapi32 = ctypes.windll.advapi32
        hkey = wintypes.HKEY()
        if advapi32.RegCreateKeyExW(HKCU, KEY, 0, None, 0, KEY_WRITE, None,
                                    ctypes.byref(hkey), None) != 0:
            return False
        try:
            data = wintypes.DWORD(int(value))
            advapi32.RegSetValueExW(hkey, name, 0, REG_DWORD,
                                    ctypes.byref(data), ctypes.sizeof(data))
            return True
        finally:
            advapi32.RegCloseKey(hkey)
    except Exception:
        return False


def is_enabled():
    return _read_dword("Enabled") == 1


def enable():
    """开启专注助手（仅闹钟）。记录原值以便 restore。"""
    global _prev
    try:
        _prev["enabled"] = _read_dword("Enabled")
        _prev["profile"] = _read_dword("Profile")
        _write_dword("Enabled", 1)
        _write_dword("Profile", 1)   # 仅闹钟：最安静
    except Exception:
        pass


def restore():
    """恢复专注助手到原状态（没有原记录则关闭）。"""
    global _prev
    try:
        if _prev["enabled"] is not None:
            _write_dword("Enabled", _prev["enabled"])
        else:
            _write_dword("Enabled", 0)
        if _prev["profile"] is not None:
            _write_dword("Profile", _prev["profile"])
        _prev = {"enabled": None, "profile": None}
    except Exception:
        pass
