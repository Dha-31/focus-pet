# -*- coding: utf-8 -*-
"""core/autostart.py：开机自启动（Windows 注册表 HKCU Run 键，无需管理员权限）。

使用：
  from core import autostart
  autostart.enable()        # 开启开机自启
  autostart.disable()       # 关闭
  autostart.is_enabled()    # 是否已开启
"""
import os
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FocusPet"


def _command():
    """当前程序的启动命令：打包后是 exe，开发时是 python + 脚本。"""
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    script = os.path.abspath(sys.argv[0] if (sys.argv and sys.argv[0]) else "main.py")
    return '"%s" "%s"' % (sys.executable, script)


def enable():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
        finally:
            winreg.CloseKey(key)
        return True
    except Exception:
        return False


def disable():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)
        return True
    except Exception:
        return False


def is_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return False
    except Exception:
        return False
