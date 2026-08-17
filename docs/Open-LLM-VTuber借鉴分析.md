# Open-LLM-VTuber 借鉴分析（交互界面 + Live2D）

> 调研日期：2026-08-17
> 来源：用户上传 `research/open-llm-vtuber`（GitHub: Open-LLM-VTuber/Open-LLM-VTuber）
> 目的：为 Focus Pet 的「v4.0.4 交互界面升级」与「远期 Live2D」寻找可借鉴方案，重点解决已遇到的透明桌宠难题

## 一、项目是什么

开源语音交互 AI 伴侣（类 neuro-sama）：实时语音对话 + 视觉感知 + Live2D 形象，支持本地离线运行。
两种形态：**网页版**（React 单页，开源）与**桌面客户端**（Electron 壳，未开源，但前端代码里留有 `ipcRenderer` / `setIgnoreMouseEvents` 调用，可确证是 Electron）。
桌面客户端支持**窗口模式 ↔ 桌宠模式**自由切换，桌宠模式 = 透明背景 + 全局置顶 + 鼠标穿透 + 可拖拽。

技术栈：Python 后端（FastAPI 风格 server + agent/asr/tts/vad）+ React 前端 + Live2D（官方 Cubism JS 框架）+ Electron 桌宠壳。

## 二、交互界面：可借鉴点

### 1. 透明桌宠的正确实现 = Electron / Tauri，不是 pywebview（最重要）
- 桌宠模式用 Electron `BrowserWindow({ transparent: true, frame: false, alwaysOnTop: true })` + `setIgnoreMouseEvents(true, { forward: true })` 实现「透明 + 置顶 + 鼠标穿透」。
- 前端调用：`window.api.setIgnoreMouseEvent`、`ipcRenderer.send("update-component-hover", ...)`。
- **结论**：Focus Pet 之前 pywebview 透明在无独显机器上透不出来，正路是 Electron/Tauri（BongoCat 也用 Tauri）。以后做 HTML 桌宠应走这条路，不再死磕 pywebview。

### 2. 点击 / 拖拽区分（摸头精细化）
- `pointerdown/pointermove` + 两个阈值：`THRESHOLD_MS`（时间）+ `DRAG_DISTANCE_THRESHOLD_PX`（距离），区分「点击」和「拖拽」。
- 点击 → `anyhitTest` 命中检测 → `startTapMotion(命中区域, tapMotions)` 播放对应动作。
- 拖拽 → `isDragging` + `cursor: grabbing`，可把桌宠拖到屏幕任意位置。
- **对 Focus Pet**：摸头可升级为「点击区域→动作」映射（摸头 / 戳身体不同反应），并规范点击与拖拽的区分。

### 3. 鼠标悬停同步（不挡桌面 + 可交互）
- 鼠标在模型上（`isHitOnModel`）→ IPC 通知主进程切换窗口交互/穿透状态。
- 桌宠平时不挡鼠标，鼠标移到身上才可点。

### 4. 设置面板数据化
- React 侧边栏实时改模型配置（缩放 / 偏移 / 表情映射 / 点击动作），配置与代码分离。

## 三、Live2D：可借鉴点

### 1. 渲染用官方 Cubism 框架，而非 PixiJS 插件
- `LAppLive2DManager` / `LAppDelegate`（官方 Cubism Samples JS 框架），支持 `setExpression`（表情）、`startTapMotion`（点击动作）、动作优先级、点击命中、拖拽。
- 之前 Focus Pet 实验用的 PixiJS + pixi-live2d 只是其中一种方案；官方框架功能更完整。

### 2. `model_dict.json`：模型配置单一数据源（强烈建议学）
每个模型一条配置：
```json
{
  "name": "mao_pro",
  "url": "/live2d-models/mao_pro/runtime/mao_pro.model3.json",
  "kScale": 0.5,
  "initialXshift": 0, "initialYshift": 0,
  "idleMotionGroupName": "Idle",
  "emotionMap": { "neutral": 0, "anger": 2, "joy": 3, "sadness": 1, "surprise": 3 },
  "tapMotions": { "HitAreaHead": { "": 1 }, "HitAreaBody": { "": 1 } }
}
```
- 缩放、位置偏移、情绪→表情、点击区域→动作全部数据化，改模型不碰代码。

### 3. 情绪→表情「标签驱动」
- 后端输出文本内嵌 `[joy]`/`[anger]`/`[sadness]` 标签 → `Live2dModel.extract_emotion()` 提取并映射表情索引 → 前端 `setExpression`。
- `remove_emotion_keywords()` 把标签从要朗读/展示的文本里剥掉。文本与情绪完全解耦。

### 4. 全程容错
- 模型未加载完即跳过表情/动作操作；大量 try/catch——「改一个不坏一片」。

### 5. 自定义模型 + 许可
- 支持导入自定义 Live2D 模型；自带模型（shizuku / mao_pro）属 Live2D Inc. 样本数据，受单独许可约束（商业使用需额外授权）。

## 四、对 Focus Pet 的意义与落地建议

1. **立即能借鉴（Tk 版）**：
   - 情绪→表情映射数据化：扩展现有皮肤/主题配置（`theme.json`），加 `emotionMap`，按情绪选表情/动作。
   - 点击区域→动作：摸头升级为 hitTest + 区域映射（头部/身体不同反应），区分点击与拖拽。
   - hover 交互：鼠标悬停时给反馈（当前 Tk 已部分支持鼠标跟随，可加悬停状态）。
2. **透明桌宠（HTML 形态）**：若以后做 HTML 桌宠，采用 Electron/Tauri，透明 + 鼠标穿透一次性解决；pywebview 不再考虑。
3. **远期真 Live2D**：用官方 Cubism 框架 + `model_dict.json` 数据化设计；先解决「原版黄猫无现成 moc3 模型」的美术资产问题再推进。

## 五、结论一句话

交互界面抄它的「Electron/Tauri 透明桌宠 + 点击/拖拽区分 + 配置数据化」，Live2D 抄它的「官方 Cubism 框架 + model_dict 数据源 + 情绪标签驱动」——这套组合正好补齐 Focus Pet 当前卡住的透明问题和远期 Live2D 的骨架。
