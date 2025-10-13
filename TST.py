import cv2, time
from ultralytics import YOLO

# ========= الإعداد =========
SOURCE = 0  # للابتوب: 0 (بدّل لاحقًا لرابط RTSP كسلسلة نصية)
TARGET_W, TARGET_H = 1280, 720
MODEL_NAME = "yolov8n.pt"  # الأصغر والأسرع؛ جرّب yolov8s.pt لاحقاً للدقة

# ========= فتح المصدر =========
def open_capture(src):
    if isinstance(src, int):
        cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_H)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    else:
        # للـ RTSP/HTTP: استخدم FFMPEG + قلّل البفر لتقليل التأخير
        cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap

cap = open_capture(SOURCE)
if not cap.isOpened():
    raise RuntimeError("Cannot open video source")

# ========= تحميل الموديل =========
model = YOLO(MODEL_NAME)  # ينزل الوزن تلقائيًا أول مرة

# ========= الحلقة الرئيسية =========
prev_t = time.time()
fps, frame_count, last_t = 0.0, 0, prev_t
person_label = "person"

while True:
    ok, frame = cap.read()
    if not ok or frame is None:
        print("Frame read failed")
        break

    # تشغيل الكشف (stream=False يرجّع النتائج مباشرة)
    results = model(frame, classes=[0], verbose=False)[0]

    persons = 0
    # رسم الصناديق لِـ person فقط
    for box in results.boxes:
        cls_id = int(box.cls[0])
        cls_name = results.names.get(cls_id, "")
        if cls_name != person_label:
            continue
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        persons += 1

        # مستطيل + لابل
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"{cls_name} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), (0, 255, 0), -1)
        cv2.putText(frame, label, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)

    # حساب الـ FPS كل 10 فريمات
    frame_count += 1
    now = time.time()
    if frame_count >= 10:
        fps = frame_count / (now - last_t)
        frame_count, last_t = 0, now

    # شريط معلومات أعلى الشاشة
    source_label = "RTSP" if isinstance(SOURCE, str) else "Webcam"
    info = f"{source_label} | YOLOv8n | FPS: {fps:.1f} | Persons: {persons}"
    cv2.putText(frame, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    cv2.imshow("YOLO Person Detection", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):   # خروج
        break
    elif key == ord('s'): # حفظ لقطة
        ts = int(time.time())
        fname = f"yolo_frame_{ts}.jpg"
        cv2.imwrite(fname, frame)
        print(f"Saved {fname}")

cap.release()
cv2.destroyAllWindows()
