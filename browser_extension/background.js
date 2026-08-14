// Focus Pet Bridge - 后台服务
// 监听标签页变化，把 URL 上报给本地 Focus Pet，并拦截黑名单网站。

const SERVER = "http://127.0.0.1:18765";

function isHttpUrl(url) {
  return typeof url === "string" && /^https?:\/\//i.test(url);
}

async function post(path, payload) {
  try {
    const resp = await fetch(SERVER + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    return await resp.json();
  } catch (e) {
    return null; // Focus Pet 未运行等情况：安静失败
  }
}

function report(url, title) {
  if (!isHttpUrl(url)) return;
  post("/report", { url: url, title: title || "" });
}

async function checkAndBlock(tabId, url, title) {
  if (!isHttpUrl(url)) return;
  const data = await post("/check", { url: url, title: title || "" });
  if (data && data.block === true) {
    // 防循环：仅当标签页仍停留在这个被拦截的地址时才重定向
    chrome.tabs.get(tabId, (tab) => {
      if (chrome.runtime.lastError || !tab) return;
      if (tab.url === url || tab.pendingUrl === url) {
        const blockUrl = chrome.runtime.getURL("block.html") +
          "?url=" + encodeURIComponent(url);
        chrome.tabs.update(tabId, { url: blockUrl });
      }
    });
  }
}

chrome.tabs.onActivated.addListener((info) => {
  chrome.tabs.get(info.tabId, (tab) => {
    if (chrome.runtime.lastError || !tab) return;
    report(tab.url, tab.title);
    checkAndBlock(info.tabId, tab.url, tab.title);
  });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    report(changeInfo.url, tab ? tab.title : "");
    checkAndBlock(tabId, changeInfo.url, tab ? tab.title : "");
  }
});