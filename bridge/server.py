"""本地 HTTP 桥接服务：接收浏览器扩展上报的标签页 URL。

安全：只监听 127.0.0.1；不保存、不上传任何数据。
接口：
  POST /report {url,title}   扩展上报当前活动标签页
  POST /check  {url,title}   扩展询问是否拦截（返回 block=true/false）
  POST /teach  {url}         把某链接记为学习（教宠物 / 白名单特例）
  GET  /status               连通性检查
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from core import logbook


class BridgeState:
    """桥接服务的共享状态（挂在 ThreadingHTTPServer 上）。"""

    def __init__(self, rules):
        self.rules = rules
        self.latest = None  # {"url": str, "title": str, "ts": float}
        self.supervising = False  # 是否在学习会话中（只有学习中才拦截）


class _Handler(BaseHTTPRequestHandler):
    server_version = "FocusPetBridge/0.1"

    # ---------- 工具 ----------
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    # ---------- HTTP ----------
    def do_OPTIONS(self):
        self._send(200, {})

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/status":
            self._send(200, {"ok": True, "service": "focus-pet"})
        else:
            self._send(404, {"ok": False})

    def do_POST(self):
        state = self.server.state
        data = self._json_body()
        path = self.path.split("?")[0]
        if path == "/report":
            url = data.get("url") or ""
            if url:
                state.latest = {
                    "url": url,
                    "title": data.get("title") or "",
                    "ts": time.time(),
                }
            self._send(200, {"ok": True})
        elif path == "/check":
            cat = state.rules.classify(
                title=data.get("title") or "",
                url=data.get("url") or "",
            )
            block = (cat == "distraction") and state.supervising
            self._send(200, {"category": cat, "block": block})
        elif path == "/teach":
            url = data.get("url") or ""
            if url:
                state.rules.learn(url=url)
                logbook.log_event("teach", f"扩展教宠物: {url}")
                self._send(200, {"ok": True, "learned": url})
            else:
                self._send(400, {"ok": False, "error": "no url"})
        else:
            self._send(404, {"ok": False})

    def log_message(self, fmt, *args):
        # 安静模式：不把每个请求打印到控制台刷屏
        pass


def start_bridge(rules, port=18765):
    """启动本地桥接服务（守护线程），返回 server 对象。"""
    state = BridgeState(rules)
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    server.state = state
    thread = threading.Thread(
        target=server.serve_forever, daemon=True, name="focus-pet-bridge"
    )
    thread.start()
    return server


def get_latest_url(server):
    """返回扩展最近上报的标签页信息，无则 None。"""
    if server is None:
        return None
    try:
        return server.state.latest
    except AttributeError:
        return None