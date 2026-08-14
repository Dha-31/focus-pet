# Focus Pet 🐾

陪你学习、也监督你学习的桌面养成宠物。平时卖萌，你摸鱼时通过"情绪温度计"
逐级变生气，用动画和阻断机制管住你。

**当前状态：v1.5（可运行）**。核心为纯 Python 标准库实现，零强制依赖。

## 功能一览

**v1 已实现**
- ✅ 桌宠：透明置顶小窗，上下浮动、眨眼、按情绪变表情（开心→好奇→不耐烦→生气→暴怒）
- ✅ 情绪温度计：分心越久越生气，回到学习慢慢消气
- ✅ 活动窗口检测：标题 + 进程名（ctypes，不截图、不保存）
- ✅ 判定规则：黑名单为主 + 白名单特例 + "教宠物"
- ✅ 分级阻断：Lv1 提醒 / Lv2 动画遮挡 / Lv3 最小化（Lv4 强制关闭默认关）
- ✅ 番茄钟开关（默认关；开=25/5 循环，休息窗口解除限制）
- ✅ 声明制：开始前告诉宠物"今天学什么"，结束给总结
- ✅ 分心日志 + 会话记录

**v1.5 新增**
- ✅ **浏览器扩展（Chrome/Edge）**：URL 级黑名单/白名单特例/教宠物；打开黑名单网站会跳转拦截页
- ✅ **图片皮肤**：任意图片一键做成桌宠（`tools/make_skin.py` 自动抠图/去底/缩放）
- ✅ **本地桥接服务**：扩展与主程序通过 `127.0.0.1` 本地通信，数据不出本机

**v2 新增**
- ✅ **摄像头监督**：人脸检测 + 低头判断 + 手部检测
- ✅ **离屏学习**：低头写字/看书也算专注（宠物安静陪伴）
- ✅ **疑似玩手机**：低头 + 手在脸附近 → 宠物提醒
- ✅ **人不在**：宠物提醒"你去哪了？"，不计专注
- ✅ 模型下载工具（`tools/fetch_models.py`）
- ✅ **摄像头设置窗口**（`python main.py --camera-setup`：实时预览 + 选择前置/后置 + 一键保存）

**v2.5 新增**
- ✅ **截图画面分析（多信号）**：窗口标题/URL 判定不了时，本地截屏分析
  - OCR 文字识别（离线中文）：读到"目录/课件/代码"→学习，"直播/弹幕/攻略"→分心
  - 图案/结构：视频播放器特征、代码编辑器（深色）、文档排版密度
  - 颜色/亮度统计 + 机器学习分类器（可训练、持续提升）
  - 全程本地，不保存不上传
- ✅ 自检命令 `python main.py --screen-check`

**尚未实现**：养成进化（v3）、多档模式（v3）、UI 全面美化（V3）。

## 环境要求

- Windows 10/11 + Python 3.10+（v1 基础功能无需 pip 安装任何包）
- 浏览器拦截需要 Chrome 或 Edge（新版）

## 快速开始

```powershell
cd 本项目目录
python main.py --headless-check   # 自检核心逻辑（可选）
python main.py                     # 启动桌宠
```

桌宠出现在右下角，可拖动；**右键**有菜单：开始学习 / 结束学习 / 番茄钟开关 / 教宠物 / 退出。

其他命令：
```powershell
python main.py --camera-setup  # 打开摄像头设置窗口（图形界面）
python main.py --status   # 查看配置和最近记录
python main.py --log      # 查看分心日志时间线
```

## 启用浏览器拦截（v1.5，可选但推荐）

1. **先启动 Focus Pet**（`python main.py`），并把 `data/config.json` 的 `extension.enabled` 改成 `true`
2. 打开浏览器：
   - Chrome：地址栏输入 `chrome://extensions`
   - Edge：地址栏输入 `edge://extensions`
3. 打开右上角**"开发者模式"**
4. 点**"加载已解压的扩展程序"**，选择本项目里的 `browser_extension` 文件夹
5. 扩展图标出现后，点一下图标应显示"已连接 Focus Pet（本机）"

生效效果：
- 打开黑名单里的网站（如 bilibili.com）→ 自动跳转到拦截页
- 拦截页点"我在学习这个页面！"→ 教宠物记住，下次放行（也可用扩展弹窗的"标记为学习"）
- 浏览器窗口本身不会被最小化/关闭（只拦标签页）

## 黑名单 / 白名单（data/）

- `blacklist.json`：`urls`（域名/链接子串）、`processes`（进程名）、`titles`（标题关键词）
- `whitelist.json`：格式同上，**优先级高于黑名单**
- 示例（B 站上课）：黑名单 `urls` 写 `bilibili.com`，白名单 `urls` 写你课程视频的精确链接
- 被误判时：右键宠物"这个是学习用的！"，或扩展拦截页/弹窗里点"标记为学习"

## 皮肤系统（v1.5）

**一键生成皮肤**（推荐，自动抠图）：
```powershell
python tools/make_skin.py 你的图片.png 我的小猫
```
- 自动处理：rembg AI 抠图 →（不可用则）PIL 白色背景去除 + 缩放 → 直接复制
- 生成到 `skins/我的小猫/pet.png`，自动改配置，重启桌宠生效

**手动方式**：图片（透明 PNG 更好）存成 `skins/<名字>/pet.png`，把 `data/config.json` 的
`pet.skin` 改成 `<名字>`，重启。不配置图片就用内建程序化小猫。

## 启用摄像头监督（v2，可选）

**推荐用图形界面设置**（不用手改配置）：
```powershell
python main.py --camera-setup
```
窗口里能实时预览画面、切换前置/后置、显示"✅ 检测到人脸（推荐）"，点保存即可。

也可以手动配置：

1. 安装依赖（如果还没装）：
   ```powershell
   pip install opencv-python mediapipe
   ```
2. 下载模型（已下载过可跳过）：
   ```powershell
   python tools\fetch_models.py
   ```
3. 编辑 `data\config.json`，把 `"camera": { "enabled": false ... }` 改成 `"enabled": true`
4. 重启桌宠，控制台会显示"摄像头已启动（后端: mediapipe）"

自检（不开桌宠也能测，约 5-10 秒）：
```powershell
python main.py --camera-check
```
会打印每帧的判定：`person_present`（有人）、`head_down`（低头）、`hand_active`（手在动）、`off_screen_study`（离屏学习）、`phone_suspicion`（疑似玩手机）。

> 隐私说明：摄像头画面只在本地实时分析，**不保存、不上传**。

## 配置（data/config.json）

| 字段 | 说明 | 默认 |
|---|---|---|
| pomodoro.enabled | 番茄钟开关 | false |
| pomodoro.focus_minutes / break_minutes | 专注/休息时长 | 25 / 5 |
| blocking.tiers_seconds | 阻断升级阈值（秒） | [5, 15, 30, 60] |
| blocking.force_close_enabled | Lv4 强制关闭（慎开） | false |
| blocking.save_warning_seconds | 关闭前保存倒计时 | 10 |
| lock.enabled / lock.exit_code | 退出承诺锁 | false / "1234" |
| pet.skin | 皮肤名 | "default" |
| extension.enabled / extension.port | 浏览器扩展桥接 | false / 18765 |
| camera.enabled / device_index / interval_seconds | 摄像头开关 / 设备编号 / 采样间隔 | false / 0 / 1 |
| screen_analysis.enabled / interval_seconds | 截图分析开关 / 间隔(秒) | true / 10 |

## 项目结构

```
focus-pet/
├── main.py              # 入口：监督循环 + CLI
├── core/                # 配置 / 规则 / 情绪 / 会话 / 番茄钟 / 日志
├── sensors/             # 感知层（v1 窗口检测；v2 摄像头）
├── ui/                  # 桌宠窗口 + 皮肤
├── blockers/            # 分级阻断
├── bridge/              # 本地桥接服务（扩展 <-> 主程序）
├── browser_extension/   # Chrome/Edge 扩展（MV3）
├── tools/               # 辅助工具（make_skin.py）
├── data/                # 配置与数据（运行时生成日志）
├── docs/设计文档.md      # 完整设计
└── skins/               # 皮肤资源包
```

## 升级路线

- **v1**：✅ 桌宠 + 情绪温度计 + 黑名单/特例 + 番茄钟 + 窗口检测 + 分级阻断 + 分心日志
- **v1.5**：✅ 浏览器扩展 + ✅ 图片皮肤 + ✅ 本地桥接
- **v2**：✅ 摄像头（人脸 + 视线 + 手部：离屏学习/玩手机）+ 摄像头设置窗口
- **v2.5（当前）**：✅ 截图画面分析（本地，不保存不上传）
- **v3**：养成进化 + 好感度 + 多档模式 + UI 全面美化
- **打包分发**：PyInstaller 打包成 exe + 图形化设置界面 + 扩展上架应用商店

升级方式是**增量修改**，不推倒重来。详细设计见 [`docs/设计文档.md`](docs/设计文档.md)。

## 常见问题

- **扩展显示"未连接"？** 确认 Focus Pet 正在运行，且 `data/config.json` 的
  `extension.enabled` 为 `true`（改完要重启桌宠）。
- **拦截页反复跳转？** 教宠物后仍被拦，说明 URL 没完全匹配白名单；白名单用
  精确链接（子串匹配），确认没写错。
- **强制关闭为什么默认关？** 会丢未保存内容，建议开启后配合保存倒计时使用。
- **没装 git？** 可安装 https://git-scm.com/ 后在本目录执行 `git init`（.gitignore 已备好）。