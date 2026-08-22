#include <WiFi.h>
#include <WiFiUdp.h>
#include <Arduino_JSON.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// ค่าตั้งค่า WiFi / IP / ขาเซนเซอร์ / ความถี่ อยู่ที่ config.h
#include "config.h"

WiFiUDP udp;
Adafruit_MPU6050 mpu;

// ตัวแปรสำหรับเก็บค่า Offset (Calibration)
float ax_off = 0, ay_off = 0, az_off = 0;
float gx_off = 0, gy_off = 0, gz_off = 0;

// ฟังก์ชัน Calibrate
void calibrateMPU() {
  Serial.println("-> Calibrating... Keep the sensor still.");
  int samples = 200; 
  
  for (int i = 0; i < samples; i++) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    ax_off += a.acceleration.x;
    ay_off += a.acceleration.y;
    az_off += a.acceleration.z - 9.81; 
    
    gx_off += g.gyro.x;
    gy_off += g.gyro.y;
    gz_off += g.gyro.z;
    delay(10);
  }

  ax_off /= samples;
  ay_off /= samples;
  az_off /= samples;
  gx_off /= samples;
  gy_off /= samples;
  gz_off /= samples;

  Serial.println("-> Calibration Done!");
}

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  // เริ่มต้น MPU6050
  if (!mpu.begin()) {
    Serial.println(" MPU6050 Not Found");
    while (1) delay(10);
  }

  // ทำการ Calibrate ก่อนเริ่มส่งข้อมูล
  calibrateMPU();

  // เริ่มต้นเชื่อมต่อ Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n Connected!");
  Serial.println("Starting UDP data transmission...");
}

void sendData() {
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  JSONVar payload;
  
  // ค่า Flex Sensor
  JSONVar flex;
  for (int i = 0; i < 5; i++) {
    flex[i] = analogRead(FLEX_PINS[i]);
  }
  payload["flex"] = flex;

  // ค่า Accel (ลบ Offset)
  JSONVar acc;
  acc[0] = a.acceleration.x - ax_off;
  acc[1] = a.acceleration.y - ay_off;
  acc[2] = a.acceleration.z - az_off;
  payload["acc"] = acc;

  // ค่า Gyro (ลบ Offset)
  JSONVar gyro;
  gyro[0] = g.gyro.x - gx_off;
  gyro[1] = g.gyro.y - gy_off;
  gyro[2] = g.gyro.z - gz_off;
  payload["gyro"] = gyro;

  String jsonString = JSON.stringify(payload);

  // ส่งข้อมูลผ่าน UDP
  udp.beginPacket(UDP_TARGET_IP, UDP_TARGET_PORT);
  udp.print(jsonString);
  udp.endPacket();
}

void loop() {
  // ตรวจสอบว่า Wi-Fi ยังเชื่อมต่ออยู่หรือไม่
  if (WiFi.status() == WL_CONNECTED) {
    sendData();
    // หน่วงเวลาตาม config.h (ค่าเริ่มต้น 50ms ≈ 20 ครั้งต่อวินาที)
    delay(SEND_DELAY_MS); 
  } else {
    // ถ้าหลุด ให้พยายามเชื่อมต่อใหม่ (Optional)
    Serial.println("Wi-Fi Disconnected. Reconnecting...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    delay(2000);
  }
}