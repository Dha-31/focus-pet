"""ui/tray.py：系统托盘图标（v3.5，ctypes 实现，零第三方依赖）。

- 生成一枚程序化小猫图标（ICO，纯 Python 画图，不依赖 PIL）
- 用 Shell_NotifyIconW 放进系统托盘
- 左键双击：显示/隐藏桌宠
- 右键菜单：开始学习 / 结束学习 / 显示或隐藏 / 退出

说明：依赖 Tk 主循环在 Windows 上的消息泵，消息窗口与桌宠同线程即可收到消息。
任何一步失败都静默降级（桌宠照常运行，只是没有托盘）。
"""
import ctypes
import os
import struct
import sys
from ctypes import wintypes

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_PATH = os.path.join(PROJECT_ROOT, "data", "pet_icon.ico")

WM_APP = 0x8000
WM_DESTROY = 0x0002
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B

NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 0x0001
NIF_ICON = 0x0002
NIF_TIP = 0x0004

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
MF_STRING = 0x0000
MF_SEPARATOR = 0x0800
TPM_RIGHTBUTTON = 0x0002
TPM_NONOTIFY = 0x0080
TPM_RETURNCMD = 0x0100

ID_TRAY = 1
MENU_START = 1001
MENU_END = 1002
MENU_TOGGLE = 1003
MENU_QUIT = 1004

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


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


def _make_icon_bytes(size=32):
    """程序化画一只小猫头，返回 ICO 文件字节（BGRA 无压缩）。"""
    w = h = size
    cx = cy = size // 2
    r = size * 0.38
    body = (255, 178, 107, 255)     # #ffb26b
    ear = (232, 138, 60, 255)       # #e88a3c
    eye = (74, 55, 40, 255)         # #4a3728
    nose = (232, 80, 80, 255)
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            in_ear = ((x < cx - r * 0.3 and y < cy - r * 0.4
                       and (cy - r * 0.4 - y) > abs(x - (cx - r * 0.55)) * 1.4)
                      or (x > cx + r * 0.3 and y < cy - r * 0.4
                          and (cy - r * 0.4 - y) > abs(x - (cx + r * 0.55)) * 1.4))
            dx = x - cx
            dy = y - cy
            in_head = dx * dx + dy * dy <= r * r
            color = body if in_head else (ear if in_ear else (0, 0, 0, 0))
            if color[3]:
                for ex in (-r * 0.32, r * 0.32):
                    edx = x - (cx + ex)
                    edy = y - (cy + r * 0.05)
                    if edx * edx + edy * edy <= (r * 0.12) ** 2:
                        color = eye
                if (x - cx) ** 2 + (y - (cy + r * 0.35)) ** 2 <= (r * 0.09) ** 2:
                    color = nose
            row.append((color[2], color[1], color[0], color[3]))
        pixels.append(row)

    xor = bytearray()
    for y in range(h - 1, -1, -1):        # 自底向上
        for x in range(w):
            b, g, rr, a = pixels[y][x]
            xor += bytes((b, g, rr, a))
    and_row = ((w + 31) // 32) * 4
    and_mask = bytearray(and_row * h)
    bih = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, len(xor), 0, 0, 0, 0)
    data = bih + bytes(xor) + bytes(and_mask)
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", w if w < 256 else 0, h if h < 256 else 0,
                        0, 0, 1, 32, len(data), 22)
    return header + entry + data


def _ensure_icon():
    if os.path.exists(ICON_PATH):
        return ICON_PATH
    try:
        os.makedirs(os.path.dirname(ICON_PATH), exist_ok=True)
        with open(ICON_PATH, "wb") as f:
            f.write(_make_icon_bytes())
        return ICON_PATH
    except Exception:
        return None


class TrayIcon:
    """系统托盘图标。创建失败时 is_ok() 为 False，桌宠照常运行。"""

    def __init__(self, tooltip="Focus Pet", on_start=None, on_end=None,
                 on_toggle=None, on_quit=None):
        self.tooltip = tooltip
        self.on_start = on_start
        self.on_end = on_end
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self._hwnd = None
        self._nid = None
        self._wndproc = None
        self._class_atom = None
        self._ok = False
        self._init()

    def _init(self):
        if sys.platform != "win32":
            return
        try:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            kernel32 = ctypes.windll.kernel32
            hinst = kernel32.GetModuleHandleW(None)
            class_name = "FocusPetTrayWnd"

            # ---- 显式声明函数签名（否则宽字符串会被当成 ANSI 传，静默失败） ----
            WNDPROC_PTR = ctypes.POINTER(WNDCLASSEXW)
            user32.RegisterClassExW.argtypes = [WNDPROC_PTR]
            user32.RegisterClassExW.restype = ctypes.c_ushort
            user32.CreateWindowExW.restype = wintypes.HWND
            user32.DefWindowProcW.restype = ctypes.c_longlong
            user32.LoadImageW.restype = wintypes.HANDLE
            shell32.Shell_NotifyIconW.restype = wintypes.BOOL
            user32.TrackPopupMenu.restype = wintypes.UINT
            user32.CreateWindowExW.argtypes = [
                wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
            user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                              wintypes.WPARAM, wintypes.LPARAM]
            user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR,
                                          wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                          wintypes.UINT]
            shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD,
                                                 ctypes.POINTER(NOTIFYICONDATAW)]
            user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT,
                                           ctypes.c_size_t, wintypes.LPCWSTR]
            user32.AppendMenuW.restype = wintypes.BOOL
            user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT,
                                              ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                              wintypes.HWND, wintypes.LPVOID]
            user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
            user32.GetCursorPos.restype = wintypes.BOOL

            def wndproc(hwnd, msg, wparam, lparam):
                if msg == WM_APP + 1:
                    return self._on_tray_message(lparam & 0xFFFF)
                if msg == WM_DESTROY:
                    return 0
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            self._wndproc = WNDPROC(wndproc)

            classdef = WNDCLASSEXW()
            classdef.cbSize = ctypes.sizeof(classdef)
            classdef.style = 0
            classdef.lpfnWndProc = self._wndproc
            classdef.hInstance = hinst
            classdef.lpszClassName = class_name
            self._class_atom = user32.RegisterClassExW(ctypes.byref(classdef))
            if not self._class_atom:
                return
            HWND_MESSAGE = wintypes.HWND(-3)
            self._hwnd = user32.CreateWindowExW(
                0, class_name, "FocusPetTray", 0, 0, 0, 0, 0,
                HWND_MESSAGE, None, hinst, None)
            if not self._hwnd:
                return

            icon_path = _ensure_icon()
            if not icon_path:
                return
            hicon = user32.LoadImageW(
                None, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
            if not hicon:
                return

            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(nid)
            nid.hWnd = self._hwnd
            nid.uID = ID_TRAY
            nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            nid.uCallbackMessage = WM_APP + 1
            nid.hIcon = hicon
            nid.szTip = self.tooltip[:127]
            self._nid = nid
            if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid)):
                return
            self._ok = True
        except Exception as exc:
            print("[tray] 托盘创建失败（不影响桌宠）:", exc)
            self._ok = False

    def _on_tray_message(self, event):
        try:
            if event == WM_LBUTTONDBLCLK:
                if self.on_toggle:
                    self.on_toggle()
                return 0
            if event in (WM_RBUTTONUP, WM_CONTEXTMENU):
                self._popup_menu()
                return 0
        except Exception:
            pass
        return 0

    def _popup_menu(self):
        if not self._ok:
            return
        try:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            hmenu = user32.CreatePopupMenu()
            items = [
                (MENU_START, "开始学习…"),
                (MENU_END, "结束学习"),
                (MENU_TOGGLE, "显示 / 隐藏桌宠"),
                (0, None),                      # 分隔线
                (MENU_QUIT, "退出"),
            ]
            for mid, label in items:
                if mid == 0:
                    user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
                else:
                    user32.AppendMenuW(hmenu, MF_STRING, mid, label)
            pt = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            cmd = user32.TrackPopupMenu(
                hmenu, TPM_RIGHTBUTTON | TPM_RETURNCMD | TPM_NONOTIFY,
                pt.x, pt.y, 0, self._hwnd, None)
            user32.DestroyMenu(hmenu)
            if cmd == MENU_START and self.on_start:
                self.on_start()
            elif cmd == MENU_END and self.on_end:
                self.on_end()
            elif cmd == MENU_TOGGLE and self.on_toggle:
                self.on_toggle()
            elif cmd == MENU_QUIT and self.on_quit:
                self.on_quit()
        except Exception:
            pass

    def set_tooltip(self, text):
        if not self._ok or not self._nid:
            return
        try:
            self._nid.uFlags = NIF_TIP
            self._nid.szTip = text[:127]
            ctypes.windll.shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))
        except Exception:
            pass

    def destroy(self):
        if not self._ok:
            return
        try:
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            if self._nid is not None:
                ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._nid))
            if self._hwnd:
                user32.DestroyWindow(self._hwnd)
            if self._class_atom:
                user32.UnregisterClassW("FocusPetTrayWnd",
                                        ctypes.windll.kernel32.GetModuleHandleW(None))
        except Exception:
            pass
        self._ok = False

    def is_ok(self):
        return self._ok





