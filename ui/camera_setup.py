"""ui/camera_setup.py：摄像头设置窗口（图形界面）。

用法：
  python main.py --camera-setup

功能：
- 自动扫描 0-4 号摄像头，列出可用的
- 实时预览所选摄像头画面（镜像显示，像照镜子）
- 实时人脸检测：显示"✅ 检测到人脸（推荐）"或"❌ 未检测到人脸"
- 上/下一台切换，或下拉框直接选
- 点"使用这台并保存"写入 data/config.json，重启桌宠生效

隐私：画面只在本地处理，不保存、不上传。
"""
import json
import os
import time
import tkinter as tk
from tkinter import messagebox, ttk

# 减少 mediapipe 日志（需在 import mediapipe 前设置）
os.environ.setdefault("GLOG_minloglevel", "2")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "data", "config.json")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "face_landmarker.task")

MAX_SCAN_DEVICES = 5
PREVIEW_WIDTH = 560
PREVIEW_HEIGHT = 420


def scan_devices():
    """扫描可用的摄像头，返回可用设备索引列表。"""
    import cv2
    devices = []
    for idx in range(MAX_SCAN_DEVICES):
        cap = cv2.VideoCapture(idx)
        try:
            if cap.isOpened():
                ok, _ = cap.read()
                if ok:
                    devices.append(idx)
        finally:
            cap.release()
    return devices


class CameraSetupWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Focus Pet - 摄像头设置")
        self.root.geometry("640x600")
        self.root.resizable(False, False)

        self.devices = []
        self.current_idx = None
        self.cap = None
        self.face_count = 0
        self._detect_ts = 0.0
        self._preview_img = None
        self.landmarker = None

        # 人脸检测器（MediaPipe）
        try:
            import mediapipe as mp
            import mediapipe.tasks as mp_tasks
            if os.path.exists(MODEL_PATH):
                vision = mp_tasks.vision
                self.landmarker = vision.FaceLandmarker.create_from_options(
                    vision.FaceLandmarkerOptions(
                        base_options=mp_tasks.BaseOptions(model_asset_path=MODEL_PATH),
                        running_mode=vision.RunningMode.IMAGE,
                        num_faces=3,
                    ))
        except Exception:
            self.landmarker = None

        self._build_ui()
        self.devices = scan_devices()
        self._refresh_device_list()

        # 默认选中配置里的设备
        default = self._configured_index()
        if default in self.devices:
            self._select_device(default)
        elif self.devices:
            self._select_device(self.devices[0])

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._update_preview()

    # ---------- UI ----------
    def _build_ui(self):
        self.preview = tk.Label(self.root, bg="black", width=PREVIEW_WIDTH, height=PREVIEW_HEIGHT)
        self.preview.pack(padx=10, pady=(10, 4))

        self.status_var = tk.StringVar(value="正在扫描摄像头…")
        tk.Label(self.root, textvariable=self.status_var, font=("Microsoft YaHei UI", 11)).pack(pady=2)

        bar = tk.Frame(self.root)
        bar.pack(pady=6)
        tk.Button(bar, text="◀ 上一台", width=10, command=self.prev_device).pack(side="left", padx=4)
        tk.Button(bar, text="下一台 ▶", width=10, command=self.next_device).pack(side="left", padx=4)
        self.device_combo = ttk.Combobox(bar, state="readonly", width=10)
        self.device_combo.pack(side="left", padx=8)
        self.device_combo.bind("<<ComboboxSelected>>", self._on_combo)

        bottom = tk.Frame(self.root)
        bottom.pack(pady=8)
        tk.Button(bottom, text="✅ 使用这台并保存", width=18,
                  bg="#5cb85c", fg="white", command=self.save_and_close).pack(side="left", padx=6)
        tk.Button(bottom, text="退出", width=10, command=self.close).pack(side="left", padx=6)

        self.hint_var = tk.StringVar(value="提示：切换到能看到自己脸的设备，保存后重启桌宠生效")
        tk.Label(self.root, textvariable=self.hint_var, fg="#888", font=("Microsoft YaHei UI", 9)).pack(pady=(0, 8))

    # ---------- 设备切换 ----------
    def _refresh_device_list(self):
        if self.devices:
            self.device_combo["values"] = [f"设备 {i}" for i in self.devices]
        else:
            self.device_combo["values"] = []
            self.status_var.set("❌ 未找到可用摄像头")

    def _configured_index(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            return int(cfg.get("camera", {}).get("device_index", 0))
        except Exception:
            return 0

    def _select_device(self, idx):
        self._release_cap()
        self.current_idx = idx
        if idx is not None:
            try:
                import cv2
                self.cap = cv2.VideoCapture(idx)
            except Exception:
                self.cap = None
        self.face_count = 0
        self._update_status("", 0)
        if idx is not None and idx in self.devices:
            self.device_combo.set(f"设备 {idx}")

    def prev_device(self):
        if not self.devices:
            return
        cur = self.current_idx if self.current_idx in self.devices else self.devices[0]
        pos = self.devices.index(cur)
        self._select_device(self.devices[(pos - 1) % len(self.devices)])

    def next_device(self):
        if not self.devices:
            return
        cur = self.current_idx if self.current_idx in self.devices else self.devices[0]
        pos = self.devices.index(cur)
        self._select_device(self.devices[(pos + 1) % len(self.devices)])

    def _on_combo(self, _event=None):
        try:
            text = self.device_combo.get()
            idx = int(text.split()[-1])
            if idx in self.devices:
                self._select_device(idx)
        except Exception:
            pass

    # ---------- 预览 ----------
    def _update_preview(self):
        if self.cap is not None:
            ok, frame = self.cap.read()
            if ok:
                import cv2
                from PIL import Image, ImageTk
                frame = cv2.flip(frame, 1)  # 镜像
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil = Image.fromarray(rgb)
                pil = pil.resize((PREVIEW_WIDTH, PREVIEW_HEIGHT))
                self._preview_img = ImageTk.PhotoImage(pil)
                self.preview.configure(image=self._preview_img)

                # 每 ~0.8 秒跑一次人脸检测
                now = time.time()
                if now - self._detect_ts > 0.8:
                    self._detect_ts = now
                    self._detect_face(frame)
        self.root.after(50, self._update_preview)

    def _detect_face(self, frame):
        if self.landmarker is None:
            return
        try:
            import cv2
            import mediapipe as mp
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res = self.landmarker.detect(mp_img)
            self.face_count = len(res.face_landmarks)
            self._update_status("", self.face_count)
        except Exception:
            pass

    def _update_status(self, _info, face_count):
        if self.current_idx is None:
            self.status_var.set("请选择一台摄像头")
        elif face_count > 0:
            self.status_var.set(f"✅ 设备 {self.current_idx}：检测到 {face_count} 张人脸（推荐使用）")
        else:
            self.status_var.set(f"设备 {self.current_idx}：画面正常，但没检测到人脸（试试换一台）")

    # ---------- 保存 / 退出 ----------
    def save_and_close(self):
        if self.current_idx is None:
            messagebox.showinfo("Focus Pet", "请先选择一台摄像头")
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
        camera = cfg.setdefault("camera", {})
        camera["enabled"] = True
        camera["device_index"] = self.current_idx
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        messagebox.showinfo(
            "Focus Pet",
            f"已保存：使用设备 {self.current_idx}\n重启桌宠后生效。",
        )
        self.close()

    def _release_cap(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def close(self):
        self._release_cap()
        self.root.destroy()


def run():
    try:
        import cv2  # noqa: F401
    except Exception:
        messagebox.showerror("Focus Pet", "请先安装: pip install opencv-python mediapipe")
        return
    CameraSetupWindow().root.mainloop()