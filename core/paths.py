"""core/paths.py：路径统一（v3.7.1）。

- 源码运行：数据/皮肤就在项目目录（与以前一致）
- 打包客户端：数据/皮肤放到 %LOCALAPPDATA%\\FocusPet（稳定位置），
  更新客户端不会丢用户的皮肤/配置/日志；首次运行自动从包内补齐默认文件
"""
import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_copied = False


def frozen():
    return bool(getattr(sys, "frozen", False))


def user_data_dir():
    """返回用户可写的数据根目录（皮肤/配置/日志放这里）。"""
    global _copied
    if not frozen():
        return PROJECT_ROOT
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "FocusPet")
    os.makedirs(d, exist_ok=True)
    if not _copied:
        _copied = True
        bundle = getattr(sys, "_MEIPASS", None)
        if bundle:
            for sub in ("data", "skins"):
                src = os.path.join(bundle, sub)
                dst = os.path.join(d, sub)
                if not os.path.isdir(src):
                    continue
                os.makedirs(dst, exist_ok=True)
                for item in os.listdir(src):
                    sp = os.path.join(src, item)
                    dp = os.path.join(dst, item)
                    try:
                        if os.path.isdir(sp) and not os.path.exists(dp):
                            shutil.copytree(sp, dp)
                        elif os.path.isfile(sp) and not os.path.exists(dp):
                            shutil.copy2(sp, dp)
                    except Exception:
                        pass
    return d
