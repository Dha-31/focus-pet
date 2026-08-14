"""ui/skin_face.py：检测自定义宠物图片中的人脸位置。

用于自动适配：装饰品戴在检测到的头上、表情标记贴在检测到的脸上。
返回归一化坐标 {cx, cy, r}（0-1），无人脸返回 None。

注意：不调用 landmarker.close()（实测会卡 80 秒），进程退出时由系统回收。
"""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE_MODEL = os.path.join(PROJECT_ROOT, "models", "face_landmarker.task")


def detect_face_meta(img_path):
    if not os.path.exists(FACE_MODEL):
        return None
    try:
        import cv2
        import mediapipe as mp
        import mediapipe.tasks as mp_tasks
    except Exception:
        return None
    try:
        img = cv2.imread(img_path)
        if img is None:
            return None
        h, w = img.shape[:2]
        vision = mp_tasks.vision
        landmarker = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=mp_tasks.BaseOptions(model_asset_path=FACE_MODEL),
                running_mode=vision.RunningMode.IMAGE,
                num_faces=1,
            ))
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_img)
        if not result.face_landmarks:
            return None
        pts = result.face_landmarks[0]
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        r = max((max(xs) - min(xs)) / 2.0, (max(ys) - min(ys)) / 2.0)
        return {"cx": round(cx, 4), "cy": round(cy, 4), "r": round(r, 4)}
    except Exception:
        return None