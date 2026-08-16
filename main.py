"""Focus Pet 入口。

用法：
  python main.py                 # 启动桌宠 + 监督循环（Windows 桌面环境）
  python main.py --headless-check # 无界面自检（核心逻辑冒烟测试）
  python main.py --status         # 查看当前配置与最近记录
  python main.py --log            # 查看分心日志时间线
"""
import argparse
import sys
import threading
import time

# 视为"浏览器"的进程：当浏览器扩展启用时，浏览器标签页由扩展负责拦截，
# 桌宠只做提醒与情绪反馈，不暴力最小化/关闭整个浏览器窗口。
BROWSER_PROCESSES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
    "360se.exe", "360chrome.exe", "qqbrowser.exe", "sogouexplorer.exe",
}


def load_core():
    from core.config import load_config
    from core.emotion import EmotionMeter
    from core.logbook import read_events
    from core.pomodoro import Pomodoro
    from core.rules import RuleEngine
    from core.session import StudySession
    return load_config, EmotionMeter, read_events, Pomodoro, RuleEngine, StudySession


def headless_check():
    load_config, EmotionMeter, _, Pomodoro, RuleEngine, StudySession = load_core()
    print("== Focus Pet 无界面自检 ==")
    cfg = load_config()
    print(f"配置: 番茄钟开启={cfg['pomodoro']['enabled']}，"
          f"强制关闭开启={cfg['blocking']['force_close_enabled']}，"
          f"浏览器扩展开启={cfg['extension']['enabled']}，"
          f"摄像头开启={cfg['camera']['enabled']}")

    rules = RuleEngine()
    cases = [
        ("B站首页（应判 distraction）", "", "chrome.exe", "https://www.bilibili.com/"),
        ("B站课程视频（默认应判 distraction，加白名单特例后为 study）",
         "", "chrome.exe", "https://www.bilibili.com/video/BV123"),
        ("学习文档（应判 study）", "机器学习笔记.pdf", "WPS.exe", None),
        ("抖音进程（应判 distraction）", "抖音", "Douyin.exe", None),
        ("记事本（应判 unknown）", "无标题 - 记事本", "notepad.exe", None),
    ]
    for label, title, proc, url in cases:
        print(f"  {label} -> {rules.classify(title, proc, url)}")

    # 教宠物（仅内存测试，不落盘）：把 B 站课程视频记为学习后，应变为 study
    rules.learned["urls"].append("https://www.bilibili.com/video/BV123")
    after = rules.classify("", "chrome.exe", "https://www.bilibili.com/video/BV123")
    print(f"  教宠物后 B 站课程视频 -> {after}（期望 study）")

    meter = EmotionMeter(cfg["blocking"]["tiers_seconds"])
    for _ in range(70):
        meter.update(True, 1.0)
    print(f"  连续分心 70 秒 -> tier={meter.current_tier} mood={meter.mood}（期望 tier=4）")
    for _ in range(30):
        meter.update(False, 1.0)
    print(f"  学习 30 秒后 -> tier={meter.current_tier} anger={meter.anger:.0f}（期望 anger 回落）")

    session = StudySession()
    session.start("数学")
    for _ in range(120):
        session.tick(True, 1.0)
    summary = session.end()
    print(f"  会话总结: focus={summary['focus_minutes']} 分钟")
    # ---- v3.5：状态机 + 主题资源包 + 单实例 ----
    from core.state_machine import PetStateMachine
    _sm = PetStateMachine()
    _sm.set_mood(0); assert _sm.current() == "happy"
    _sm.set_mood(2); assert _sm.current() == "annoyed"
    _sm.set_mood(4); assert _sm.current() == "furious"
    _sm.play("celebrate", 0.6); assert _sm.current() == "celebrate"
    import time as _t
    _t.sleep(0.7)
    _sm.set_mood(1); assert _sm.current() == "curious"
    _sm.set_sleeping(True); assert _sm.current() == "sleep"
    _sm.set_sleeping(False)
    print("  v3.5 状态机 -> OK（happy/curious/annoyed/angry/furious + celebrate/error/sleep）")

    from core import theme as _theme
    print(f"  v3.5 主题资源包 -> OK（皮肤列表: {_theme.iter_skins()}，状态槽位: {len(_theme.THEME_STATES)} 个）")

    from core import single_instance
    _ok = single_instance.acquire()
    single_instance.release()
    print(f"  v3.5 单实例锁 -> OK（acquire={_ok}）")

    print("== 自检结束（核心逻辑正常） ==")


def print_status():
    load_config, _, read_events, _, _, StudySession = load_core()
    cfg = load_config()
    print("== 当前配置 ==")
    print(f"  番茄钟: {'开' if cfg['pomodoro']['enabled'] else '关'}"
          f"（专注 {cfg['pomodoro']['focus_minutes']} 分钟 / 休息 {cfg['pomodoro']['break_minutes']} 分钟）")
    print(f"  阻断阈值(秒): {cfg['blocking']['tiers_seconds']}")
    print(f"  强制关闭: {'开' if cfg['blocking']['force_close_enabled'] else '关'}"
          f"（警告 {cfg['blocking']['save_warning_seconds']} 秒）")
    print(f"  退出锁: {'开' if cfg['lock']['enabled'] else '关'}")
    print(f"  皮肤: {cfg['pet']['skin']}")
    from core.pet_state import PetState
    _ps = PetState()
    print(f"  桌宠: Lv.{_ps.level} | 模式: {'考试冲刺' if _ps.mode == 'exam' else '日常自习'} | 好感度 {_ps.affinity:.0f} | 累计专注 {_ps.total_focus_minutes:.0f} 分钟")
    from core.economy import Inventory
    _inv = Inventory()
    print(f"  专注币: {_inv.coins:.0f} | 已购装饰 {len(_inv.owned_accessories)} 件 / 家具 {len(_inv.owned_furniture)} 件")
    print(f"  浏览器扩展: {'开（端口 %d）' % cfg['extension']['port'] if cfg['extension']['enabled'] else '关'}")
    print(f"  摄像头: {'开（设备 %d，后端见运行日志）' % cfg['camera']['device_index'] if cfg['camera']['enabled'] else '关'}")
    print("== 最近会话 ==")
    logs = StudySession.read_log(3)
    for log in logs:
        print(f"  {log['start']} ~ {log['end']} | 目标: {log['goal']} | "
              f"专注 {log['focus_minutes']} 分 / 分心 {log['distract_minutes']} 分")
    if not logs:
        print("  （暂无记录）")
    print("== 最近事件 ==")
    for ev in read_events(5):
        print(f"  {ev['time']} [{ev['kind']}] {ev['detail']}")


def print_log():
    _, _, read_events, _, _, _ = load_core()
    events = read_events(100)
    if not events:
        print("还没有事件记录。启动桌宠后会开始记录。")
        return
    print("== 分心日志时间线（最近 100 条） ==")
    for ev in events:
        print(f"  {ev['time']} [{ev['kind']}] {ev['detail']}")


def run_app():
    try:
        from tkinter import simpledialog
    except Exception as exc:
        print("无法加载 tkinter（需要桌面环境）：", exc)
        sys.exit(1)

    load_config, EmotionMeter, _, Pomodoro, RuleEngine, StudySession = load_core()

    from core import logbook
    from core import sounds
    from core.config import save_config
    from sensors.window_monitor import get_foreground_info
    from blockers.blocker import Blocker
    from ui.pet_app import PetApp
    from bridge.server import start_bridge, get_latest_url

    from core import single_instance
    if not single_instance.acquire():
        print("Focus Pet 已经在运行了（单实例）。")
        print("如果桌宠不见了，请到托盘图标右键 -> 退出，或任务管理器结束 Python 进程。")
        sys.exit(0)

    cfg = load_config()
    rules = RuleEngine()
    session = StudySession()
    meter = EmotionMeter(cfg["blocking"]["tiers_seconds"])
    pomodoro = Pomodoro(**cfg["pomodoro"])
    ext_enabled = bool(cfg["extension"]["enabled"])

    # 桌宠养成状态 + 多档模式（日常/考试冲刺）+ 专注币经济
    from core.pet_state import PetState
    from core.economy import Inventory
    from core.settings import settings
    pet_state = PetState()
    inventory = Inventory()
    original_force_close = bool(cfg["blocking"]["force_close_enabled"])
    # v4.0.1：每日打卡 / 工作时钟 / 小游戏兑换
    from core.checkin import CheckIn
    from core.work import WorkClock
    checkin = CheckIn()
    work_clock = WorkClock()

    MODE_TIERS = settings.get("blocking.tiers") or {
        "relaxed": [10, 30, 60, 120],
        "daily": [5, 15, 30, 60],
        "exam": [3, 8, 15, 30],
        "custom": [5, 15, 30, 60],
    }
    MODE_MSG = {
        "relaxed": "轻松模式，我会温柔一点~",
        "daily": "日常自习模式！",
        "exam": "考试冲刺模式！我会更严格！",
        "custom": "自定义模式！",
    }

    def apply_mode(mode):
        cfg["blocking"]["tiers_seconds"] = MODE_TIERS.get(mode, MODE_TIERS["daily"])
        cfg["blocking"]["force_close_enabled"] = (mode == "exam") or original_force_close
        meter.tier_seconds = list(cfg["blocking"]["tiers_seconds"])

    apply_mode(pet_state.mode)

    # 浏览器扩展桥接服务（可选）
    bridge = None
    bridge_error = None
    if ext_enabled:
        try:
            bridge = start_bridge(rules, port=int(cfg["extension"]["port"]))
            print(f"[bridge] 本地桥接服务已启动，端口 {cfg['extension']['port']}（供浏览器扩展连接）")
        except Exception as exc:
            print("[bridge] 桥接服务启动失败：", exc)
            bridge_error = exc

    # 截图画面分析（v2.5）：快速通道判定不了时，本地看画面
    screen_analysis_enabled = bool(cfg["screen_analysis"]["enabled"])
    screen_interval = max(5, float(cfg["screen_analysis"]["interval_seconds"]))
    last_screen_analyze = [0.0]
    # 摄像头监督（可选，v2）：后端在后台线程创建，不阻塞桌宠启动
    camera_monitor = None
    camera_error_shown = [False]
    if cfg["camera"]["enabled"]:
        try:
            from camera.camera_monitor import CameraMonitor
            camera_monitor = CameraMonitor(
                backend=None,
                device_index=int(cfg["camera"]["device_index"]),
                interval=float(cfg["camera"]["interval_seconds"]),
            )
            camera_monitor.start()
            print("[camera] 摄像头线程已启动（模型加载在后台进行，稍后生效）")
        except Exception as exc:
            print("[camera] 摄像头初始化失败：", exc)

    def on_teach(info):
        if info:
            rules.learn(title=info.get("title", ""), process=info.get("process", ""))
            logbook.log_event("teach", f"教宠物: {info.get('process')}｜{info.get('title', '')[:20]}")
            pet.say("记住了，下次不拦你！")

    time_up_reminded = [False]

    def on_start_study(goal, minutes=None):
        if session.start(goal, planned_minutes=minutes):
            time_up_reminded[0] = False
            if bridge:
                bridge.state.supervising = True   # 学习中：启用浏览器扩展拦截
            logbook.log_event("session_start", goal)
            sounds.play("start")
            if cfg.get("focus_assist", {}).get("enabled"):
                try:
                    from core.focus_assist import enable as _fa_enable
                    _fa_enable()
                except Exception:
                    pass
            if minutes:
                pet.say(f"好！今天一起学{goal}，计划 {minutes} 分钟！")
            else:
                pet.say(f"好！今天一起学{goal}！")
        else:
            pet.say("已经在学习啦！")

    def on_end_study():
        summary = session.end()
        if bridge:
            bridge.state.supervising = False   # 结束学习：解除浏览器扩展拦截
        if not summary:
            pet.say("还没有开始学习呢")
            return
        logbook.log_event("session_end", summary["goal"])
        check_achievements()
        try:
            from core.focus_assist import restore as _fa_restore
            _fa_restore()
        except Exception:
            pass
        pet.celebrate(f"结束！专注 {summary['focus_minutes']} 分钟，"
                      f"分心 {summary['distract_minutes']} 分钟，"
                      f"好感度 {pet_state.affinity:.0f}")

    def on_toggle_pomodoro():
        cfg["pomodoro"]["enabled"] = not cfg["pomodoro"]["enabled"]
        pomodoro.set_enabled(cfg["pomodoro"]["enabled"])
        save_config(cfg)
        pet.set_pomodoro_enabled(cfg["pomodoro"]["enabled"])
        pet.say("番茄钟开启！" if cfg["pomodoro"]["enabled"] else "番茄钟关闭，持续监督！")

    def on_toggle_dnd():
        cfg["dnd"]["enabled"] = not cfg["dnd"]["enabled"]
        save_config(cfg)
        pet.set_dnd(cfg["dnd"]["enabled"])
        sounds.set_muted(cfg["dnd"]["enabled"])
        if not cfg["dnd"]["enabled"]:
            pet.say("免打扰关闭，我回来啦！")

    def on_toggle_mini():
        cfg["pet"]["mini_mode"] = not cfg["pet"]["mini_mode"]
        save_config(cfg)
        pet.set_mini(cfg["pet"]["mini_mode"])
        pet.say("我变小啦~" if cfg["pet"]["mini_mode"] else "变回原样！")

    def on_toggle_mode(mode):
        pet_state.set_mode(mode)
        apply_mode(mode)
        pet.set_mode(mode)
        pet.say(MODE_MSG.get(mode, "已切换模式"))

    # 成就系统
    from core.achievements import AchievementManager, REWARD_COINS
    achievements = AchievementManager()

    def check_achievements():
        newly = achievements.evaluate(pet_state, inventory)
        if not newly:
            return
        names = "、".join(
            (AchievementManager.get(aid) or {}).get("name", aid) for aid in newly)
        reward = len(newly) * settings.get("economy.achievement_reward", REWARD_COINS)
        inventory.add_coins(reward)
        pet.celebrate(f"🎉 解锁成就：{names}（+{reward} 币）")
        logbook.log_event("achievement", f"解锁 {names}")

    def on_open_achievements():
        check_achievements()
        from ui import window_manager
        from ui.achievements_window import AchievementsWindow
        window_manager.open(AchievementsWindow(pet.root, achievements).root)

    def on_open_report():
        from ui import window_manager
        from ui.report_window import ReportWindow
        window_manager.open(ReportWindow(pet.root).root)

    def on_open_settings():
        from ui import window_manager
        from ui.settings_editor import SettingsEditor
        window_manager.open(SettingsEditor(pet.root, pet=pet).root)

    def on_open_rules():
        from ui import window_manager
        from ui.rules_window import RulesWindow
        window_manager.open(RulesWindow(pet.root).root)
    def on_open_help(welcome=False):
        from ui import window_manager
        from ui.help_window import HelpWindow
        window_manager.open(HelpWindow(pet.root, welcome=bool(welcome)).root)

    escape_attempts = [0]

    def on_exit():
        if cfg["lock"]["enabled"]:
            code = simpledialog.askstring("退出", "输入退出码才能溜走！",
                                          parent=pet.root, show="*")
            if code != cfg["lock"]["exit_code"]:
                escape_attempts[0] += 1
                pet.say("哼，不许逃！")
                if escape_attempts[0] >= 3:
                    escape_attempts[0] = 0
                    pet_state.add_escape()
                    inventory.penalize(settings.get("economy.escape_penalty", 20))
                    logbook.log_event("escape", "连续输错退出码（惩罚）")
                    pet.say("连续逃跑要扣金币和好感！")
                return False
        if session.active:
            from tkinter import messagebox
            again = messagebox.askyesno(
                "逃跑确认",
                "还有未结束的学习会话，确定要退出吗？\n将扣除 20 专注币和好感度！",
                parent=pet.root)
            if not again:
                return False
            pet_state.add_escape()
            inventory.penalize(settings.get("economy.escape_penalty", 20))
            logbook.log_event("escape", "学习中途退出（惩罚）")
            pet.say("逃跑成功…下次别这样了")
        return True

    # ---------- v4.0.1：互动玩法回调 ----------
    def on_pet():
        """摸头：好感 +1（冷却在 PetApp 里，防连点）。"""
        pet_state.affinity = min(100.0, pet_state.affinity + 1.0)
        pet_state.save()

    def on_checkin():
        """每日打卡：领币 + 连续签到奖励。"""
        done, streak, total = checkin.status()
        if done:
            pet.say("今天已经打过卡啦，明天再来！")
            return
        r = checkin.do()
        if r:
            reward, streak, total = r
            inventory.add_coins(reward)
            logbook.log_event("checkin", f"第 {streak} 天连续打卡 +{reward:.0f} 币")
            pet.celebrate(f"打卡成功！连续 {streak} 天，+{reward:.0f} 专注币！")

    def on_feed(item):
        """投喂：花币换好感。"""
        price = int(item.get("price", 0))
        aff = float(item.get("affinity", 0))
        if not inventory.can_afford(price):
            pet.say("金币不够啦，先去学习赚币吧！")
            return
        inventory.penalize(price)
        pet_state.affinity = min(100.0, pet_state.affinity + aff)
        pet_state.save()
        logbook.log_event("feed", f"投喂 {item.get('name')} 好感+{aff:.0f}")
        pet.celebrate(f"好好吃！好感 +{aff:.0f}！")

    def on_work(minutes):
        """打工：开始工作时钟（时间到自动结算，见 check_work）。"""
        if work_clock.active:
            pet.say("已经在打工啦，别急~")
            return
        if work_clock.start(minutes):
            logbook.log_event("work_start", f"开始打工 {minutes} 分钟")
            pet.say(f"我去上班啦！{minutes} 分钟后记得来领工资~")
        else:
            pet.say("现在不能打工哦")


    def check_work():
        """主线程轮询工作时钟：更新头顶徽章、到期自动结算。"""
        try:
            if work_clock.active:
                if work_clock.is_done():
                    base = work_clock.finish()
                    if base:
                        coins = base * (1.0 + (pet_state.level - 1) * 0.05)
                        inventory.add_coins(coins)
                        logbook.log_event("work_done", f"打工完成 +{coins:.0f} 币")
                        pet.set_work(False)
                        pet.celebrate(f"下班啦！赚了 {coins:.0f} 专注币！")
                else:
                    pet.set_work(True, work_clock.remaining())
            else:
                pet.set_work(False)
        except Exception as exc:
            print("[work] 结算异常：", exc)
        try:
            pet.root.after(5000, check_work)
        except Exception:
            pass

    pet = PetApp(cfg, mode=pet_state.mode, inventory=inventory,
                 on_teach=on_teach,
                 on_start_study=on_start_study, on_end_study=on_end_study,
                 on_toggle_pomodoro=on_toggle_pomodoro,
                 on_mode_change=on_toggle_mode, on_exit=on_exit,
                 on_open_achievements=on_open_achievements,
                 on_open_report=on_open_report,
                 on_open_settings=on_open_settings,
                 tray_enabled=True,
                 on_toggle_dnd=on_toggle_dnd,
                 on_toggle_mini=on_toggle_mini,
                 on_open_help=on_open_help,
                 on_pet=on_pet, on_checkin=on_checkin, on_feed=on_feed,
                 on_work=on_work, on_open_rules=on_open_rules)

    sounds.set_muted(pet.dnd)   # 免打扰初始状态同步给音效

    # 首次启动：自动弹出帮助/欢迎（可勾选"下次不再显示"，右键「使用帮助…」随时打开）
    if not cfg.get("first_run", {}).get("done"):
        pet.root.after(600, lambda: on_open_help(welcome=True))
        try:
            cfg.setdefault("first_run", {})["done"] = True
            save_config(cfg)
        except Exception:
            pass
    # v4.0.1：启动工作结算轮询 + 今日未打卡提醒
    pet.root.after(3000, check_work)
    _done_today, _, _ = checkin.status()
    if not _done_today:
        pet.root.after(2500, lambda: pet.say("新的一天！记得右键「每日打卡」领金币哦~"))

    # 系统托盘（v3.5）：失败也不影响桌宠
    tray = None
    try:
        from ui.tray import TrayIcon
        tray = TrayIcon(
            tooltip="Focus Pet 学习监督桌宠",
            on_start=lambda: pet._menu_start_study(),
            on_end=lambda: pet._menu_end_study(),
            on_toggle=lambda: pet.toggle_visible(),
            on_quit=lambda: pet._menu_exit(),
            on_dnd=on_toggle_dnd,
            on_mini=on_toggle_mini)
        if tray.is_ok():
            print("[tray] 系统托盘已启用：双击显示/隐藏，右键菜单")
        else:
            tray = None
            pet.tray_enabled = False
    except Exception as exc:
        print("[tray] 托盘不可用:", exc)
        tray = None
        pet.tray_enabled = False
    if bridge_error:
        pet.show_error(f"浏览器扩展桥接启动失败：{bridge_error}")

    # 托盘图标跟随当前皮肤（自定义图像适配：换皮肤后托盘图标一起变）
    def _update_tray_icon():
        if tray is None:
            return
        try:
            from core import theme as theme_mod
            path = theme_mod.resolve_image_file(cfg.get("pet", {}).get("skin", "default"), "idle")
            if path:
                tray.set_icon_from_path(path)
        except Exception:
            pass

    if tray is not None:
        pet.on_skin_changed = _update_tray_icon
        _update_tray_icon()

    # 全局快捷键（v3.6）：Ctrl+Alt+S 学习 / Ctrl+Alt+H 显隐 / Ctrl+Alt+M 迷你
    hotkeys_mgr = None
    if cfg.get("hotkeys", {}).get("enabled"):
        try:
            from core.hotkeys import HotkeyManager
            hotkeys_mgr = HotkeyManager()
            if hotkeys_mgr.is_ok():
                def _hk_study():
                    if session.active:
                        pet.root.after(0, on_end_study)
                    else:
                        pet.root.after(0, lambda: pet._menu_start_study())
                def _hk_toggle():
                    pet.root.after(0, pet.toggle_visible)
                def _hk_mini():
                    pet.root.after(0, on_toggle_mini)
                hotkeys_mgr.register(0x0001 | 0x0002, 0x53, _hk_study)   # Ctrl+Alt+S
                hotkeys_mgr.register(0x0001 | 0x0002, 0x48, _hk_toggle)  # Ctrl+Alt+H
                hotkeys_mgr.register(0x0001 | 0x0002, 0x4D, _hk_mini)    # Ctrl+Alt+M
                # 同步登记到帮助数据源（帮助中心自动展示，保证不过期）
                from core.help_data import register_hotkey as _reg_hk
                _reg_hk("Ctrl+Alt+S", "开始/结束学习")
                _reg_hk("Ctrl+Alt+H", "显示/隐藏桌宠")
                _reg_hk("Ctrl+Alt+M", "迷你模式")
                print("[hotkeys] 全局快捷键已启用：Ctrl+Alt+S 学习 / Ctrl+Alt+H 显隐 / Ctrl+Alt+M 迷你")
            else:
                hotkeys_mgr = None
        except Exception as exc:
            print("[hotkeys] 快捷键不可用:", exc)
            hotkeys_mgr = None
    pomodoro.on_state_change = lambda state: (
        sounds.play("break"),
        pet.say("专注时间到！" if state == "focus" else "休息时间到啦，去喝口水吧~"))

    blocker = Blocker(pet, cfg)
    stop_event = threading.Event()

    def supervisor():
        poll = max(0.5, float(cfg["supervision"]["poll_interval_seconds"]))
        last_cat = None
        last_tier = 0
        while not stop_event.is_set():
            time.sleep(poll)
            info = get_foreground_info()
            pet.update_info(info)
            if not info:
                continue

            process = (info["process"] or "").lower()
            is_browser = process in BROWSER_PROCESSES

            # 浏览器扩展启用时，用扩展上报的 URL 参与判定
            url = None
            if ext_enabled and is_browser:
                latest = get_latest_url(bridge)
                if latest and (time.time() - latest["ts"]) < 5.0:
                    url = latest["url"]

            cat = rules.classify(title=info["title"], process=info["process"], url=url)

            # ---- 摄像头增强判定（可选，v2）----
            cam = camera_monitor.get_latest() if camera_monitor else None
            if cam and cam.get("error") and not camera_error_shown[0]:
                camera_error_shown[0] = True
                print("[camera]", cam["error"])
                pet.show_error("摄像头出问题了，先不盯镜头啦")
            if cam and not cam.get("error") and cam.get("backend") != "none":
                if not cam.get("person_present"):
                    # 人不在：不计专注、不生气、不阻断，宠物睡觉
                    meter.update(False, poll)
                    pet.set_mood(0)
                    pet.set_sleeping(True)
                    blocker.reset()
                    session.tick(False, poll)
                    if last_cat != "away":
                        pet.say("你去哪了？回来学习呀~")
                        logbook.log_event("away", "人不在摄像头前")
                    last_cat = "away"
                    continue
                if cam.get("off_screen_study"):
                    cat = "study"          # 纸上写字 / 看书 = 学习
                elif cam.get("phone_suspicion"):
                    cat = "distraction"    # 疑似玩手机

            # ---- 截图画面分析（v2.5）：快速通道判定不了时，本地看画面 ----
            screen_derived = False
            if cat == "unknown" and screen_analysis_enabled:
                now = time.time()
                if now - last_screen_analyze[0] >= screen_interval:
                    last_screen_analyze[0] = now
                    try:
                        from sensors.screen_analyzer import analyze_foreground
                        result = analyze_foreground(info.get("hwnd"))
                    except Exception:
                        result = None
                    if result and result["category"] in ("study", "distraction"):
                        cat = result["category"]
                        screen_derived = True
                        logbook.log_event(
                            "screen_analysis",
                            f"{result['category']}（{'、'.join(result['reasons']) or '画面特征'}）",
                        )
            # 番茄钟（可开关）
            if pomodoro.enabled and pomodoro.state == "idle":
                pomodoro.start()
            pomodoro.tick(poll)
            if pomodoro.is_break():
                # 休息窗口：解除一切阻断
                meter.update(False, poll)
                blocker.reset()
                pet.set_mood(0)
                last_cat = cat
                continue

            # 集中配置热更新：阻断阈值实时生效
            _tiers = settings.get("blocking.tiers")
            if isinstance(_tiers, dict):
                _cur = _tiers.get(pet_state.mode)
                if _cur and list(_cur) != meter.tier_seconds:
                    meter.tier_seconds = list(_cur)

            # 只有学习会话中才监督；未学习/已结束时宠物不生气、不阻断
            if not session.active:
                meter.update(False, poll)
                blocker.reset()
                pet.set_mood(meter.mood)
                pet.set_activity("idle", 0)
                last_cat = cat
                continue

            is_distraction = cat == "distraction"
            tier = meter.update(is_distraction, poll)
            if screen_derived:
                tier = min(tier, 1)  # 画面分析是启发式，只提醒不暴力关
            pet.set_mood(meter.mood)
            pet.set_activity(cat, pet_state.current_streak)   # 活动驱动动画（打盹/踱步）
            session.tick(cat == "study", poll)
            # 计划学习时长到点提醒（一次）
            if session.active and session.is_time_up() and not time_up_reminded[0]:
                time_up_reminded[0] = True
                pet.say(f"学习时间到啦！已经过了 {int(session.planned_minutes)} 分钟，可以休息或继续~")
                sounds.play("celebrate")
                logbook.log_event("time_up", f"计划时长 {int(session.planned_minutes)} 分钟到点")

            # 桌宠养成：专注加经验、摸鱼扣好感、升级提示
            if cat == "study":
                pet_state.add_focus(poll)
                inventory.earn(poll)   # 专注赚币
            elif is_distraction:
                pet_state.add_distraction(poll)
            if pet_state.consume_level_up():
                pet.celebrate(f"🎉 我升到 Lv.{pet_state.level} 啦！")
                check_achievements()
            pet.set_level(pet_state.level)

            # 小猫生气时的文字提醒（情绪升级时说话）
            if tier > 0 and tier > last_tier:
                if tier == 1:
                    pet.say("喂喂，别分心啦，快回来学习！")
                elif tier == 2:
                    pet.say("还在分心？我要生气啦！")
                elif tier == 3:
                    pet.say("再分心我就要遮住你的屏幕了！")
                else:
                    pet.say("最后一次警告！快回来学习！")
            last_tier = tier

            if tier == 0:
                if last_cat == "distraction" and cat != "distraction":
                    pet.set_sleeping(False)
                    pet.say("回来啦，继续加油！")
                elif last_cat == "away":
                    pet.set_sleeping(False)
                    pet.say("欢迎回来！")
                blocker.reset()
            else:
                if screen_derived:
                    # 画面分析判定为分心：只提醒，不暴力关
                    if cat != last_cat:
                        pet.say("这个画面看起来不像在学习哦~")
                    blocker.reset()
                elif cam and cam.get("phone_suspicion"):
                    # 玩手机：关不了手机，只能提醒
                    if cat != last_cat:
                        pet.say("别玩手机啦！")
                    blocker.reset()
                elif is_browser and ext_enabled:
                    # 浏览器标签页交给扩展拦截，桌宠只提醒不暴力关窗口
                    if cat != last_cat:
                        pet.say("这个页面被拦住了，回来学习吧！")
                    blocker.reset()
                else:
                    blocker.handle(tier, info["hwnd"], info["title"])
                    blocker.tick(poll)

            if is_distraction and cat != last_cat:
                logbook.log_event(
                    "distraction",
                    f"{info['process']}｜{info['title'][:40]}",
                )
            last_cat = cat

    thread = threading.Thread(target=supervisor, daemon=True)
    thread.start()
    try:
        pet.root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        try:
            from core.focus_assist import restore as _fa_restore
            _fa_restore()
        except Exception:
            pass
        if tray is not None:
            try:
                tray.destroy()
            except Exception:
                pass
        if hotkeys_mgr is not None:
            try:
                hotkeys_mgr.destroy()
            except Exception:
                pass
        try:
            single_instance.release()
        except Exception:
            pass
    print("桌宠已退出。晚安！")


def screen_check():
    """截图画面分析自检：截当前窗口画面并打印分析结果。"""
    from sensors.screen_analyzer import analyze_foreground
    from sensors.window_monitor import get_foreground_info
    info = get_foreground_info()
    print("当前窗口:", info)
    result = analyze_foreground(info["hwnd"] if info else None)
    print("分析结果:", result)

def import_theme_cli(path):
    """命令行导入主题包 zip 并设为当前形象。"""
    from core import theme as theme_mod
    ok, msg = theme_mod.import_theme_zip(path)
    if not ok:
        print("导入失败：", msg)
        sys.exit(1)
    print(msg)
    name = msg.split(": ")[-1]
    from core.config import load_config, save_config
    cfg = load_config()
    cfg.setdefault("pet", {})["skin"] = name
    save_config(cfg)
    print(f"已把 pet.skin 设为: {name}，下次启动桌宠生效")


def open_settings():
    """直接打开集中配置编辑器（不需要先启动桌宠）。"""
    import tkinter as tk
    from ui.settings_editor import SettingsEditor
    root = tk.Tk()
    root.withdraw()
    SettingsEditor(root, pet=None)
    root.mainloop()

def camera_setup():
    """打开摄像头设置窗口（图形界面）：实时预览 + 选择前置/后置 + 保存。"""
    try:
        from ui.camera_setup import run
    except Exception as exc:
        print("无法打开摄像头设置窗口：", exc)
        sys.exit(1)
    run()

def camera_check():
    """摄像头自检：打开摄像头跑约 5 秒，打印每一帧的状态。"""
    from core.config import load_config
    from camera.backends import create_backend
    from camera.camera_monitor import CameraMonitor

    cfg = load_config()
    backend = create_backend()
    if backend is None:
        print("未安装 opencv/mediapipe。请先运行: pip install opencv-python mediapipe")
        sys.exit(1)
    print(f"后端: {backend.name}，设备索引: {cfg['camera']['device_index']}")
    mon = CameraMonitor(backend, device_index=int(cfg["camera"]["device_index"]), interval=0.5)
    mon.start()
    try:
        for _ in range(10):
            time.sleep(0.5)
            st = mon.get_latest()
            if st.get("error"):
                print("摄像头错误:", st["error"])
                break
            print(st)
    finally:
        mon.stop()
    print("摄像头自检结束")

def _enable_dpi_awareness():
    """开启 DPI 感知：让 Tk 界面在 Windows 缩放下文字清晰（v3.7.1）。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def main():
    _enable_dpi_awareness()
    parser = argparse.ArgumentParser(description="Focus Pet - 陪你学习也监督你学习")
    parser.add_argument("--headless-check", action="store_true", help="无界面自检核心逻辑")
    parser.add_argument("--camera-check", action="store_true", help="摄像头自检（约 5 秒）")
    parser.add_argument("--camera-setup", action="store_true", help="打开摄像头设置窗口（图形界面）")
    parser.add_argument("--screen-check", action="store_true", help="截图画面分析自检")
    parser.add_argument("--settings", action="store_true", help="打开集中配置编辑器（不用先开桌宠）")
    parser.add_argument("--import-theme", metavar="ZIP", help="导入主题包 zip 并设为当前形象")
    parser.add_argument("--status", action="store_true", help="查看配置与最近记录")
    parser.add_argument("--log", action="store_true", help="查看分心日志")
    args = parser.parse_args()

    if args.headless_check:
        headless_check()
    elif args.camera_check:
        camera_check()
    elif args.camera_setup:
        camera_setup()
    elif args.screen_check:
        screen_check()
    elif args.import_theme:
        import_theme_cli(args.import_theme)
    elif args.settings:
        open_settings()
    elif args.status:
        print_status()
    elif args.log:
        print_log()
    else:
        run_app()


if __name__ == "__main__":
    main()





