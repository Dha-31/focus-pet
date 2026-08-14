"""tools/validate_theme.py：校验主题资源包（v3.5）。

用法：
  python tools/validate_theme.py [皮肤名]    # 校验指定皮肤（不填则校验全部）

输出每个状态的解析结果：OK（有专属图）/ fallback（回退 pet.png）/ missing（无图）。
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from core.theme import (THEME_STATES, available_states, iter_skins,
                        resolve_image_file, validate_theme)  # noqa: E402


def main():
    args = sys.argv[1:]
    if args:
        names = [args[0]]
    else:
        names = iter_skins()
    failed = False
    for name in names:
        ok, msgs = validate_theme(name)
        print(f"== {name} ==")
        if name == "default":
            for m in msgs:
                print("  " + m)
            continue
        for st in THEME_STATES:
            f = resolve_image_file(name, st)
            if f and f.endswith(f"{st}.png"):
                tag = "OK"
            elif f:
                tag = "fallback"
            else:
                tag = "missing"
            rel = os.path.relpath(f, PROJECT_ROOT) if f else "-"
            print(f"  {st:10s} {tag:8s} {rel}")
        for m in msgs:
            print("  ! " + m)
        if not ok:
            failed = True
    print("== 校验结束 ==")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
