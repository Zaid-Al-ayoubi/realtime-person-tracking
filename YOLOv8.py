from ultralytics import YOLO
import cv2

model = YOLO("yolov8s.pt")  # جرّب n أو m لو حبيت
img = "people walking street.jpg"          # حط أي صورة فيها أشخاص

results = model.predict(
    source=img,
    classes=[0],
    conf=0.4,# confidence score كل ما قلننا قاعد بطلعلي اشخاص اكثر
    imgsz=1280, # resolution of the image بعد ما رفعتها احست الدقة كثير 
    device=0,   # GPU5
   # half=True   # FP16
)
5
r = results[0]
# عدل الأسماء داخل قاموس names
r.names[0] = "person"   # أو أي اسم بدك ياه

persons_count = len(r.boxes) if r.boxes is not None else 0
print("عدد الأشخاص:", persons_count)

# نرسم الصورة مع كتابة العدد عليها
vis = r.plot()
cv2.putText(vis, f"Persons: {persons_count}", (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

# عرض الصورة الناتجة وتثبيتها
cv2.imshow("Result", vis)
cv2.waitKey(0)  # 0 معناها انتظر ضغط أي مفتاح
cv2.destroyAllWindows()
# عرض

results[0].save(filename="output.jpg")  # حفظ
