"""tools/make_skin.py：把一张图片做成桌宠皮肤。

用法：
  python tools/make_skin.py <图片路径> [皮肤名]

可选依赖（不装也能用，只是不能自动去背景）：
  pip install pillow       # 缩放 + 白色背景去除
  pip install rembg        # AI 自动抠图（更通用，首次运行会下载模型）

处理顺序：rembg 抠图 -> PIL 白色去底+缩放 -> 直接复制原图。
生成到 skins/<皮肤名>/pet.png，并把 data/config.json 的 pet.skin 设为皮肤名。
"""
import json
import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS_DIR = os.path.join(PROJECT_ROOT, "skins")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "config.json")

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
    img = img.convert("RGBA")
    data = list(img.getdata())
    out = []
    for r, g, b, a in data:
        if r > 240 and g > 240 and b > 240:
            out.append((r, g, b, 0))
        else:
            out.append((r, g, b, a))
    img.putdata(out)
    return img


def build_skin(src, out_path):
    if HAS_REMBG:
        try:
            from rembg import remove as _remove
            with open(src, "rb") as f:
                data = _remove(f.read())
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
    if len(sys.argv) < 2:
        print("用法: python tools/make_skin.py <图片路径> [皮肤名]")
        sys.exit(1)
    src = sys.argv[1]
    if not os.path.exists(src):
        print(f"找不到图片: {src}")
        sys.exit(1)
    name = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(src))[0]
    out_dir = os.path.join(SKINS_DIR, name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "pet.png")

    method = build_skin(src, out_path)
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
