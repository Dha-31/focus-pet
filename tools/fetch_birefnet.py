"""tools/fetch_birefnet.py：预下载 AI 抠图模型（BiRefNet，约 300MB）。

客户端首次用"导入照片"AI 抠图时，rembg 会自动联网下载约 300MB 模型，
网慢会等很久、还容易被误以为卡死。提前运行本脚本把模型下好，
之后导入照片就能秒用：
  python tools/fetch_birefnet.py          # 下载 BiRefNet 高质量模型（推荐）
  python tools/fetch_birefnet.py --u2net  # 可选：下载默认 u2net 模型（约 170MB）

模型保存到 rembg 默认目录（U2NET_HOME 或 ~/.u2net），带进度条，可重复运行。
"""
import os
import sys
import urllib.request

BASE = "https://github.com/danielgatis/rembg/releases/download/v0.0.0"
MODELS = {
    "birefnet-general.onnx": f"{BASE}/birefnet-general.onnx",   # 高质量（推荐）
    "u2net.onnx": f"{BASE}/u2net.onnx",                          # 默认模型
}


def model_dir():
    return os.environ.get("U2NET_HOME") or os.path.join(os.path.expanduser("~"), ".u2net")


def model_ready(name="birefnet-general.onnx"):
    """模型已存在且大小合理（>1MB）即视为就绪。"""
    p = os.path.join(model_dir(), name)
    return os.path.exists(p) and os.path.getsize(p) > 1_000_000


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}TB"


def download(name, url):
    os.makedirs(model_dir(), exist_ok=True)
    dest = os.path.join(model_dir(), name)
    if model_ready(name):
        print(f"[ok] 已存在: {dest}（{human(os.path.getsize(dest))}）")
        return True
    part = dest + ".part"
    print(f"[download] {name}（约 300MB，网速慢请耐心等待）")
    print(f"          保存到: {dest}")

    def hook(block, blocksize, total):
        done = block * blocksize
        if total > 0:
            pct = min(100.0, done * 100.0 / total)
            bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
            print(f"\r    [{bar}] {pct:5.1f}%  {human(done)} / {human(total)}   ",
                  end="", flush=True)
        else:
            print(f"\r    … {human(done)}   ", end="", flush=True)

    for attempt in range(1, 4):
        try:
            urllib.request.urlretrieve(url, part, reporthook=hook)
            if not model_ready(name) and os.path.exists(part) and os.path.getsize(part) < 1_000_000:
                raise IOError("下载不完整")
            os.replace(part, dest)
            print(f"\n[ok] 完成: {dest}（{human(os.path.getsize(dest))}）")
            return True
        except Exception as exc:
            print(f"\n[!] 第 {attempt} 次下载失败: {exc}")
            if os.path.exists(part):
                try:
                    os.remove(part)
                except OSError:
                    pass
    print("[!] 下载失败：请检查网络后重试；也可以直接用 tools/make_skin.py --no-rembg（快速去底）")
    return False


def main():
    args = sys.argv[1:]
    names = ["u2net.onnx"] if "--u2net" in args else ["birefnet-general.onnx"]
    ok = True
    for name in names:
        ok = download(name, MODELS[name]) and ok
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

