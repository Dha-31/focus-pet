"""tools/fetch_models.py：下载 MediaPipe 人脸/手部模型。

摄像头（v2）首次使用前运行一次：
  python tools/fetch_models.py
模型会保存到项目根目录的 models/ 文件夹（约 11MB）。
"""
import os
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

URLS = {
    "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "hand_landmarker.task": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}


def main():
    os.makedirs(MODELS_DIR, exist_ok=True)
    for name, url in URLS.items():
        path = os.path.join(MODELS_DIR, name)
        if os.path.exists(path) and os.path.getsize(path) > 100000:
            print(f"已存在: {name}（{os.path.getsize(path)} 字节）")
            continue
        print(f"下载中: {name}")
        urllib.request.urlretrieve(url, path)
        print(f"完成: {name}（{os.path.getsize(path)} 字节）")
    print("模型就绪：", MODELS_DIR)


if __name__ == "__main__":
    main()