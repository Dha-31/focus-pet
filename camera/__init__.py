"""camera 包：摄像头监督（v2）。

- backends：MediaPipe（人脸 + 手部关键点，推荐）/ OpenCV（人脸 + 肤色手部，降级）
- camera_monitor：后台采集线程，不阻塞主监督循环
"""