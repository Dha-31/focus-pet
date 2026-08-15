"""core/settings_schema.py：集中配置清单（数据驱动）。

- DEFAULTS：所有"魔法数字"的默认值（开发者参数）
- SETTINGS_SCHEMA：编辑器按它自动生成输入界面
- CONFIG_SCHEMA：应用配置（config.json）的编辑清单

以后加新功能：在 DEFAULTS 加默认值 + 在对应 SCHEMA 加一条描述，
编辑器会自动多出对应输入框（无需改编辑器代码）。
"""
# 默认参数（会被 data/settings.json 覆盖）
DEFAULTS = {
    "economy": {
        "coin_per_minute": 1.0,      # 每专注 1 分钟获得的金币数（0.1 = 10 分钟 1 币）
        "achievement_reward": 20,    # 每解锁一个成就奖励的金币
        "escape_penalty": 20,        # 逃跑/连错密码扣除的金币
    },
    "blocking": {
        "tiers": {
            "relaxed": [10, 30, 60, 120],
            "daily": [5, 15, 30, 60],
            "exam": [3, 8, 15, 30],
            "custom": [5, 15, 30, 60],
        },
    },
    "pet": {
        "xp_levels_seconds": [0, 1800, 5400, 10800, 18000, 28800, 43200, 64800],
    },
    "shop": {
        "prices": {
            "flower": 15, "bow_pink": 20, "scarf": 25, "hat_red": 30,
            "glasses": 40, "crown_gold": 80,
            "rug": 20, "lamp": 25, "plant": 30, "window": 35,
            "table": 40, "bookshelf": 60, "sofa": 80,
        },
    },
    "checkin": {
        "base_reward": 10,      # 每日打卡基础奖励金币
        "streak_bonus": 2,      # 连续签到额外加成（连续第 N 天 +N*2 币）
    },
    "work": {
        "rate_per_min": 2.0,    # 打工汇率（币/分钟）
        "options": [30, 60, 120],   # 可选打工时长（分钟）
    },
    "feed": {
        "items": [
            {"id": "fish", "name": "小鱼干", "price": 10, "affinity": 6},
            {"id": "milk", "name": "牛奶", "price": 15, "affinity": 10},
            {"id": "cake", "name": "蛋糕", "price": 25, "affinity": 18},
        ],
    },
    "space": {
        "scenes": ["cozy", "star", "sea", "forest"],
    },
    "keywords": {
        "study": [
            "目录", "摘要", "参考文献", "关键词", "讲义", "课件", "笔记", "作业",
            "试卷", "课本", "教程", "练习题", "第一章", "第二章", "第1章", "第2章",
            "引言", "绪论", "课程", "考试", "复习", "知识点", "公式", "定理",
            "证明", "实验报告", "阅读", "训练", "单词", "词汇", "答案", "六级",
            "四级", "真题", "语法",
            "pdf", "lecture", "course", "tutorial", "homework", "exam", "study",
            "notes", "chapter", "abstract", "references", "introduction", "conclusion",
            "import ", "def ", "class ", "function", "return", "numpy", "pandas",
            "torch", "print", "代码", "编程", "算法", "程序", "数据结构",
        ],
        "distraction": [
            "直播", "视频", "播放", "弹幕", "点赞", "投币", "收藏", "关注",
            "订阅", "评论", "观看", "追番", "电竞", "游戏", "攻略", "抽卡",
            "氪金", "开箱", "赛季", "段位", "排位", "匹配", "副本", "装备",
            "开始游戏", "购物车", "下单", "包邮", "秒杀", "优惠券", "热搜",
            "八卦", "明星", "吃瓜", "搞笑", "段子", "血量", "金币", "钻石",
            "战力", "皮肤", "英雄", "排行榜", "大厅", "热门", "番剧", "剧集",
            "追剧", "首页推荐",
            "play", "watch", "live", "stream", "subscribe", "game", "score",
            "video", "entertainment", "cart", "checkout", "discount",
        ],
        "code_pattern": r"\b(def|class|import|function|return|int|void|public|private|const|var|let|if|else|for|while|printf|print|console\.log|lambda|self)\b",
    },
}

# 开发者参数编辑器清单（file=settings 表示 data/settings.json）
SETTINGS_SCHEMA = [
    # 经济
    {"path": "economy.coin_per_minute", "file": "settings", "category": "经济",
     "label": "专注币汇率（币/分钟）", "type": "float", "min": 0.01, "max": 10.0, "step": 0.1,
     "desc": "每专注 1 分钟获得的金币数。填 0.1 = 专注 10 分钟得 1 币"},
    {"path": "economy.achievement_reward", "file": "settings", "category": "经济",
     "label": "成就奖励金币", "type": "int", "min": 0, "max": 1000, "step": 5,
     "desc": "每解锁一个成就奖励的金币"},
    {"path": "economy.escape_penalty", "file": "settings", "category": "经济",
     "label": "逃跑罚款金币", "type": "int", "min": 0, "max": 1000, "step": 5,
     "desc": "学习中途退出 / 连续输错退出码扣除的金币"},
    # 阻断档位
    {"path": "blocking.tiers.relaxed", "file": "settings", "category": "阻断",
     "label": "轻松模式阻断阈值(秒)", "type": "list",
     "desc": "提醒/遮挡/最小化/关闭 四个等级各自触发所需的分心秒数，逗号分隔"},
    {"path": "blocking.tiers.daily", "file": "settings", "category": "阻断",
     "label": "日常模式阻断阈值(秒)", "type": "list",
     "desc": "提醒/遮挡/最小化/关闭，逗号分隔"},
    {"path": "blocking.tiers.exam", "file": "settings", "category": "阻断",
     "label": "考试冲刺阻断阈值(秒)", "type": "list",
     "desc": "提醒/遮挡/最小化/关闭，逗号分隔"},
    {"path": "blocking.tiers.custom", "file": "settings", "category": "阻断",
     "label": "自定义模式阻断阈值(秒)", "type": "list",
     "desc": "提醒/遮挡/最小化/关闭，逗号分隔"},
    # 养成
    {"path": "pet.xp_levels_seconds", "file": "settings", "category": "养成",
     "label": "升级所需累计专注(秒)", "type": "list",
     "desc": "第 N 个值 = 升到 Lv.N+1 所需累计专注秒数，逗号分隔"},
    # 商店价格
    {"path": "shop.prices.flower", "file": "settings", "category": "商店", "label": "小花价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.bow_pink", "file": "settings", "category": "商店", "label": "蝴蝶结价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.scarf", "file": "settings", "category": "商店", "label": "围巾价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.hat_red", "file": "settings", "category": "商店", "label": "小红帽价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.glasses", "file": "settings", "category": "商店", "label": "眼镜价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.crown_gold", "file": "settings", "category": "商店", "label": "金皇冠价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.rug", "file": "settings", "category": "商店", "label": "地毯价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.lamp", "file": "settings", "category": "商店", "label": "台灯价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.plant", "file": "settings", "category": "商店", "label": "绿植价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.window", "file": "settings", "category": "商店", "label": "窗户价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.table", "file": "settings", "category": "商店", "label": "学习桌价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.bookshelf", "file": "settings", "category": "商店", "label": "书架价格", "type": "int", "min": 0, "max": 1000},
    {"path": "shop.prices.sofa", "file": "settings", "category": "商店", "label": "沙发价格", "type": "int", "min": 0, "max": 1000},
    # 打卡
    {"path": "checkin.base_reward", "file": "settings", "category": "打卡",
     "label": "每日打卡基础奖励", "type": "int", "min": 0, "max": 1000, "step": 1,
     "desc": "每天首次打卡领取的基础专注币"},
    {"path": "checkin.streak_bonus", "file": "settings", "category": "打卡",
     "label": "连续签到加成/天", "type": "int", "min": 0, "max": 100, "step": 1,
     "desc": "连续第 N 天打卡额外 +N*此值 金币"},
    # 打工
    {"path": "work.rate_per_min", "file": "settings", "category": "打工",
     "label": "打工汇率（币/分钟）", "type": "float", "min": 0.1, "max": 20.0, "step": 0.5,
     "desc": "宠物打工每分钟赚的专注币"},
    {"path": "work.options", "file": "settings", "category": "打工",
     "label": "可选打工时长(分钟)", "type": "list",
     "desc": "打工菜单里的时长选项，逗号分隔"},
    # 空间场景
    {"path": "space.scenes", "file": "settings", "category": "空间",
     "label": "可用场景列表", "type": "list",
     "desc": "我的空间可切换的场景 id，逗号分隔"},

    # 关键词
    {"path": "keywords.study", "file": "settings", "category": "关键词",
     "label": "学习关键词", "type": "textlist", "height": 6,
     "desc": "每行一个；画面文字命中即偏向判为学习"},
    {"path": "keywords.distraction", "file": "settings", "category": "关键词",
     "label": "分心关键词", "type": "textlist", "height": 6,
     "desc": "每行一个；画面文字命中即偏向判为分心"},
]

# 应用配置编辑器清单（file=config 表示 data/config.json）
CONFIG_SCHEMA = [
    {"path": "pomodoro.enabled", "file": "config", "category": "番茄钟", "label": "番茄钟开关", "type": "bool"},
    {"path": "pomodoro.focus_minutes", "file": "config", "category": "番茄钟", "label": "专注时长(分钟)", "type": "int", "min": 1, "max": 180},
    {"path": "pomodoro.break_minutes", "file": "config", "category": "番茄钟", "label": "休息时长(分钟)", "type": "int", "min": 1, "max": 60},
    {"path": "blocking.force_close_enabled", "file": "config", "category": "阻断", "label": "允许强制关闭", "type": "bool", "desc": "Lv4 强制关闭（会关掉窗口，慎开）"},
    {"path": "blocking.save_warning_seconds", "file": "config", "category": "阻断", "label": "关闭前保存倒计时(秒)", "type": "int", "min": 3, "max": 120},
    {"path": "lock.enabled", "file": "config", "category": "锁定", "label": "退出承诺锁", "type": "bool"},
    {"path": "lock.exit_code", "file": "config", "category": "锁定", "label": "退出码", "type": "str"},
    {"path": "pet.skin", "file": "config", "category": "形象", "label": "当前皮肤", "type": "str"},
    {"path": "pet.mini_mode", "file": "config", "category": "形象", "label": "迷你模式", "type": "bool", "desc": "桌宠缩成小形态，不挡桌面"},
    {"path": "pet.pet_size", "file": "config", "category": "形象", "label": "桌宠大小(宽,高)", "type": "list", "desc": "调整大小窗口会写这里，一般不手改"},
    {"path": "dnd.enabled", "file": "config", "category": "免打扰", "label": "免打扰模式", "type": "bool", "desc": "宠物闭嘴静音，监督照常（仍会检测/记录）"},
    {"path": "sound.enabled", "file": "config", "category": "音效", "label": "提示音效", "type": "bool", "desc": "完成/提醒/出错时的提示音（免打扰时自动静音）"},
    {"path": "hotkeys.enabled", "file": "config", "category": "快捷键", "label": "全局快捷键", "type": "bool", "desc": "Ctrl+Alt+S 开始/结束学习，Ctrl+Alt+H 显示/隐藏，Ctrl+Alt+M 迷你模式"},
    {"path": "focus_assist.enabled", "file": "config", "category": "通知屏蔽", "label": "学习时屏蔽系统通知", "type": "bool", "desc": "开始学习自动开 Windows 专注助手（微信/QQ 等不弹通知、不闪烁、不响），结束恢复"},
    {"path": "extension.enabled", "file": "config", "category": "扩展", "label": "浏览器扩展桥接", "type": "bool"},
    {"path": "extension.port", "file": "config", "category": "扩展", "label": "桥接端口", "type": "int", "min": 1024, "max": 65535},
    {"path": "camera.enabled", "file": "config", "category": "摄像头", "label": "摄像头开关", "type": "bool"},
    {"path": "camera.device_index", "file": "config", "category": "摄像头", "label": "设备编号", "type": "int", "min": 0, "max": 10},
    {"path": "camera.interval_seconds", "file": "config", "category": "摄像头", "label": "采样间隔(秒)", "type": "float", "min": 0.2, "max": 10, "step": 0.2},
    {"path": "screen_analysis.enabled", "file": "config", "category": "截图分析", "label": "截图分析开关", "type": "bool"},
    {"path": "screen_analysis.interval_seconds", "file": "config", "category": "截图分析", "label": "分析间隔(秒)", "type": "int", "min": 5, "max": 120},
]