"""tools/train_classifier.py：训练截图分类器。

用法：python tools/train_classifier.py
- 读取 dataset/study/ 与 dataset/distraction/ 的图片
- 用 screen_analyzer 提取特征（视觉 + OCR 文字 + 图案）
- 训练逻辑回归并输出准确率
- 保存到 models/screen_classifier.pkl，运行时会自动加载
"""
import glob
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from sensors.screen_analyzer import (  # noqa: E402
    analyze_image, make_feature_vector, visual_stats, video_pattern,
)


def extract_for_file(path):
    from PIL import Image
    img = Image.open(path).convert("RGB")
    stats = visual_stats(img)
    # 复用 analyze_image 拿不到中间 ocr，这里直接调用内部函数
    from sensors import screen_analyzer as sa
    ocr = sa.ocr_analyze(img)
    vp = video_pattern(img)
    feats = make_feature_vector(stats, ocr, vp)
    return feats


def main():
    import numpy as np

    study_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "dataset", "study", "*.png")))
    dist_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, "dataset", "distraction", "*.png")))
    if not study_files or not dist_files:
        print("数据不足：先运行 python tools/make_synthetic_data.py 或 "
              "python tools/collect_dataset.py 采集数据")
        sys.exit(1)

    print(f"样本数: study={len(study_files)} distraction={len(dist_files)}")
    all_files = study_files + dist_files
    labels = [0] * len(study_files) + [1] * len(dist_files)  # 0=study 1=distraction

    X = []
    print("提取特征中（OCR 需要一点时间）…")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(extract_for_file, f): f for f in all_files}
        done = 0
        for fut in as_completed(futures):
            X.append(fut.result())
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(all_files)}")

    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int64)

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    clf = LogisticRegression(max_iter=3000, C=1.0)
    clf.fit(X_train, y_train)
    pred = clf.predict(X_test)
    acc = accuracy_score(y_test, pred)
    print("\n=== 测试集准确率: %.1f%% ===" % (acc * 100))
    print(classification_report(y_test, pred, target_names=["study", "distraction"]))

    # 用全量数据再拟合一次（保存最终模型）
    clf.fit(X, y)
    import joblib
    model_path = os.path.join(PROJECT_ROOT, "models", "screen_classifier.pkl")
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(clf, model_path)
    print(f"模型已保存: {model_path}")


if __name__ == "__main__":
    main()