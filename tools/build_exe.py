"""tools/build_exe.py：打包 Windows 客户端（PyInstaller）。

用法：
  python tools/build_exe.py          # 体验版：排除重型 AI（摄像头/截图分析降级提示）
  python tools/build_exe.py --full   # 完整版：包含摄像头/截图分析（体积大、易踩坑）

产物：dist/FocusPet/FocusPet.exe（onedir，双击即用，无需 Python）
"""
import io
import os
import subprocess
import sys

# 控制台可能是 GBK，打印 emoji 会崩；统一 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    full = "--full" in sys.argv
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", "FocusPet",
        "--icon", os.path.join(PROJECT_ROOT, "data", "pet_icon.ico"),
        # 数据目录（运行时读写：皮肤/配置/日志/文档/扩展）
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'data')}{os.pathsep}data",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'skins')}{os.pathsep}skins",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'docs')}{os.pathsep}docs",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'browser_extension')}{os.pathsep}browser_extension",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'models')}{os.pathsep}models",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'release')}{os.pathsep}release",
    ]
    if not full:
        # 体验版：排除重型 AI 依赖（它们打包易失败、体积巨大；代码已优雅降级）
        for mod in ("mediapipe", "cv2", "rapidocr_onnxruntime", "sklearn", "scipy"):
            cmd += ["--exclude-module", mod]
    # 动态导入的工具模块（PyInstaller 可能漏）
    cmd += ["--hidden-import", "tools.make_skin", "--hidden-import", "tools.theme_scaffold",
            "--hidden-import", "tools.validate_theme"]
    cmd.append(os.path.join(PROJECT_ROOT, "main.py"))

    print("构建命令:", " ".join(cmd[:8]), "...")
    print("模式:", "完整版" if full else "体验版（无摄像头/截图分析，降级提示）")
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    print("构建结束，退出码:", r.returncode)
    exe = os.path.join(PROJECT_ROOT, "dist", "FocusPet", "FocusPet.exe")
    if os.path.exists(exe):
        size = os.path.getsize(exe) / 1024 / 1024
        print(f"✅ 客户端已生成: {exe}（{size:.1f} MB）")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
