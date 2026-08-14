"""摄像头采集线程：后台持续读帧，主程序只取最新状态，不被阻塞。"""
import threading
import time

EMPTY_STATE = {
    "person_present": False,
    "looking_at_screen": False,
    "head_down": False,
    "hand_active": False,
    "off_screen_study": False,
    "phone_suspicion": False,
    "backend": "none",
    "error": None,
}


class CameraMonitor:
    def __init__(self, backend=None, device_index=0, interval=1.0):
        """backend 可为 None：会在后台线程里自动创建，避免阻塞桌宠启动。"""
        self.backend = backend
        self.device_index = device_index
        self.interval = max(0.2, float(interval))
        self._lock = threading.Lock()
        self._latest = dict(EMPTY_STATE)
        if backend is not None:
            self._latest["backend"] = backend.name
        self._stop = threading.Event()
        self._thread = None

    def _set_error(self, message):
        with self._lock:
            self._latest["error"] = message

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="focus-pet-camera")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def get_latest(self):
        with self._lock:
            return dict(self._latest)

    def _run(self):
        # 后台创建后端（模型加载较慢，不阻塞主线程）
        if self.backend is None:
            try:
                from camera.backends import create_backend
                self.backend = create_backend()
            except Exception as exc:
                self._set_error(f"摄像头后端初始化失败: {exc}")
                return
        if self.backend is None:
            self._set_error("未安装 opencv/mediapipe，请运行: pip install opencv-python mediapipe")
            return
        with self._lock:
            self._latest["backend"] = self.backend.name
        cap = self.backend.open(self.device_index)
        if cap is None:
            self._set_error(f"无法打开摄像头（设备索引 {self.device_index}）")
            return
        try:
            while not self._stop.is_set():
                state = self.backend.process_frame(cap)
                if state is not None:
                    with self._lock:
                        self._latest.update(state)
                        self._latest["error"] = None
                time.sleep(self.interval)
        finally:
            self.backend.close(cap)