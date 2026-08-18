"""tools/build_exe.py：打包 Windows 客户端（PyInstaller）。

用法：
  python tools/build_exe.py          # 精简版（默认）：保留 rapidocr 屏幕分析，排除 mediapipe/cv2/sklearn/scipy/rembg（上传图片人脸自适配降级）
  python tools/build_exe.py --full   # 完整版：全部依赖都包含（体积大）

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
        "--windowed",   # 最终用户版无黑色控制台（开发调试请用 python main.py）
        "--name", "FocusPet",
        "--icon", os.path.join(PROJECT_ROOT, "data", "pet_icon.ico"),
        # 数据目录（运行时读写：皮肤/配置/日志/文档/扩展）
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'data')}{os.pathsep}data",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'skins')}{os.pathsep}skins",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'docs')}{os.pathsep}docs",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'browser_extension')}{os.pathsep}browser_extension",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'models')}{os.pathsep}models",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'release')}{os.pathsep}release",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'desktop')}{os.pathsep}desktop",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'ui', 'web_pet')}{os.pathsep}ui/web_pet",
        "--add-data", f"{os.path.join(PROJECT_ROOT, 'tools', 'electron', 'runtime')}{os.pathsep}tools/electron/runtime",
    ]
    import importlib.util as _iu
    if not full:
        # 精简版：排除重型/已删除功能依赖（摄像头 mediapipe/cv2、ML 训练 sklearn/scipy、AI 抠图 rembg）
        # 保留 rapidocr_onnxruntime（屏幕分析 OCR）；joblib 自动识别打包
        for mod in ("mediapipe", "cv2", "sklearn", "scipy", "rembg"):
            cmd += ["--exclude-module", mod]
        try:
            if _iu.find_spec("rapidocr_onnxruntime"):
                cmd += ["--collect-all", "rapidocr_onnxruntime"]
                print("[build] 已包含 rapidocr_onnxruntime（屏幕分析 OCR）")
        except Exception:
            pass
    else:
        # 完整版：mediapipe/rapidocr 没有官方 PyInstaller hook，需显式收集
        for mod in ("rapidocr_onnxruntime",):
            try:
                if _iu.find_spec(mod):
                    cmd += ["--collect-all", mod]
                    print(f"[build] 已包含 {mod}（完整版）")
            except Exception:
                pass
    # 动态导入的工具模块（PyInstaller 可能漏）
    cmd += ["--hidden-import", "tools.make_skin", "--hidden-import", "tools.theme_scaffold",
            "--hidden-import", "tools.validate_theme", "--hidden-import", "ui.rules_window"]
    # AI 抠图（rembg）：仅完整版包含（体积大但效果好）
    if full:
        try:
            import importlib.util
            if importlib.util.find_spec("rembg"):
                cmd += ["--collect-all", "rembg"]
                print("[build] 已包含 rembg（AI 抠图，首次使用需联网下载模型）")
        except Exception:
            pass
    cmd.append(os.path.join(PROJECT_ROOT, "main.py"))

    print("构建命令:", " ".join(cmd[:8]), "...")
    print("模式:", "完整版（全部依赖）" if full else "精简版（保留屏幕分析，排除重型依赖）")
    r = subprocess.run(cmd, cwd=PROJECT_ROOT)
    print("构建结束，退出码:", r.returncode)
    exe = os.path.join(PROJECT_ROOT, "dist", "FocusPet", "FocusPet.exe")
    if os.path.exists(exe):
        size = os.path.getsize(exe) / 1024 / 1024
        print(f"✅ 客户端已生成: {exe}（{size:.1f} MB）")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
