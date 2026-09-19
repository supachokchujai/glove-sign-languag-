# ถุงมือแปลภาษามือข้างเดียว (Single-Hand Sign Language Translator Glove)

ระบบแปลภาษามือ (American Sign Language) แบบครบวงจร: ESP32 + เซนเซอร์ Flex 5 จุด + MPU6050 (IMU) → ส่งข้อมูลผ่าน UDP ในรูปแบบ JSON (60 เฟรม/ท่า) → จำแนกท่าด้วยโครงข่ายประสาทเทียมแบบ MLP → แสดงผลเป็นข้อความแบบ real-time บนเว็บแอป (Flask)

> โครงงานอุปกรณ์ช่วยเหลือ (Assistive Device) ที่พัฒนาบนพื้นฐานปัญญาประดิษฐ์ เพื่อลดอุปสรรคด้านการสื่อสารของผู้มีความบกพร่องทางการได้ยินในการใช้ชีวิตประจำวันและการมีส่วนร่วมทางสังคม
>
> **ผลการทดสอบท่าจริง: ความแม่นยำเฉลี่ย 96.02%** (ทดสอบท่าละ 30 ครั้ง) — ตอบสนองเร็ว ความหน่วงต่ำ แปลท่าเป็นข้อความได้ลื่นไหลและแม่นยำ

## ความสามารถของระบบ

จำแนกท่าทางภาษามือได้ **31 คลาส**:

- ตัวอักษรภาษามือ **A–Z** (26 ท่า)
- คำที่ใช้บ่อย: **Hello, Thank you, I love you, Yes, No** (5 ท่า)

แสดงผลการแปลเป็นข้อความบนเว็บแอปพลิเคชัน

## ฮาร์ดแวร์

| อุปกรณ์ | จำนวน | หน้าที่ |
|---|---|---|
| ESP32 (Dual-core 240 MHz, Wi-Fi 802.11 b/g/n) | 1 | อ่านค่าเซนเซอร์ + ส่งข้อมูลไร้สายผ่าน UDP |
| Flex Sensor 2.2" | 5 | ตรวจจับการงอของนิ้วทั้ง 5 นิ้ว |
| MPU6050 (IMU 6-DOF) | 1 | วัดความเร่งและมุมหมุน/เอียงของข้อมือ |

### การเชื่อมต่อขา (จากเอกสารโครงงาน)

| สัญญาณ | ขา ESP32 |
|---|---|
| Flex Sensor 1–5 | GPIO 36 (VP), 39 (VN), 34, 35, 32 |
| MPU6050 SDA (I2C) | GPIO 21 |
| MPU6050 SCL (I2C) | GPIO 22 |

## ข้อมูลและโมเดล

- **ข้อมูลต่อ 1 ท่า**: 60 เฟรม × 11 features (flex 5 + accel 3 + gyro 3) = 660 ค่า
- **การส่งข้อมูล**: UDP @ ~20 Hz (50 ms/เฟรม → 60 เฟรม ≈ 3 วินาที) ในรูปแบบ JSON
- **การเตรียมข้อมูล**: StandardScaler (standardization)
- **โมเดล**: MLP ชั้นซ่อน 2 ชั้น (256 → 128, รูปทรง funnel)
  - activation: **ReLU** (ป้องกัน vanishing gradient)
  - solver: **Adam** (Adaptive Moment Estimation), Cross-Entropy Loss
  - max_iter: 500, output: **Softmax** จำแนก 31 คลาส
- **การแบ่งข้อมูล**: Train/Test 80:20 (stratify ตามคลาส)
- **ผลการประเมิน**: ทดสอบกับท่าจริงท่าละ 30 ครั้ง → ความแม่นยำเฉลี่ย **96.02%**

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
- `FLEX_PINS` — ขา ADC ของ flex sensor (ค่าเริ่มต้นตามตารางด้านบน: GPIO 36, 39, 34, 35, 32)

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
thesis.pdf                # เอกสารประกอบโครงงาน (PDF)
```

## เอกสารประกอบ

รายละเอียดโครงงานฉบับเต็ม (134 หน้า — ทฤษฎี, การออกแบบวงจร, วิธีดำเนินงาน, ผลการทดลอง):
[thesis.pdf](thesis.pdf)

**Keywords**: Sign Language Translation Glove, Artificial Intelligence, Neural Network, ESP32, American Sign Language

## ผู้จัดทำ

- **นายศุภโชค ชูใจ** (Mr. Supachok Chujai) — รหัส 6505918
- อาจารย์ที่ปรึกษา: **Apirak Pakdeewong**
- ปีการศึกษา 2568
