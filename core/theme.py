"""core/theme.py：主题资源包系统（v3.5，借鉴 clawd-on-desk 的 theme.json 设计思想，独立实现）。

皮肤目录 skins/<名字>/：
  theme.json      可选清单：{"name","fallback","states":{状态:文件},"face":{cx,cy,r}}
  pet.png         兜底图（旧版单图皮肤 = 只此一张，所有状态用它，完全兼容）
  idle.png        可选：默认待机图（比 pet.png 优先）
  happy/curious/annoyed/angry/furious/celebrate/error/sleep.png  可选：各状态专属图

回退链（按状态取图）：
  指定状态图 -> idle 图 -> fallback(pet.png) -> None（由程序化小猫兜底）

说明：Tk 的 PhotoImage 只支持 PNG/GIF/PPM，主题图统一用 PNG。
"""
import json
import os
import shutil
import tempfile
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS_DIR = os.path.join(PROJECT_ROOT, "skins")

# 全部状态槽位（按"严重程度/情绪"排列，idle 是通用兜底）
THEME_STATES = [
    "idle", "happy", "curious", "annoyed", "angry", "furious",
    "celebrate", "error", "sleep",
]
# 可选状态：缺了不报错（用回退链），但校验脚本会提醒
OPTIONAL_STATES = ["happy", "curious", "annoyed", "angry", "furious",
                   "celebrate", "error", "sleep"]


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def iter_skins():
    """返回全部可用皮肤名（含内置 default）。"""
    names = ["default"]
    if not os.path.isdir(SKINS_DIR):
        return names
    for entry in sorted(os.listdir(SKINS_DIR)):
        d = os.path.join(SKINS_DIR, entry)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "pet.png")):
            names.append(entry)
    return names


def load_manifest(name):
    """读取主题清单；不是主题（或损坏）返回 None。"""
    if not name or name == "default":
        return None
    path = os.path.join(SKINS_DIR, name, "theme.json")
    if os.path.exists(path):
        data = _read_json(path)
        if isinstance(data, dict):
            return data
    return None


def face_meta(name):
    """皮肤的人脸元数据（装饰品/表情自动适配用）。"""
    if not name or name == "default":
        return None
    path = os.path.join(SKINS_DIR, name, "pet.json")
    data = _read_json(path)
    if isinstance(data, dict) and isinstance(data.get("face"), dict):
        return data["face"]
    return None


def resolve_image_file(name, state):
    """按回退链返回某状态对应的图片文件路径；没有则 None。

    优先级：theme.json 指定 -> 目录里同名的 <状态>.png -> idle.png -> pet.png
    """
    if not name or name == "default":
        return None
    skin_dir = os.path.join(SKINS_DIR, name)
    manifest = load_manifest(name)
    # 1) theme.json 里显式指定
    if manifest:
        fname = (manifest.get("states") or {}).get(state)
        if fname:
            p = os.path.join(skin_dir, fname)
            if os.path.exists(p):
                return p
    # 2) 目录里同名的 <状态>.png（最省事：放一张 angry.png 就是生气表情）
    direct = os.path.join(skin_dir, f"{state}.png")
    if os.path.exists(direct):
        return direct
    # 3) idle 图
    idle_png = os.path.join(skin_dir, "idle.png")
    if os.path.exists(idle_png):
        return idle_png
    # 4) fallback（theme.json 里指定，默认 pet.png）
    fallback = "pet.png"
    if manifest:
        fallback = manifest.get("fallback") or "pet.png"
    p = os.path.join(skin_dir, fallback)
    if os.path.exists(p):
        return p
    return None


def available_states(name):
    """该主题实际能提供哪些状态（按回退链去重后）。"""
    if not name or name == "default":
        return []
    out = []
    for st in THEME_STATES:
        if resolve_image_file(name, st):
            out.append(st)
    return out


def validate_theme(name):
    """返回 (ok, messages)。ok=False 时该主题不可用。"""
    msgs = []
    if not name or name == "default":
        return True, ["（内置程序化小猫，无需校验）"]
    skin_dir = os.path.join(SKINS_DIR, name)
    if not os.path.isdir(skin_dir):
        return False, [f"皮肤目录不存在: {skin_dir}"]
    manifest = load_manifest(name)
    if manifest is not None:
        states = manifest.get("states")
        if not isinstance(states, dict):
            msgs.append("theme.json 的 states 应为对象")
        fallback = manifest.get("fallback", "pet.png")
        if not os.path.exists(os.path.join(skin_dir, fallback)):
            msgs.append(f"兜底图缺失: {fallback}")
        for st, fname in (states or {}).items():
            if not os.path.exists(os.path.join(skin_dir, fname)):
                msgs.append(f"状态 {st} 指定的文件不存在: {fname}")
    if not os.path.exists(os.path.join(skin_dir, "pet.png")):
        msgs.append("缺少 pet.png（至少需要一张兜底图）")
        return False, msgs
    missing = [s for s in OPTIONAL_STATES
               if not resolve_image_file(name, s)]
    if missing:
        msgs.append("可选状态缺图（会自动回退到 pet.png）: "
                    + "、".join(missing))
    return (not [m for m in msgs if m.startswith("缺") or "不存在" in m
                 or "应为" in m]), msgs


def import_theme_zip(zip_path, skin_name=None):
    """导入主题包 zip -> skins/<名字>/，返回 (ok, message)。

    兼容两种结构：zip 根目录直接放 theme.json/图片，或套一层顶层文件夹。
    """
    if not os.path.exists(zip_path):
        return False, f"找不到文件: {zip_path}"
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        return False, "不是有效的 zip 压缩包"
    names = zf.namelist()
    names = [n for n in names if not n.endswith("/")]
    if not names:
        return False, "压缩包里没有文件"
    # 去掉公共顶层目录
    roots = {n.split("/")[0] for n in names}
    prefix = ""
    if len(roots) == 1 and all("/" in n for n in names):
        prefix = next(iter(roots)) + "/"
    inner = [n[len(prefix):] for n in names if n.startswith(prefix)]
    if not any(n in ("theme.json", "pet.png") for n in inner):
        return False, "包里没找到 theme.json 或 pet.png，不是主题包"
    # 优先用包内 theme.json 声明的名字
    if skin_name is None:
        try:
            with zf.open(prefix + "theme.json") as f:
                _m = json.load(f)
            skin_name = _m.get("name") or "imported"
        except Exception:
            skin_name = "imported"
    skin_name = "".join(c for c in skin_name if c not in '\\/:*?"<>|').strip()
    if not skin_name:
        skin_name = "imported"
    out_dir = os.path.join(SKINS_DIR, skin_name)
    base = out_dir
    i = 1
    while os.path.exists(os.path.join(out_dir, "pet.png")):
        out_dir = f"{base}_{i}"
        i += 1
    os.makedirs(out_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="focus_pet_theme_")
    try:
        for n in names:
            if n.endswith("/"):
                continue
            rel = n[len(prefix):] if n.startswith(prefix) else n
            if not rel or rel.startswith("__MACOSX") or rel.startswith("."):
                continue
            dest = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(n) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
        ok, msgs = validate_theme_dir(tmp)
        if not ok:
            shutil.rmtree(tmp, ignore_errors=True)
            return False, "主题校验未通过：" + "；".join(msgs)
        for item in os.listdir(tmp):
            shutil.move(os.path.join(tmp, item), os.path.join(out_dir, item))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True, f"已导入主题: {os.path.basename(out_dir)}"


def validate_theme_dir(skin_dir):
    """按目录校验（zip 导入前用），返回 (ok, messages)。"""
    name = os.path.basename(skin_dir.rstrip("\\/"))
    old = SKINS_DIR
    try:
        # 临时指向该目录校验
        globals()["SKINS_DIR"] = os.path.dirname(skin_dir)
        return validate_theme(name)
    finally:
        globals()["SKINS_DIR"] = old


