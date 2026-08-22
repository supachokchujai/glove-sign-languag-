# ถุงมือแปลภาษามือ (Single-Hand Sign Language Translator Glove)

ระบบแปลภาษามือแบบครบวงจร: ESP32 + เซนเซอร์ Flex 5 จุด + MPU6050 (IMU) →
ส่งข้อมูลผ่าน UDP → เก็บข้อมูล → ฝึกโมเดล MLP → แปลผลแบบ real-time ผ่าน
terminal และเว็บแอป (Flask)

## สถาปัตยกรรม

```
ESP32 (sketch_feb11a/main/main.ino) --UDP JSON (60 เฟรม/ท่า)--> Python

  savedata1.py         เก็บข้อมูล (เวลา/เฟรม/label)
  convert_dataset.py   แปลง JSON -> .npz (เล็กและโหลดเร็ว)
  train_model3.py      ฝึก MLP (256-128) -> .pkl + scaler
  monitor_glove.py     ดูค่าเซนเซอร์ดิบแบบ real-time
  monitor_predict.py   ดูการ predict แบบ real-time (sliding window)
  web.py               เว็บแอปแปลท่าทาง (Flask)
```

ข้อมูล: 60 เฟรม × 11 features ต่อ sample (flex 5 + acc 3 + gyro 3)

## การตั้งค่า

### 1. Python (ฝั่งคอมพิวเตอร์)

```bash
pip install -r requirements.txt
```

ค่าทุกอย่าง (UDP port, path ไฟล์, จำนวนเฟรม) อยู่ที่ **`config.py`** ที่เดียว

### 2. Arduino (ฝั่งถุงมือ)

แก้ค่าใน **`sketch_feb11a/main/config.h`** ที่เดียว:
- `WIFI_SSID` / `WIFI_PASSWORD` — เครือข่าย WiFi
- `UDP_TARGET_IP` — IP คอมพิวเตอร์ที่รัน Python (หาได้จาก `ipconfig` / `ip addr`)
- `UDP_TARGET_PORT` — ต้องตรงกับ `UDP_PORT` ใน `config.py`
- `SEND_DELAY_MS` — ความถี่ส่ง (50 ms ≈ 20 Hz → 60 เฟรมใช้เวลาประมาณ 3 วินาที)
  ⚠️ ถ้าเปลี่ยนความถี่ ต้องเก็บข้อมูลและฝึกโมเดลใหม่
- `FLEX_PINS` — ขา ADC ของ flex sensor

## ขั้นตอนการใช้งาน

### 1. เก็บข้อมูล

```bash
python savedata1.py
```

- กด **Enter** เพื่อบันทึก 1 sample (ทำท่าค้างไว้ ~3 วินาที)
- พิมพ์ **`l <label>`** เพื่อสลับ label ระหว่าง session (เช่น `l hello`)
- พิมพ์ **`q`** เพื่อออก

โปรแกรมจะรายงานเวลาและอัตราเฟรมจริงของแต่ละ sample ถ้าสัญญาณขาด
(ไม่มี packet เกิน 0.5 วิ) หรือใช้เวลาเกิน 6 วิ จะยกเลิก sample นั้นอัตโนมัติ
(แทนที่จะนับ packet ไปเรื่อย ๆ อย่างเดิม)

### 2. แปลง dataset เป็น .npz (แนะนำ)

```bash
python convert_dataset.py
```

ลดขนาดจาก ~27 MB (JSON) เหลือ ~2 MB และโหลดเร็วกว่ามาก
`train_model3.py` จะใช้ไฟล์ .npz อัตโนมัติถ้ามี
(ถ้าเครื่องมี stdlib `zipfile` เสีย จนสร้าง .npz ไม่ได้ สคริปต์จะบันทึกเป็น
`dynamic_data_60fnew.joblib` แทน — โหลดด้วย `train_model3.py` ได้เหมือนกัน)

### 3. ฝึกโมเดล

```bash
python train_model3.py
```

บันทึก `smart_glove_model_dynamic2.pkl` + `scaler_dynamic2.pkl`
และสร้าง `confusion_matrix.png`

### 4. ทดสอบ real-time

```bash
python monitor_glove.py      # ดูค่าเซนเซอร์ดิบ
python monitor_predict.py    # ดูการ predict (sliding window)
```

⚠️ โปรแกรมที่ bind UDP port 4210 รันพร้อมกันไม่ได้ — รันทีละตัว

### 5. เว็บแอป

```bash
python web.py
```

เปิด `http://localhost:5000` — กดปุ่ม (หรือ Enter) แล้วทำท่าค้างไว้
**3 วินาที** (60 เฟรม @ ~20 Hz) ระบบจะแสดงคำแปล

## ทดสอบ

```bash
python -m unittest discover -s tests -v
```

## โครงสร้างไฟล์

```
config.py                 # ค่าตั้งค่ากลาง (UDP, path, เฟรม)
glove_utils.py            # helper สร้าง frame vector จาก UDP payload
savedata1.py              # เก็บข้อมูล
convert_dataset.py        # แปลง JSON -> .npz
train_model3.py           # ฝึกโมเดล
monitor_glove.py          # monitor เซนเซอร์ดิบ
monitor_predict.py        # monitor การ predict
web.py                    # เว็บแอป
templates/index.html      # หน้าเว็บ
sketch_feb11a/main/       # Firmware ESP32 (main.ino + config.h)
tests/                    # unit tests
```
