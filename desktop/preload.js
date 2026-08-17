// desktop/preload.js：暴露安全桥 window.api 给前端
"use strict";
const { contextBridge, ipcRenderer } = require("electron");

// 从命令行参数注入 Python 端口（辅助窗口用）
const pyArg = process.argv.find((a) => a.startsWith("--py-port="));
const PY_PORT = pyArg ? pyArg.split("=")[1] : "";

contextBridge.exposeInMainWorld("api", {
  ready: () => ipcRenderer.send("pet:ready"),
  pyPort: PY_PORT,
  openWindow: (name) => ipcRenderer.send("pet:open-window", name),
  setIgnoreMouseEvents: (ignore) => ipcRenderer.send("pet:set-ignore-mouse", !!ignore),
  command: (name, args) => ipcRenderer.send("pet:command", name, args),
  hideToTray: () => ipcRenderer.send("pet:hide-to-tray"),
  moveWindow: (x, y) => ipcRenderer.invoke("pet:window-move", x, y),
  onState: (cb) => ipcRenderer.on("pet:state", (_e, state) => { try { cb(state); } catch (e) {} }),
});
