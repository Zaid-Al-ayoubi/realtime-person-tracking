from ultralytics import YOLO
import cv2, time
import numpy as np

MODEL  = "yolov8s.pt"   # جرّب "yolov8m.pt" لو بدك دقة أعلى
IMG_SZ = 960            # 640/960/1280
CONF   = 0.35           # نزلناها شوي عشان ما يفلتك
IOU    = 0.5
USE_GPU=True; USE_FP16=False  # جرّب ترجع True بعد ما تتأكد من الدقة

model = YOLO(MODEL)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

device = 0 if USE_GPU else "cpu"
half   =  USE_FP16 and USE_GPU

t0, frames = time.time(), 0
while True:
    ok, frame = cap.read()
    if not ok: break

    r = model.predict(
        frame, classes=[0], conf=CONF, iou=IOU,
        imgsz=IMG_SZ, device=device, half=half, verbose=False
    )[0]

    # العدّ ومتوسط الثقة
    if r.boxes is not None and len(r.boxes) > 0:
        confs = r.boxes.conf.float().cpu().numpy()
        persons = len(confs)
        avg_conf = float(np.mean(confs))
        min_conf = float(np.min(confs))
    else:
        persons, avg_conf, min_conf = 0, 0.0, 0.0

    vis = r.plot()
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

cap.release()
cv2.destroyAllWindows()
