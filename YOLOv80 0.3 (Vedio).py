from ultralytics import YOLO
import cv2, time
import numpy as np
import torch


MODEL  = "yolov8m.pt"   # جرّب "yolov8m.pt" لو بدك دقة أعلى
IMG_SZ = 960            # 640/960/1280
CONF   = 0.45           # نزلناها شوي عشان ما يفلتك
IOU    = 0.5
USE_GPU=True; USE_FP16=False  # جرّب ترجع True بعد ما تتأكد من الدقة

model = YOLO(MODEL)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

HAS_GPU = torch.cuda.is_available()
device  = 0 if HAS_GPU else "cpu"   # لو فيه GPU استخدمه، غير هيك CPU
half    = HAS_GPU                   # FP16 بس مع GPU
print(f"Using: {'CUDA:0' if HAS_GPU else 'CPU'} | FP16={half}")

t0, frames = time.time(), 0
while True:
    ok, frame = cap.read()
    if not ok:
        break

    r = model.track(
        frame,
        classes=[0],
        conf=CONF,
        iou=IOU,
        imgsz=IMG_SZ,
        device=device,
        half=half,
        persist=True,          # مهم: يخلي التتبع مستمر بين الفريمات
        tracker="bytetrack.yaml",  # إذا ما اشتغل احذف هذا السطر
        verbose=False
    )[0]
    
    vis = frame.copy()


    
    # استخراج البوكسات + IDs
    persons = 0
    confs_list = []

    
    
    
    if r.boxes is not None and len(r.boxes) > 0:
        boxes_xyxy = r.boxes.xyxy.cpu().numpy()
        boxes_conf = r.boxes.conf.cpu().numpy()

        # ids ممكن تكون None أول كم فريم
        ids = None
        if r.boxes.id is not None:
            ids = r.boxes.id.cpu().numpy().astype(int)

        for i, ((x1, y1, x2, y2), c) in enumerate(zip(boxes_xyxy, boxes_conf)):
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])

            tid = -1
            if ids is not None and i < len(ids):
                tid = int(ids[i])

            persons += 1
            confs_list.append(float(c))

            # رسم البوكس
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # كتابة الـ ID فوق الشخص
            label = f"ID:{tid} {c:.2f}" if tid != -1 else f"{c:.2f}"
            cv2.putText(vis, label, (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)


    # العدّ ومتوسط الثقة (حسب اللي رسمناه/قبلناه)
    persons = len(confs_list)
    if persons > 0:
       avg_conf = float(np.mean(confs_list))
       min_conf = float(np.min(confs_list))
    else:
        avg_conf, min_conf = 0.0, 0.0


    frames += 1
    fps = frames/(time.time()-t0)

    cv2.putText(vis, f"Persons: {persons}", (10,40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    cv2.putText(vis, f"AvgConf: {avg_conf:.2f}  Min:{min_conf:.2f}",
                (10,75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    cv2.putText(vis, f"FPS:{fps:.1f} | {IMG_SZ}px | conf>{CONF} | FP16:{half}",
                (10,110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

    cv2.imshow("YOLO Live (q to quit)", vis)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    # إذا النافذة انسكرت من زر X
    if cv2.getWindowProperty("YOLO Live (q to quit)", cv2.WND_PROP_VISIBLE) < 1:
       break


cap.release()
cv2.destroyAllWindows()
