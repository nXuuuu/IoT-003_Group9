# =============================================================================
# README.md — Setup & Deployment Guide
# Smart IoT Parking Management System
# ESP32 + MicroPython
# =============================================================================

# ─────────────────────────────────────────────
# STEP 1 — Flash MicroPython onto your ESP32
# ─────────────────────────────────────────────

1. Download the latest MicroPython firmware for ESP32:
   https://micropython.org/download/esp32/

2. Install esptool:
   pip install esptool

3. Erase flash:
   esptool.py --chip esp32 --port COM3 erase_flash
   (replace COM3 with your actual port, e.g. /dev/ttyUSB0 on Linux/Mac)

4. Flash firmware:
   esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 esp32-xxxx.bin


# ─────────────────────────────────────────────
# STEP 2 — Install Thonny IDE (recommended)
# ─────────────────────────────────────────────

Download from: https://thonny.org/
In Thonny: Tools → Options → Interpreter → MicroPython (ESP32) → Select your port


# ─────────────────────────────────────────────
# STEP 3 — Download required library files
# ─────────────────────────────────────────────

Download these files and upload them to ESP32 root (/):

a) TM1637 driver:
   https://raw.githubusercontent.com/mcauser/micropython-tm1637/master/tm1637.py
   Save as: tm1637.py

b) LCD I2C drivers (2 files needed):
   https://raw.githubusercontent.com/dhylands/python_lcd/master/lcd/lcd_api.py
   https://raw.githubusercontent.com/dhylands/python_lcd/master/lcd/i2c_lcd.py
   Save as: lcd_api.py and i2c_lcd.py


# ─────────────────────────────────────────────
# STEP 4 — Configure your settings
# ─────────────────────────────────────────────

Open config.py and fill in ALL of the following:

  WIFI_SSID          = "Your network name"
  WIFI_PASSWORD      = "Your password"
  TELEGRAM_TOKEN     = "Token from @BotFather"
  TELEGRAM_CHAT_ID   = "Your chat ID (get from @userinfobot)"
  BLYNK_AUTH_TOKEN   = "Token from Blynk app"

Then verify all GPIO pin numbers match your physical wiring.


# ─────────────────────────────────────────────
# STEP 5 — Set up Telegram Bot
# ─────────────────────────────────────────────

1. Open Telegram, search for @BotFather
2. Send /newbot and follow instructions
3. Copy the API token into config.py TELEGRAM_TOKEN
4. Get your Chat ID: search @userinfobot, send /start, copy your ID
5. Paste into config.py TELEGRAM_CHAT_ID


# ─────────────────────────────────────────────
# STEP 6 — Set up Blynk App
# ─────────────────────────────────────────────

1. Download Blynk app (iOS or Android)
2. Create account at blynk.cloud
3. Create new template → choose ESP32
4. Add these widgets and assign virtual pins:

   Widget          | Type          | Virtual Pin
   ─────────────── | ───────────── | ───────────
   Gate Control    | Button        | V0
   Light Control   | Button        | V1
   Available Slots | Value Display | V2
   Temperature     | Value Display | V3
   Humidity        | Value Display | V4
   Gate Status     | Value Display | V5

5. Copy Auth Token from device settings into config.py BLYNK_AUTH_TOKEN


# ─────────────────────────────────────────────
# STEP 7 — Wire up hardware
# ─────────────────────────────────────────────

Component          | ESP32 Pin | Notes
────────────────── | ───────── | ──────────────────────────────
Ultrasonic TRIG    | GPIO 5    | 3.3V logic OK
Ultrasonic ECHO    | GPIO 18   | Use voltage divider if 5V sensor
IR Sensor 1        | GPIO 34   | Input only pin
IR Sensor 2        | GPIO 35   | Input only pin
IR Sensor 3        | GPIO 36   | Input only pin
Servo Signal       | GPIO 13   | PWM capable pin
DHT11 Data         | GPIO 4    | Add 10K pull-up to 3.3V
Relay IN           | GPIO 12   |
TM1637 CLK         | GPIO 14   |
TM1637 DIO         | GPIO 27   |
LCD SDA            | GPIO 21   | Hardware I2C SDA
LCD SCL            | GPIO 22   | Hardware I2C SCL

All GND → ESP32 GND
All 3.3V/5V → Appropriate power rail


# ─────────────────────────────────────────────
# STEP 8 — Upload all files to ESP32
# ─────────────────────────────────────────────

Upload these files to the ESP32 root directory (/):
  main.py
  config.py
  state.py
  hardware.py
  telegram_bot.py
  web_server.py
  blynk_client.py
  tm1637.py          (downloaded in Step 3)
  lcd_api.py         (downloaded in Step 3)
  i2c_lcd.py         (downloaded in Step 3)


# ─────────────────────────────────────────────
# STEP 9 — Run and verify
# ─────────────────────────────────────────────

1. Open Thonny serial monitor (bottom panel)
2. Press Reset on ESP32 or click Run main.py
3. You should see:
     ══════════════════════════════════════════
       Smart IoT Parking Management System
       ESP32 + MicroPython
     ══════════════════════════════════════════
     [WiFi] Connecting to 'YourNetwork'...
     [WiFi] Connected! IP: 192.168.x.x
     [Web] Dashboard: http://192.168.x.x/
     [Main] System ready. Entering main loop...

4. Open browser: http://<IP shown in serial>
5. Send /status to your Telegram bot
6. Check Blynk app for live data


# ─────────────────────────────────────────────
# TROUBLESHOOTING
# ─────────────────────────────────────────────

Problem: LCD not showing anything
→ Try changing LCD_I2C_ADDR to 0x3F in config.py
→ Check SDA/SCL wiring

Problem: Servo jitters or doesn't move
→ Adjust SERVO_OPEN_DEG and SERVO_CLOSE_DEG in config.py
→ Ensure servo has dedicated 5V power (not from ESP32 3.3V)

Problem: IR sensors always show occupied
→ Set IR_INVERT = False in config.py
→ Check sensor module's sensitivity potentiometer

Problem: Telegram not responding
→ Verify TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in config.py
→ Make sure ESP32 has internet access (ping test via REPL)

Problem: Blynk data not updating
→ Verify BLYNK_AUTH_TOKEN in config.py
→ Check virtual pin numbers match Blynk app setup

Problem: Memory error on ESP32
→ Set DEBUG_MODE = False in config.py
→ Increase TELEGRAM_POLL_INTERVAL and Blynk intervals


# ─────────────────────────────────────────────
# FILE OVERVIEW
# ─────────────────────────────────────────────

  config.py       — ⚙️  ALL settings here (WiFi, pins, tokens)
  state.py        — 📊 Shared live system state
  hardware.py     — 🔧 All sensor/actuator drivers
  telegram_bot.py — ✈️  Telegram bot commands & notifications
  web_server.py   — 🌐 ESP32-hosted web dashboard
  blynk_client.py — 📱 Blynk app integration
  main.py         — 🚀 Entry point & main loop
