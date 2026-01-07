from ultralytics import YOLO
import cv2, time
import numpy as np
import torch

# === Models ===
PERSON_MODEL = "yolov8m.pt"
FACE_MODEL   = "face_yolov8s.pt"

# === Settings ===
IMG_SZ_PERSON = 960
IMG_SZ_FACE   = 640

CONF_PERSON = 0.45
IOU_PERSON  = 0.5

CONF_FACE = 0.35
IOU_FACE  = 0.4

WINDOW_NAME = "Person Track + Face (q to quit)"

# === Load models ===
person_model = YOLO(PERSON_MODEL)
face_model   = YOLO(FACE_MODEL)

# === Camera ===
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# === Device ===
HAS_GPU = torch.cuda.is_available()
device  = 0 if HAS_GPU else "cpu"
half    = HAS_GPU
print(f"Using: {'CUDA:0' if HAS_GPU else 'CPU'} | FP16={half}")

t0, frames = time.time(), 0

# === Face stability per TrackID ===
face_hits = {}              # id -> counter
FACE_STABLE_FRAMES = 3      # كم فريم لازم عشان نعتمد الوجه
FACE_DECAY = 1              # قديش ننقص لما ما يكون فيه وجه

while True:
    ok, frame = cap.read()
    if not ok:
        break

    H, W = frame.shape[:2]
    vis = frame.copy()

    pr = person_model.track(
        frame,
        classes=[0],
        conf=CONF_PERSON,
        iou=IOU_PERSON,
        imgsz=IMG_SZ_PERSON,
        device=device,
        half=half,
        persist=True,
        tracker="bytetrack.yaml",
        verbose=False
    )[0]

    verified_persons = 0
    confs_list = []   # فعليًا: verified_confs فقط

    if pr.boxes is not None and len(pr.boxes) > 0:
        boxes_xyxy = pr.boxes.xyxy.cpu().numpy()
        boxes_conf = pr.boxes.conf.cpu().numpy()

        ids = None
        if pr.boxes.id is not None:
            ids = pr.boxes.id.cpu().numpy().astype(int)

        for i, ((x1, y1, x2, y2), pc) in enumerate(zip(boxes_xyxy, boxes_conf)):
            x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
            tid = int(ids[i]) if (ids is not None and i < len(ids)) else -1

            x1c, y1c = max(0, x1), max(0, y1)
            x2c, y2c = min(W, x2), min(H, y2)
            crop = frame[y1c:y2c, x1c:x2c]

            has_face = False

            if crop.size > 0:
                fr = face_model.predict(
                    crop,
                    conf=CONF_FACE,
                    iou=IOU_FACE,
                    imgsz=IMG_SZ_FACE,
                    device=device,
                    half=half,
                    verbose=False
                )[0]

                if fr.boxes is not None and len(fr.boxes) > 0:
                    fxyxy = fr.boxes.xyxy.cpu().numpy()
                    for (fx1, fy1, fx2, fy2) in fxyxy:
                        fx1, fy1, fx2, fy2 = map(int, [fx1, fy1, fx2, fy2])
                        fw = fx2 - fx1
                        fh = fy2 - fy1
                        face_area = fw * fh
                        person_area = max(1, (x2c - x1c) * (y2c - y1c))

                        if face_area > 0.01 * person_area:
                            has_face = True
                            break

            # === Face stability (نهائي) ===
            if tid not in face_hits:
                face_hits[tid] = 0

            if has_face:
                face_hits[tid] += 1
            else:
                face_hits[tid] = max(0, face_hits[tid] - FACE_DECAY)

            has_face_final = face_hits[tid] >= FACE_STABLE_FRAMES

            status = "FACE" if has_face_final else "NOFACE"
            color  = (0, 255, 0) if has_face_final else (0, 200, 255)

            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
            cv2.putText(vis, f"ID:{tid} {pc:.2f} | {status}",
                        (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            if has_face_final:
                verified_persons += 1
                confs_list.append(float(pc))

    # Stats (للـ verified فقط)
    if verified_persons > 0:
        avg_conf = float(np.mean(confs_list))
        min_conf = float(np.min(confs_list))
    else:
        avg_conf, min_conf = 0.0, 0.0

    frames += 1
    fps = frames / (time.time() - t0)

    cv2.putText(vis, f"Verified Persons (FACE): {verified_persons}", (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    cv2.putText(vis, f"AvgConf: {avg_conf:.2f}  Min:{min_conf:.2f}", (10, 75),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
    cv2.putText(vis, f"FPS:{fps:.1f} | P:{IMG_SZ_PERSON}px conf>{CONF_PERSON} | F:{IMG_SZ_FACE}px conf>{CONF_FACE}",
                (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

    cv2.imshow(WINDOW_NAME, vis)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()
