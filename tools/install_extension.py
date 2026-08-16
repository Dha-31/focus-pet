"""tools/install_extension.py：一键引导安装浏览器扩展（尽量少手动操作）。

自动：检测 Chrome/Edge -> 复制扩展目录到剪贴板 -> 打开扩展管理页。
用户只需：开开发者模式 -> 加载已解压 -> Ctrl+V 粘贴路径 -> 确定。

说明：浏览器禁止第三方程序静默安装扩展，上架商店后才能真正一键安装。
"""
import os
import webbrowser

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_DIR = os.path.join(PROJECT_ROOT, "browser_extension")


def _copy_to_clipboard(text):
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return True
    except Exception:
        return False


def _find_browser():
    candidates = [
        ("Chrome", "chrome://extensions/", [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]),
        ("Edge", "edge://extensions/", [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]),
    ]
    for name, url, paths in candidates:
        for p in paths:
            if os.path.exists(p):
                return name, url
    return None, None


def main():
    name, url = _find_browser()
    ok = _copy_to_clipboard(EXT_DIR)
    print("=" * 50)
    print("Focus Pet 浏览器扩展安装引导")
    print("=" * 50)
    print()
    print(f"扩展目录：{EXT_DIR}")
    if ok:
        print("✅ 已把扩展目录路径复制到剪贴板")
    else:
        print("请手动复制上面的扩展目录路径")
    print()
    if name:
        print(f"即将用 {name} 打开扩展管理页：{url}")
        webbrowser.open(url)
    else:
        print("未检测到 Chrome/Edge，请手动在浏览器打开扩展管理页：")
        print("  Chrome: chrome://extensions/")
        print("  Edge:   edge://extensions/")
    print()
    print("接下来只需 3 步：")
    print("  1. 打开右上角【开发者模式】开关")
    print("  2. 点击【加载已解压的扩展程序】")
    print("  3. 在路径框里 Ctrl+V 粘贴，点确定")
    print()
    print("加载后即可关闭本窗口；扩展会通过本地 127.0.0.1 与桌宠通信。")
    input("按回车退出...")


if __name__ == "__main__":
    main()
