"""core/hotkeys.py：全局快捷键（v3.6，ctypes RegisterHotKey，零依赖）。

- 独立的消息窗口接收 WM_HOTKEY（Tk 主循环会泵线程消息，回调在主线程执行）
- register(modifiers, vk, callback)：注册一个热键；重复/被占用自动跳过
- destroy()：统一注销

默认热键（main.py 里注册）：
  Ctrl+Alt+S 开始/结束学习     Ctrl+Alt+H 显示/隐藏桌宠     Ctrl+Alt+M 迷你模式
"""
import ctypes
import sys
from ctypes import wintypes

WM_HOTKEY = 0x0312
WM_DESTROY = 0x0002

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
                             wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HANDLE),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class HotkeyManager:
    """全局快捷键管理器。创建失败时 is_ok() 为 False，桌宠照常运行。"""

    def __init__(self):
        self._hwnd = None
        self._wndproc = None
        self._class_atom = None
        self._callbacks = {}     # hotkey id -> callback
        self._next_id = 100
        self._ok = False
        self._init()

    def _init(self):
        if sys.platform != "win32":
            return
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            hinst = kernel32.GetModuleHandleW(None)
            class_name = "FocusPetHotkeyWnd"

            def wndproc(hwnd, msg, wparam, lparam):
                if msg == WM_HOTKEY:
                    cb = self._callbacks.get(wparam)
                    if cb:
                        try:
                            cb()
                        except Exception:
                            pass
                    return 0
                if msg == WM_DESTROY:
                    return 0
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            self._wndproc = WNDPROC(wndproc)
            user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                              wintypes.WPARAM, wintypes.LPARAM]
            user32.DefWindowProcW.restype = ctypes.c_longlong
            user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
            user32.RegisterClassExW.restype = ctypes.c_ushort
            user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int,
                                              wintypes.UINT, wintypes.UINT]
            user32.RegisterHotKey.restype = wintypes.BOOL

            classdef = WNDCLASSEXW()
            classdef.cbSize = ctypes.sizeof(classdef)
            classdef.lpfnWndProc = self._wndproc
            classdef.hInstance = hinst
            classdef.lpszClassName = class_name
            self._class_atom = user32.RegisterClassExW(ctypes.byref(classdef))
            if not self._class_atom:
                return
            HWND_MESSAGE = wintypes.HWND(-3)
            user32.CreateWindowExW.argtypes = [
                wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
            user32.CreateWindowExW.restype = wintypes.HWND
            self._hwnd = user32.CreateWindowExW(
                0, class_name, "FocusPetHotkey", 0, 0, 0, 0, 0,
                HWND_MESSAGE, None, hinst, None)
            if not self._hwnd:
                return
            self._ok = True
        except Exception as exc:
            print("[hotkeys] 快捷键初始化失败（不影响桌宠）:", exc)
            self._ok = False

    def register(self, modifiers, vk, callback):
        if not self._ok:
            return False
        try:
            hid = self._next_id
            self._next_id += 1
            if ctypes.windll.user32.RegisterHotKey(self._hwnd, hid, modifiers, vk):
                self._callbacks[hid] = callback
                return True
            return False
        except Exception:
            return False

    def is_ok(self):
        return self._ok

    def destroy(self):
        if not self._ok:
            return
        try:
            user32 = ctypes.windll.user32
            for hid in list(self._callbacks):
                user32.UnregisterHotKey(self._hwnd, hid)
            self._callbacks.clear()
            if self._hwnd:
                user32.DestroyWindow(self._hwnd)
            if self._class_atom:
                user32.UnregisterClassW("FocusPetHotkeyWnd",
                                        ctypes.windll.kernel32.GetModuleHandleW(None))
        except Exception:
            pass
        self._ok = False
