"""core/dev.py：开发者模式判定。

打包成 exe（用户版）时自动隐藏开发者功能（集中配置编辑器等）；
源码运行（开发）时保留。做客户端时无需再手动删，打包即生效。
"""
import sys


def is_dev_mode():
    """开发模式 = True（源码运行）；用户版 exe = False。"""
    return not getattr(sys, "frozen", False)
