"""core/help_data.py：帮助中心数据源（v3.7 预埋骨架）。

【核心原则】帮助内容不手写死，而是从代码里的"单一事实来源"自动收集，
这样帮助永远和实际功能同步，不会因为版本更新而过期：

- 设置项说明  <- core/settings_schema.py（label/desc 字段，编辑器也在用）
- 快捷键清单  <- 本模块 register_hotkey() 登记（main.py 注册热键时同步登记）
- 功能条目    <- 本模块 FEATURES（每加一个新功能就在这里加一条 added_in=版本号）
- 当前版本    <- VERSION（每次发版更新）

以后加新功能 = 在 FEATURES / schema / 热键登记处各加一条 = 帮助中心自动多一条。
帮助中心可以按 added_in 分组显示"本版本新增"，让老用户升级后立刻知道多了什么。
"""
import os

APP_NAME = "Focus Pet"
VERSION = "4.0.4"          # 当前版本号（每次发版更新这里）
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

# 功能条目（v3.7 帮助中心渲染用；随版本增补）
# id / name / where（在哪开启）/ what（干什么）/ added_in（引入版本）
FEATURES = [
    {"id": "start_study", "name": "开始学习",
     "where": "右键桌宠 →「开始学习…」，或快捷键 Ctrl+Alt+S",
     "what": "告诉宠物今天学什么 + 本次学习时长（分钟，可留空不限时），进入监督会话；到点提醒；结束后给总结",
     "added_in": "1.0"},
    {"id": "end_study", "name": "结束学习",
     "where": "右键桌宠 →「结束学习」",
     "what": "结束当前会话，宠物播报专注/分心时长（学习中途退出会扣金币和好感）",
     "added_in": "1.0"},
    {"id": "mode", "name": "多档模式",
     "where": "右键桌宠 →「多档模式」",
     "what": "轻松/日常/考试冲刺/自定义四档，档位越严阻断越快",
     "added_in": "3.0"},
    {"id": "pomodoro", "name": "番茄钟",
     "where": "右键桌宠 →「番茄钟：开启/关闭」",
     "what": "开关式：开启后专注/休息循环，休息窗口解除限制",
     "added_in": "1.0"},
    {"id": "dnd", "name": "免打扰",
     "where": "右键桌宠 →「免打扰：开启/关闭」，或托盘右键",
     "what": "让宠物闭嘴静音（不弹气泡/不发声/不放大遮挡），但监督照常",
     "added_in": "3.6"},
    {"id": "mini", "name": "迷你模式",
     "where": "右键桌宠 →「迷你模式」，或托盘右键，或 Ctrl+Alt+M",
     "what": "桌宠缩成 90×90 小形态，不挡桌面",
     "added_in": "3.6"},
    {"id": "skin", "name": "更换形象 / 自定义桌宠",
     "where": "右键桌宠 →「更换形象…」→ 导入新图片 / 导入主题包",
     "what": "用自己的图片当桌宠（桌面上和我的空间里都会显示你的图片），自动适配所有状态/托盘图标；或导入多状态主题包 zip。建议用白底/浅色背景的照片，AI 抠图更干净",
     "added_in": "3.0"},
    {"id": "shop", "name": "商店",
     "where": "右键桌宠 →「商店…」",
     "what": "用专注币买家具：按地图（温馨小屋/星空书房/海边/森林）分类，在哪个地图买的家具只能放在那个地图（切到对应地图才显示）",
     "added_in": "3.1"},
    {"id": "space", "name": "我的空间",
     "where": "右键桌宠 →「我的空间…」",
     "what": "宠物的房间，摆放买到的家具（家具按地图分类，切到对应地图才显示）；家具可自由拖动，位置自动记住",
     "added_in": "3.1"},
    {"id": "achievements", "name": "成就",
     "where": "右键桌宠 →「成就…」",
     "what": "学习成就徽章，解锁奖励专注币",
     "added_in": "3.2"},
    {"id": "report", "name": "数据报表",
     "where": "右键桌宠 →「数据报表…」",
     "what": "每日专注/分心柱状图 + 分心明细",
     "added_in": "3.2"},
    {"id": "settings", "name": "设置（集中配置编辑器）",
     "where": "右键桌宠 →「设置…」，或 python main.py --settings",
     "what": "所有参数集中一处：汇率/阻断阈值/经验表/价格/关键词，保存即热生效",
     "added_in": "3.3"},
    {"id": "teach", "name": "教宠物（误判纠正）",
     "where": "右键桌宠 →「这个是学习用的！」",
     "what": "被误拦时告诉宠物这个窗口/网站是学习用的，以后不再拦",
     "added_in": "1.0"},
    {"id": "tray", "name": "系统托盘",
     "where": "Windows 右下角通知区域（桌宠启动后自动出现）",
     "what": "左键双击显示/隐藏桌宠；右键菜单：开始学习/结束学习/显示隐藏/免打扰/迷你模式/退出",
     "added_in": "3.5"},
    {"id": "notify_block", "name": "通知屏蔽（专注助手）",
     "where": "设置 → 通知屏蔽（默认开）；开始学习自动生效",
     "what": "学习时自动开 Windows 专注助手：微信/QQ 等不弹通知、任务栏不闪烁、不响铃，结束恢复",
     "added_in": "3.7"},
    {"id": "extension", "name": "浏览器扩展拦截",
     "where": "Chrome/Edge 手动加载 browser_extension/，设置里开启桥接",
     "what": "URL 级黑名单拦截 + 白名单特例 + 教宠物；打开黑名单网站跳转拦截页",
     "added_in": "1.5"},
    # ---- v4.0.1 互动玩法 ----
    {"id": "pet_headpat", "name": "摸头",
     "where": "左键双击桌宠本体（不是拖动）",
     "what": "双击摸头：脑袋上冒小爱心、脸红、眼睛眯起来很享受；好感 +1（约 3 秒冷却）",
     "added_in": "4.0.1"},
    {"id": "feed", "name": "投喂",
     "where": "右键桌宠 →「投喂…」",
     "what": "花专注币买食物喂宠物，增加好感（小鱼干/牛奶/蛋糕，价格与好感在设置里可调）",
     "added_in": "4.0.1"},
    {"id": "checkin", "name": "每日打卡",
     "where": "右键桌宠 →「每日打卡…」；启动时未打卡会提醒",
     "what": "每天限一次领专注币，连续打卡额外奖励（连续第 N 天 +N×加成）",
     "added_in": "4.0.1"},
    {"id": "space_scene", "name": "空间场景切换",
     "where": "右键桌宠 →「我的空间…」→ 左上角场景下拉框",
     "what": "温馨小屋/星空书房/海边/森林四种场景，家具照常摆放（二维小世界第一步）",
     "added_in": "4.0.1"},
]

# 快捷键登记表（main.py 注册热键时同步调用 register_hotkey）
_hotkeys = []


def register_hotkey(combo, description):
    """登记一个快捷键说明（帮助中心展示用）。combo 如 'Ctrl+Alt+S'。"""
    _hotkeys.append({"combo": combo, "desc": description})


def hotkeys_help():
    """返回快捷键帮助清单（按登记顺序）。"""
    return list(_hotkeys)


def settings_help():
    """从 settings_schema 自动收集设置项说明（与编辑器共用同一数据源，不会过期）。"""
    try:
        from core.settings_schema import CONFIG_SCHEMA, SETTINGS_SCHEMA
    except Exception:
        return []
    out = []
    for entry in CONFIG_SCHEMA + SETTINGS_SCHEMA:
        out.append({
            "category": entry.get("category", "其他"),
            "label": entry.get("label", entry.get("path", "")),
            "desc": entry.get("desc", ""),
            "file": "应用配置" if entry.get("file") == "config" else "开发者参数",
        })
    return out


def features_new_in(version):
    """返回指定版本之后新增的功能（帮助中心"本版本新增"标签用）。"""
    return [f for f in FEATURES if f["added_in"] == version]
