// desktop/main.js：Focus Pet Electron 桌宠壳（v4.0.4）
// 透明 + 无边框 + 置顶 + 鼠标穿透；Python 通过本地 HTTP 推送状态 / 接收命令。
// 托盘：点"退出"= 最小化到托盘；托盘右键"退出"= 真正关闭。
"use strict";
const { app, BrowserWindow, ipcMain, Tray, Menu } = require("electron");
const path = require("path");
const http = require("http");

// 无独立显卡机器上用软件渲染，透明才可靠（学 Open-LLM-VTuber 桌宠模式）
app.disableHardwareAcceleration();

const PY_HOST = "127.0.0.1";
const PY_PORT = Number(process.env.FOCUS_PET_PORT || 0);
const INDEX = path.join(__dirname, "..", "ui", "web_pet", "index.html");
const TRAY_ICON = path.join(__dirname, "..", "data", "pet_icon.ico");

let win = null;
let tray = null;
let pollTimer = null;
let lastOutboxSeq = 0;
let quitting = false;

function postToPy(pathname, body) {
  if (!PY_PORT) return;
  const data = JSON.stringify(body || {});
  try {
    const req = http.request({
      host: PY_HOST, port: PY_PORT, path: pathname, method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
    }, (res) => { res.resume(); });
    req.on("error", () => {});
    req.write(data);
    req.end();
  } catch (e) {}
}

function getOutbox() {
  if (!PY_PORT || !win || win.isDestroyed()) return;
  try {
    http.get({ host: PY_HOST, port: PY_PORT, path: "/pet/outbox" }, (res) => {
      let buf = "";
      res.on("data", (c) => (buf += c));
      res.on("end", () => {
        try {
          const data = JSON.parse(buf);
          if (data && data.seq && data.seq !== lastOutboxSeq) {
            lastOutboxSeq = data.seq;
            const st = data.state || {};
            // 窗口指令（Python -> Electron）
            if (st._action === "toggle_visible") {
              if (win.isVisible()) win.hide(); else win.show();
            }
            if (st._action === "open_window" && st.window) {
              openPetWindow(st.window);
            }
            if (!win.isDestroyed()) win.webContents.send("pet:state", st);
          }
        } catch (e) {}
      });
    }).on("error", () => {});
  } catch (e) {}
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(getOutbox, 120);
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

function createWindow() {
  win = new BrowserWindow({
    x: Number(process.env.FOCUS_PET_X || 100),
    y: Number(process.env.FOCUS_PET_Y || 100),
    width: 520,
    height: 380,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    hasShadow: false,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.setAlwaysOnTop(true, "screen-saver");
  win.loadFile(INDEX);
  // 渲染进程 console 转发到 stderr（便于诊断）
  win.webContents.on("console-message", (_e, _level, message) => {
    process.stderr.write("[renderer] " + message + "\n");
  });
  // 默认鼠标穿透（学 Open-LLM-VTuber：平时不挡桌面，鼠标移到猫身上才可交互）
  win.setIgnoreMouseEvents(true, { forward: true });
  // 兜底：窗口被关闭时最小化到托盘（而不是退出）
  win.on("close", (e) => {
    if (!quitting) { e.preventDefault(); win.hide(); }
  });
  win.on("closed", () => { stopPolling(); win = null; });
}

function createTray() {
  try {
    tray = new Tray(TRAY_ICON);
    tray.setToolTip("Focus Pet 学习监督桌宠");
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: "显示桌宠", click: () => { if (win) win.show(); } },
      { type: "separator" },
      { label: "退出", click: () => { quitting = true; app.quit(); } },
    ]));
    tray.on("click", () => {
      if (!win) return;
      if (win.isVisible()) win.hide(); else win.show();
    });
  } catch (e) {
    console.error("[main] tray error:", e);
  }
}

// ---- IPC ----
ipcMain.on("pet:ready", () => startPolling());
ipcMain.on("pet:set-ignore-mouse", (_e, ignore) => {
  if (win && !win.isDestroyed()) win.setIgnoreMouseEvents(!!ignore, { forward: true });
});
ipcMain.on("pet:command", (_e, name, args) => {
  postToPy("/pet/command", { name, args });
});
// 前端"退出"= 最小化到托盘（不退出）
ipcMain.on("pet:hide-to-tray", () => {
  if (win) win.hide();
});
ipcMain.handle("pet:window-move", (_e, x, y) => {
  if (win && !win.isDestroyed()) win.setPosition(Math.round(x), Math.round(y));
});
// 辅助窗口（HTML）：设置/黑白名单/帮助/空间/商店/报告/成就
const PET_WINDOWS = {
  settings: { file: "settings.html", w: 1080, h: 980 },
  rules:    { file: "rules.html",    w: 1500, h: 900 },
  help:     { file: "help.html",     w: 1080, h: 980 },
  space:    { file: "space.html",    w: 1080, h: 1000 },
  shop:     { file: "shop.html",     w: 1080, h: 980 },
  report:   { file: "report.html",   w: 1080, h: 980 },
  achievements: { file: "achievements.html", w: 1080, h: 980 },
};
function openPetWindow(name) {
  const spec = PET_WINDOWS[name];
  if (!spec) return;
  try {
    const w = new BrowserWindow({
      width: spec.w, height: spec.h,
      backgroundColor: "#fdf6ec",
      autoHideMenuBar: true,
      webPreferences: {
        preload: path.join(__dirname, "preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
        additionalArguments: ["--py-port=" + PY_PORT],
      },
    });
    w.loadFile(path.join(__dirname, "..", "ui", "web_pet", "windows", spec.file));
  } catch (e) { console.error("[main] open window error:", e); }
}
ipcMain.on("pet:open-window", (_e, name) => openPetWindow(name));

app.whenReady().then(() => { createWindow(); createTray(); });
app.on("before-quit", () => { quitting = true; });
app.on("window-all-closed", () => {
  // 有托盘：窗口隐藏不等于退出；只有托盘"退出"或真正关闭时才退出
  if (quitting) app.quit();
});
