from ultralytics import YOLO
import cv2

model = YOLO("yolov8s.pt")  # جرّب n أو m لو حبيت
img = "people walking street.jpg"          # حط أي صورة فيها أشخاص

results = model.predict(
    source=img,
    classes=[0],
    conf=0.5,
    imgsz=640,
    device=0,   # GPU
    half=True   # FP16
)

# عرض الصورة الناتجة وتثبيتها
cv2.imshow("Result", results[0].plot())  # plot() ترسم المربعات على الصورة
cv2.waitKey(0)  # 0 معناها انتظر ضغط أي مفتاح
cv2.destroyAllWindows()
# عرض

results[0].save(filename="output.jpg")  # حفظ
