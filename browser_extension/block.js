// 拦截页逻辑
const SERVER = "http://127.0.0.1:18765";
const params = new URLSearchParams(location.search);
const target = params.get("url") || "";

document.getElementById("url").textContent = target || "未知地址";

// 教宠物：把当前页面标记为学习，然后返回
document.getElementById("teach").addEventListener("click", async () => {
  if (!target) return;
  try {
    await fetch(SERVER + "/teach", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: target })
    });
  } catch (e) { /* Focus Pet 未运行时仍允许返回 */ }
  chrome.tabs.update({ url: target });
});

// 关掉标签页
document.getElementById("close").addEventListener("click", () => {
  chrome.tabs.getCurrent((tab) => {
    if (tab) chrome.tabs.remove(tab.id);
  });
});