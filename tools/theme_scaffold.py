"""tools/theme_scaffold.py：从一张图生成"多状态主题"骨架（v3.5）。

用法：
  python tools/theme_scaffold.py <图片路径> [皮肤名]
  python tools/theme_scaffold.py <图片路径> [皮肤名] --copy   # 把图复制到每个状态槽，方便逐个替换

生成到 skins/<皮肤名>/：
  pet.png      兜底图（所有状态先用它）
  theme.json   主题清单（states 留空 = 全部回退 pet.png）
  pet.json     人脸元数据（可选，装饰品/表情自动适配）

之后想单独换某个状态的表情，把新图存成 happy.png / angry.png / furious.png
等即可（见 theme.json 说明），不需要改任何代码。
"""
import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
SKINS_DIR = os.path.join(PROJECT_ROOT, "skins")

from core.theme import THEME_STATES  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="把一张图片做成多状态桌宠主题骨架")
    ap.add_argument("image")
    ap.add_argument("name", nargs="?", default=None)
    ap.add_argument("--copy", action="store_true",
                    help="把图片复制到每个状态槽位（方便逐个替换）")
    args = ap.parse_args()

    src = args.image
    if not os.path.exists(src):
        print(f"找不到图片: {src}")
        sys.exit(1)
    name = args.name or os.path.splitext(os.path.basename(src))[0]
    out_dir = os.path.join(SKINS_DIR, name)
    base = out_dir
    i = 1
    while os.path.exists(os.path.join(out_dir, "pet.png")):
        out_dir = f"{base}_{i}"
        i += 1
    os.makedirs(out_dir, exist_ok=True)

    from tools.make_skin import build_skin
    method = build_skin(src, os.path.join(out_dir, "pet.png"))
    print(f"pet.png 已生成（{method}）: {os.path.join(out_dir, 'pet.png')}")

    if args.copy:
        for st in THEME_STATES:
            if st != "idle":
                shutil_copy(os.path.join(out_dir, "pet.png"),
                            os.path.join(out_dir, f"{st}.png"))
        states = {st: f"{st}.png" for st in THEME_STATES if st != "idle"}
        print("已把图片复制到每个状态槽位，可逐个替换")
    else:
        states = {}
        print("提示：想单独换某个状态的表情，把新图存成 happy.png / angry.png /")
        print("      furious.png / celebrate.png / error.png / sleep.png 等即可。")

    manifest = {
        "name": name,
        "fallback": "pet.png",
        "states": states,
        "说明": "states 里每个状态对应一张 PNG 图；缺省状态自动回退 pet.png。",
    }
    with open(os.path.join(out_dir, "theme.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    try:
        from ui.skin_face import detect_face_meta
        meta = detect_face_meta(os.path.join(out_dir, "pet.png"))
        if meta:
            with open(os.path.join(out_dir, "pet.json"), "w", encoding="utf-8") as f:
                json.dump({"face": meta}, f, ensure_ascii=False, indent=2)
            print("已识别人脸位置，装饰品/表情会自动适配")
        else:
            print("（未识别到人脸，装饰品/表情将居中摆放）")
    except Exception as exc:
        print("人脸检测跳过：", exc)

    print(f"主题骨架已生成: {out_dir}")
    print(f"使用: python tools/validate_theme.py {name}")


def shutil_copy(src, dst):
    import shutil
    shutil.copy(src, dst)


if __name__ == "__main__":
    main()
