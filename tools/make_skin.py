"""tools/make_skin.py：把一张图片做成桌宠皮肤。

用法：
  python tools/make_skin.py <图片路径> [皮肤名]

可选依赖（不装也能用，只是不能自动去背景）：
  pip install pillow       # 缩放 + 四角扩散去背景
  pip install rembg        # AI 自动抠图（推荐，首次运行下载模型）
                          # 默认用 BiRefNet 高质量模型（头发/边缘抠得更干净，约 300MB，只下一次）

处理顺序：rembg 抠图 -> PIL 白色去底+缩放 -> 直接复制原图。
生成到 skins/<皮肤名>/pet.png，并把 data/config.json 的 pet.skin 设为皮肤名。
"""
import json
import os
import shutil
import sys

import sys as _sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, PROJECT_ROOT)
from core.theme import SKINS_DIR  # noqa: E402
from core.config import CONFIG_PATH  # noqa: E402

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False

try:
    import rembg  # noqa: F401
    HAS_REMBG = True
except Exception:
    HAS_REMBG = False


def fit(img, max_size=400):
    img.thumbnail((max_size, max_size))
    return img


def remove_white_bg(img):
    """从四角扩散去掉浅色背景（比整图判断白色更通用：只清背景，不误伤前景里的白色）。"""
    from collections import deque
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    visited = [[False] * w for _ in range(h)]
    q = deque()
    for sx, sy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        q.append((sx, sy))
        visited[sy][sx] = True
    while q:
        x, y = q.popleft()
        r, g, b, a = px[x, y]
        if r > 225 and g > 225 and b > 225:   # 浅色（白/米白）背景
            px[x, y] = (r, g, b, 0)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                    visited[ny][nx] = True
                    q.append((nx, ny))
    return img


def _rembg_model_dir():
    """rembg 模型目录（U2NET_HOME 或 ~/.u2net）。"""
    return os.environ.get("U2NET_HOME") or os.path.join(os.path.expanduser("~"), ".u2net")


def rembg_model_ready(name="birefnet-general.onnx"):
    """AI 抠图模型是否已下载（>1MB 视为就绪）。"""
    p = os.path.join(_rembg_model_dir(), name)
    return os.path.exists(p) and os.path.getsize(p) > 1_000_000

_REMBG_SESSION = None


def _rembg_session():
    """懒加载 rembg 会话：优先 BiRefNet 高质量模型，失败回退默认 u2net。"""
    global _REMBG_SESSION
    if _REMBG_SESSION is not None:
        return _REMBG_SESSION
    try:
        from rembg import new_session
        if not rembg_model_ready("birefnet-general.onnx"):
            print("[make_skin] 首次 AI 抠图需联网下载约 300MB BiRefNet 模型，网慢会久。")
            print("[make_skin] 建议先运行: python tools/fetch_birefnet.py 提前下载（带进度条）")
            print("[make_skin] 或跳过 AI 抠图: python tools/make_skin.py --no-rembg <图片>")
        try:
            _REMBG_SESSION = new_session("birefnet-general")  # 高质量：头发/边缘更干净
            print("[make_skin] 使用 BiRefNet 高质量抠图模型")
        except Exception:
            if not rembg_model_ready("u2net.onnx"):
                print("[make_skin] BiRefNet 不可用，回退默认 u2net 模型（首次也需联网下载约 170MB）")
            else:
                print("[make_skin] BiRefNet 不可用，回退默认 u2net 模型")
            _REMBG_SESSION = new_session()                    # 回退默认 u2net
    except Exception as exc:
        print("[make_skin] rembg 模型初始化失败：", exc)
        _REMBG_SESSION = False
    return _REMBG_SESSION


def build_skin(src, out_path, prefer="auto"):
    """把图片做成皮肤。

    prefer: "auto"=rembg 优先 / "rembg"=强制 AI 抠图 / "pillow"=跳过 AI 快速去底。
    返回使用的方法: rembg / pillow / copy。
    """
    if prefer != "pillow" and HAS_REMBG:
        try:
            from rembg import remove as _remove
            sess = _rembg_session()
            if sess:
                with open(src, "rb") as f:
                    data = _remove(f.read(), session=sess)
                with open(out_path, "wb") as f:
                    f.write(data)
                return "rembg"
        except Exception as exc:
            print("rembg 失败，改用备用方案：", exc)
    if HAS_PIL:
        img = Image.open(src)
        img = fit(remove_white_bg(img))
        img.save(out_path)
        return "pillow"
    shutil.copy(src, out_path)
    return "copy"


def main():
    args = list(sys.argv[1:])
    prefer = "auto"
    if "--no-rembg" in args:
        prefer = "pillow"
        args.remove("--no-rembg")
    if "--prefer" in args:
        i = args.index("--prefer")
        if i + 1 < len(args):
            prefer = args[i + 1]
            del args[i:i + 2]
    if not args:
        print("用法: python tools/make_skin.py <图片路径> [皮肤名] [--no-rembg|--prefer auto|rembg|pillow]")
        sys.exit(1)
    src = args[0]
    if not os.path.exists(src):
        print(f"找不到图片: {src}")
        sys.exit(1)
    name = args[1] if len(args) > 1 else os.path.splitext(os.path.basename(src))[0]
    out_dir = os.path.join(SKINS_DIR, name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "pet.png")

    method = build_skin(src, out_path, prefer=prefer)
    if method == "rembg":
        print(f"已生成（rembg AI 抠图）: {out_path}")
    elif method == "pillow":
        print(f"已生成（PIL 白色去底 + 缩放）: {out_path}")
    else:
        print(f"已复制原图: {out_path}")
        print("提示：未安装 pillow/rembg，无法自动去背景。请准备透明背景 PNG，")
        print("或运行: pip install pillow rembg")

    # 生成主题清单（v3.5）：所有状态先回退 pet.png，可逐状态替换
    manifest = {
        "name": name,
        "fallback": "pet.png",
        "states": {},
        "说明": "把 happy.png / angry.png / furious.png / celebrate.png / error.png / sleep.png 放进本目录即可单独换该状态的表情。",
    }
    with open(os.path.join(out_dir, "theme.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 更新配置
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        cfg.setdefault("pet", {})["skin"] = name
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"已把 pet.skin 设为: {name}，重启桌宠生效")
    print("已生成 theme.json：放 angry.png / celebrate.png 等即可单独换该状态表情")


if __name__ == "__main__":
    main()
