import cv2 # استيراد مكتبة OpenCV المسؤولة عن معالجة الصور والفيديو

# افتح الكاميرا عبر DirectShow (أنسب لمعظم كاميرات اللابتوب/USB على ويندوز)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # الرقم 0 = الكاميرا الافتراضية، لو عندك كاميرا ثانية جرب 1 أو 2

# جرّب MJPG لتقليل استهلاك CPU وتحسين السلاسة
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
# تعيين عرض الإطار (الدقة الأفقية) إلى 1280 بكسل
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280) 
# تعيين ارتفاع الإطار (الدقة العمودية) إلى 720 بكسل
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
# تعيين عدد الإطارات في الثانية (Frame Rate) إلى 30 إطار/ثانية
cap.set(cv2.CAP_PROP_FPS, 30)

# التحقق من أن الكاميرا فعلاً اشتغلت
if not cap.isOpened():
    raise RuntimeError("Cannot open webcam") # في حال ما اشتغلت يرفع خطأ

# طباعة المعلومات الفعلية التي تم قبولها من الكاميرا (قد تختلف عما حددته)
print("Opened with:",
      int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), # عرض الفيديو الحالي
      int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),  # ارتفاع الفيديو الحالي
      "fps=", cap.get(cv2.CAP_PROP_FPS)) # معدل الإطارات الحالي

# إنشاء متغيرات لحساب عدد الإطارات في الثانية (FPS)
fps, cnt, t0 = 0.0, 0, cv2.getTickCount()  # t0 = الزمن الابتدائي
tick_freq = cv2.getTickFrequency() # للحصول على التردد (عدد النبضات في الثانية)

while True:  # تكرار القراءة والعرض إلى أن يخرج المستخدم
    ok, frame = cap.read() # قراءة فريم جديد من الكاميرا
    if not ok:
        print("Frame read failed") # قراءة فريم جديد من الكاميرا
        break

    # قلب الصورة أفقيًا (مثل المراية) حتى يظهر الوجه بنفس الجهة الطبيعية
    frame = cv2.flip(frame, 1)

    # زيادة عدد الإطارات المقروءة (لأجل حساب الـ FPS)
    cnt += 1
    t1 = cv2.getTickCount() # وقت القراءة الحالي
    # إذا مرّت ثانية واحدة تقريبًا، احسب عدد الإطارات خلال هذه المدة
    if (t1 - t0) / tick_freq >= 1.0:
        fps = cnt / ((t1 - t0) / tick_freq) # FPS = عدد الإطارات ÷ الوقت
        cnt, t0 = 0, t1 # أعد التهيئة لحساب الثانية التالية

 # كتابة نص على الصورة يُظهر عدد الإطارات في الثانية (FPS)
    cv2.putText(frame, f"Webcam | FPS: {fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)# المعاملات: النص، المكان (x,y)، نوع الخط، الحجم، اللون، السمك

# عرض الإطار في نافذة بعنوان "Webcam"
    cv2.imshow("Webcam", frame)
    # انتظار ضغط مفتاح من المستخدم (1 مللي ثانية)
    key = cv2.waitKey(1) & 0xFF # قراءة المفتاح كقيمة رقمية
    if key in (27, ord('q')):   # إذا ضغط Esc أو q → خروج من الحلقة
        break

   # التحقق إذا المستخدم أغلق نافذة العرض بالزر X
    if cv2.getWindowProperty("Webcam", cv2.WND_PROP_VISIBLE) < 1:
        break
    
cap.release() # إغلاق الكاميرا وتحريرها من الاستخدام
cv2.destroyAllWindows() # إغلاق جميع نوافذ العرض المفتوحة
