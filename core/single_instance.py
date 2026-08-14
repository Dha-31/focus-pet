"""core/single_instance.py：单实例锁（v3.5）。

Windows 用命名互斥量（CreateMutexW），防止开两个桌宠互相打架；
其他平台退回"端口/锁文件"不可用时直接放行（桌面端以 Windows 为主）。
"""
import sys

_handle = None
_LOCK_NAME = "FocusPet_Instance_Lock_v35"


def acquire():
    """尝试获取单实例锁。成功返回 True；已有实例在运行返回 False。"""
    global _handle
    if sys.platform != "win32":
        return True  # 非 Windows 暂不强制
    try:
        import ctypes
        from ctypes import wintypes
        handle = ctypes.windll.kernel32.CreateMutexW(None, False, _LOCK_NAME)
        if not handle:
            return True  # 拿不到句柄也不阻塞（保守）
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.kernel32.CloseHandle(handle)
            return False
        _handle = handle  # 保持句柄，进程存活期间锁有效
        return True
    except Exception:
        return True


def release():
    global _handle
    if _handle:
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_handle)
        except Exception:
            pass
        _handle = None
