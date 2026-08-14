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
    from core.config import save_config
    from sensors.window_monitor import get_foreground_info
    from blockers.blocker import Blocker
    from ui.pet_app import PetApp
    from bridge.server import start_bridge, get_latest_url

    cfg = load_config()
    rules = RuleEngine()
    session = StudySession()
    meter = EmotionMeter(cfg["blocking"]["tiers_seconds"])
    pomodoro = Pomodoro(**cfg["pomodoro"])
    ext_enabled = bool(cfg["extension"]["enabled"])

    # 桌宠养成状态 + 多档模式（日常/考试冲刺）+ 专注币经济
    from core.pet_state import PetState
    from core.economy import Inventory
    pet_state = PetState()
    inventory = Inventory()
    original_force_close = bool(cfg["blocking"]["force_close_enabled"])

    def apply_mode(mode):
        cfg["blocking"]["tiers_seconds"] = (
            [3, 8, 15, 30] if mode == "exam" else [5, 15, 30, 60])
        cfg["blocking"]["force_close_enabled"] = (mode == "exam") or original_force_close
        meter.tier_seconds = list(cfg["blocking"]["tiers_seconds"])

    apply_mode(pet_state.mode)

    # 浏览器扩展桥接服务（可选）
    bridge = None
    if ext_enabled:
        try:
            bridge = start_bridge(rules, port=int(cfg["extension"]["port"]))
            print(f"[bridge] 本地桥接服务已启动，端口 {cfg['extension']['port']}（供浏览器扩展连接）")
        except Exception as exc:
            print("[bridge] 桥接服务启动失败：", exc)

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

    def on_start_study(goal):
        if session.start(goal):
            logbook.log_event("session_start", goal)
            pet.say(f"好！今天一起学{goal}！")
        else:
            pet.say("已经在学习啦！")

    def on_end_study():
        summary = session.end()
        if not summary:
            pet.say("还没有开始学习呢")
            return
        logbook.log_event("session_end", summary["goal"])
        pet.say(f"结束！专注 {summary['focus_minutes']} 分钟，"
                f"分心 {summary['distract_minutes']} 分钟，"
                f"好感度 {pet_state.affinity:.0f}")

    def on_toggle_pomodoro():
        cfg["pomodoro"]["enabled"] = not cfg["pomodoro"]["enabled"]
        pomodoro.set_enabled(cfg["pomodoro"]["enabled"])
        save_config(cfg)
        pet.set_pomodoro_enabled(cfg["pomodoro"]["enabled"])
        pet.say("番茄钟开启！" if cfg["pomodoro"]["enabled"] else "番茄钟关闭，持续监督！")

    def on_toggle_mode(mode):
        pet_state.set_mode(mode)
        apply_mode(mode)
        pet.set_mode(mode)
        pet.say("考试冲刺模式！我会更严格地盯住你！"
                if mode == "exam" else "日常自习模式，放松一点~")

    def on_exit():
        if cfg["lock"]["enabled"]:
            code = simpledialog.askstring("退出", "输入退出码才能溜走！",
                                          parent=pet.root, show="*")
            if code != cfg["lock"]["exit_code"]:
                pet.say("哼，不许逃！")
                return False
        return True

    pet = PetApp(cfg, mode=pet_state.mode, inventory=inventory,
                 on_teach=on_teach,
                 on_start_study=on_start_study, on_end_study=on_end_study,
                 on_toggle_pomodoro=on_toggle_pomodoro,
                 on_mode_change=on_toggle_mode, on_exit=on_exit)
    pomodoro.on_state_change = lambda state: (
        pet.say("专注时间到！" if state == "focus" else "休息时间到啦，去喝口水吧~"))

    blocker = Blocker(pet, cfg)
    stop_event = threading.Event()

    def supervisor():
        poll = max(0.5, float(cfg["supervision"]["poll_interval_seconds"]))
        last_cat = None
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
            if cam and not cam.get("error") and cam.get("backend") != "none":
                if not cam.get("person_present"):
                    # 人不在：不计专注、不生气、不阻断
                    meter.update(False, poll)
                    pet.set_mood(0)
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

            is_distraction = cat == "distraction"
            tier = meter.update(is_distraction, poll)
            if screen_derived:
                tier = min(tier, 1)  # 画面分析是启发式，只提醒不暴力关
            pet.set_mood(meter.mood)
            session.tick(cat == "study", poll)

            # 桌宠养成：专注加经验、摸鱼扣好感、升级提示
            if cat == "study":
                pet_state.add_focus(poll)
                inventory.earn(poll)   # 专注赚币
            elif is_distraction:
                pet_state.add_distraction(poll)
            if pet_state.consume_level_up():
                pet.say(f"🎉 我升到 Lv.{pet_state.level} 啦！")
            pet.set_level(pet_state.level)

            if tier == 0:
                if last_cat == "distraction" and cat != "distraction":
                    pet.say("回来啦，继续加油！")
                elif last_cat == "away":
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
    print("桌宠已退出。晚安！")


def screen_check():
    """截图画面分析自检：截当前窗口画面并打印分析结果。"""
    from sensors.screen_analyzer import analyze_foreground
    from sensors.window_monitor import get_foreground_info
    info = get_foreground_info()
    print("当前窗口:", info)
    result = analyze_foreground(info["hwnd"] if info else None)
    print("分析结果:", result)

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

def main():
    parser = argparse.ArgumentParser(description="Focus Pet - 陪你学习也监督你学习")
    parser.add_argument("--headless-check", action="store_true", help="无界面自检核心逻辑")
    parser.add_argument("--camera-check", action="store_true", help="摄像头自检（约 5 秒）")
    parser.add_argument("--camera-setup", action="store_true", help="打开摄像头设置窗口（图形界面）")
    parser.add_argument("--screen-check", action="store_true", help="截图画面分析自检")
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
    elif args.status:
        print_status()
    elif args.log:
        print_log()
    else:
        run_app()


if __name__ == "__main__":
    main()
