// 扩展弹窗逻辑
const SERVER = "http://127.0.0.1:18765";
const statusEl = document.getElementById("status");

async function refresh() {
  try {
    const resp = await fetch(SERVER + "/status");
    const data = await resp.json();
    statusEl.textContent = data.ok ? "已连接 Focus Pet（本机）" : "未连接";
  } catch (e) {
    statusEl.textContent = "未连接：请先启动 Focus Pet";
  }
}

document.getElementById("teach").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.url) {
    statusEl.textContent = "无法读取当前页面";
    return;
  }
  try {
    await fetch(SERVER + "/teach", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: tab.url })
    });
    statusEl.textContent = "已记住！下次不再拦这个页面";
  } catch (e) {
    statusEl.textContent = "失败：请先启动 Focus Pet";
  }
});

refresh();