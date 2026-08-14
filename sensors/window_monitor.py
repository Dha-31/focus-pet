"""活动窗口检测：标题 + 进程名（ctypes，Windows 专用）。

v1 说明：只读窗口标题和进程名，不截图。浏览器具体标签页 URL 需要
浏览器扩展配合（v1.5），届时 url 参数由扩展回填。

2026-08-14 修复记录：
- 给全部 WinAPI 显式声明 argtypes/restype，避免 64 位句柄截断
- QueryFullProcessImageNameW 改从 kernel32.dll 调用（psapi.dll 在部分
  Python 3.14 环境找不到该导出，kernel32 保证存在）
- 失败降级返回部分信息，不阻塞监督循环；打印节流避免刷屏
"""
import ctypes
import os
from ctypes import wintypes

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
WM_CLOSE = 0x0010
SW_MINIMIZE = 6
MAX_TITLE_LEN = 32767


def available():
    """是否 Windows 平台（其他平台返回 False，便于跨平台测试）。"""
    return os.name == "nt"


# ---------- WinAPI 声明（64 位下避免句柄截断的关键） ----------
_api = None


def _api_loaded():
    global _api
    if _api is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        HWND = wintypes.HWND
        DWORD = wintypes.DWORD
        BOOL = wintypes.BOOL
        HANDLE = wintypes.HANDLE
        LPWSTR = wintypes.LPWSTR
        LPDWORD = ctypes.POINTER(DWORD)

        user32.GetForegroundWindow.restype = HWND
        user32.GetWindowTextLengthW.argtypes = [HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [HWND, LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetWindowThreadProcessId.argtypes = [HWND, LPDWORD]
        user32.GetWindowThreadProcessId.restype = DWORD
        user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
        user32.ShowWindow.restype = BOOL
        user32.PostMessageW.argtypes = [HWND, wintypes.UINT,
                                        wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW.restype = BOOL

        kernel32.OpenProcess.argtypes = [DWORD, BOOL, DWORD]
        kernel32.OpenProcess.restype = HANDLE
        kernel32.CloseHandle.argtypes = [HANDLE]
        kernel32.CloseHandle.restype = BOOL
        kernel32.QueryFullProcessImageNameW.argtypes = [HANDLE, DWORD, LPWSTR, LPDWORD]
        kernel32.QueryFullProcessImageNameW.restype = BOOL

        _api = (user32, kernel32)
    return _api


# ---------- 各步骤独立容错 ----------
def _get_window_text(user32, hwnd):
    try:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0 or length > MAX_TITLE_LEN:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value or ""
    except Exception:
        return ""


def _get_process_name(kernel32, pid):
    try:
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                name = buf.value or ""
                return name.split("\\")[-1]
            return ""
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        return ""


_error_count = 0
_last_printed = 0


def get_foreground_info():
    """返回当前前台窗口信息 dict，失败返回 None。

    {"hwnd": int, "title": str, "process": str, "pid": int}
    进程名拿不到时返回空字符串（降级为"未知"放行），不影响整体运行。
    """
    global _error_count, _last_printed
    if not available():
        return None
    try:
        user32, kernel32 = _api_loaded()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        title = _get_window_text(user32, hwnd)
        process = _get_process_name(kernel32, pid.value)
        return {
            "hwnd": int(hwnd),
            "title": title,
            "process": process,
            "pid": int(pid.value),
        }
    except Exception as exc:
        # 节流：第一次和每 30 次失败各打印一次，避免刷屏
        _error_count += 1
        if _error_count == 1 or (_error_count - _last_printed) >= 30:
            _last_printed = _error_count
            print("[window_monitor] 获取前台窗口失败：", exc)
        return None


def minimize_window(hwnd):
    """把窗口最小化（Lv3 阻断用）。"""
    if not available() or not hwnd:
        return False
    try:
        user32, _ = _api_loaded()
        return bool(user32.ShowWindow(hwnd, SW_MINIMIZE))
    except Exception:
        return False


def post_close(hwnd):
    """向窗口发送 WM_CLOSE（Lv4 阻断用，比杀进程温和，给用户保存机会）。"""
    if not available() or not hwnd:
        return False
    try:
        user32, _ = _api_loaded()
        return bool(user32.PostMessageW(hwnd, WM_CLOSE, 0, 0))
    except Exception:
        return False