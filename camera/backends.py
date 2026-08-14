"""摄像头后端：优先 MediaPipe（Tasks API），降级 OpenCV。

MediaPipe 后端需要模型文件（首次使用前下载，或运行 tools/fetch_models.py）：
  models/face_landmarker.task
  models/hand_landmarker.task

状态字段说明：
- person_present   是否检测到人脸
- head_down        低头（鼻子低于眼线，可能写字/看书/玩手机）
- hand_active      检测到手
- phone_suspicion  低头 + 手在脸附近（疑似玩手机）
- off_screen_study 低头 + 手在活动且不在脸附近（疑似写字/看书）

OpenCV 降级版无法可靠判断低头，head_down 恒为 False（不误报）。
"""
import os

# 减少 mediapipe 的 INFO/WARNING 日志刷屏（需在 import mediapipe 前设置）
os.environ.setdefault("GLOG_minloglevel", "2")

try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

try:
    import mediapipe as mp
    import mediapipe.tasks as mp_tasks
    _HAS_MP = True
except Exception:
    _HAS_MP = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
FACE_MODEL = os.path.join(MODELS_DIR, "face_landmarker.task")
HAND_MODEL = os.path.join(MODELS_DIR, "hand_landmarker.task")


# ---------- MediaPipe 后端（推荐） ----------
class MediaPipeBackend:
    name = "mediapipe"

    def __init__(self):
        self.available = _HAS_MP and _HAS_CV2
        self._face = None
        self._hands = None
        if not self.available:
            return
        try:
            vision = mp_tasks.vision
            base_options = mp_tasks.BaseOptions
            self._face = vision.FaceLandmarker.create_from_options(
                vision.FaceLandmarkerOptions(
                    base_options=base_options(model_asset_path=FACE_MODEL),
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=1,
                    min_face_detection_confidence=0.5,
                ))
            self._hands = vision.HandLandmarker.create_from_options(
                vision.HandLandmarkerOptions(
                    base_options=base_options(model_asset_path=HAND_MODEL),
                    running_mode=vision.RunningMode.IMAGE,
                    num_hands=2,
                    min_hand_detection_confidence=0.5,
                ))
        except Exception as exc:
            print("[camera] MediaPipe 初始化失败（将降级 OpenCV）：", exc)
            self.available = False
            self._face = None
            self._hands = None

    def open(self, device_index):
        if not self.available:
            return None
        cap = cv2.VideoCapture(device_index)
        if not cap.isOpened():
            cap.release()
            return None
        return cap

    def process_frame(self, cap):
        ok, frame = cap.read()
        if not ok:
            return None
        frame = cv2.flip(frame, 1)  # 镜像，像照镜子一样
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        face_result = self._face.detect(mp_image)
        hands_result = self._hands.detect(mp_image)

        person_present = bool(face_result.face_landmarks)
        hand_active = bool(hands_result.hand_landmarks)
        head_down = False
        phone_suspicion = False
        nose = None

        if person_present:
            lm = face_result.face_landmarks[0]
            nose = lm[1]
            eye_y = (lm[33].y + lm[263].y) / 2.0
            if nose.y > eye_y + 0.06:
                head_down = True

        if hand_active and nose is not None:
            for hand in hands_result.hand_landmarks:
                wrist = hand[0]
                dx = abs(wrist.x - nose.x)
                dy = abs(wrist.y - nose.y)
                if dx < 0.25 and dy < 0.35:
                    phone_suspicion = True
                    break

        off_screen_study = head_down and hand_active and not phone_suspicion
        return {
            "person_present": person_present,
            "looking_at_screen": person_present and not head_down,
            "head_down": head_down,
            "hand_active": hand_active,
            "off_screen_study": off_screen_study,
            "phone_suspicion": phone_suspicion,
            "backend": self.name,
            "error": None,
        }

    def close(self, cap):
        try:
            if cap is not None:
                cap.release()
        except Exception:
            pass
        # 注意：mediapipe 的 landmarker.close() 在本机实测耗时 ~80 秒，
        # 会卡住退出，所以跳过不调用（进程退出时由操作系统回收）。


# ---------- OpenCV 降级后端（人脸 + 肤色手部粗略判断） ----------
if _HAS_CV2:
    class OpenCVBackend:
        name = "opencv"

        def __init__(self):
            self.available = True
            self._face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            self._last_gray = None

        def open(self, device_index):
            cap = cv2.VideoCapture(device_index)
            if not cap.isOpened():
                cap.release()
                return None
            return cap

        def process_frame(self, cap):
            ok, frame = cap.read()
            if not ok:
                return None
            frame = cv2.flip(frame, 1)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
            person_present = len(faces) > 0

            # 肤色分割（YCrCb）粗略估计"手部"区域
            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
            skin = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
            hand_active = cv2.countNonZero(skin) > 4000

            # 帧间运动
            motion = False
            if self._last_gray is not None:
                diff = cv2.absdiff(self._last_gray, gray)
                _, th = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                if cv2.countNonZero(th) > 8000:
                    motion = True
            self._last_gray = gray

            return {
                "person_present": person_present,
                "looking_at_screen": person_present,
                "head_down": False,          # OpenCV 无法可靠判断低头，保守不误报
                "hand_active": hand_active or motion,
                "off_screen_study": False,
                "phone_suspicion": False,
                "backend": self.name,
                "error": None,
            }

        def close(self, cap):
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
else:
    class OpenCVBackend:
        name = "opencv"
        available = False

        def open(self, device_index):
            return None

        def process_frame(self, cap):
            return None

        def close(self, cap):
            pass


def create_backend():
    """按可用性返回一个后端；都没有则返回 None。"""
    mp_backend = MediaPipeBackend()
    if mp_backend.available:
        return mp_backend
    cv_backend = OpenCVBackend()
    if cv_backend.available:
        return cv_backend
    return None