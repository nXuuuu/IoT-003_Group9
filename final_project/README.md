# Photobooth — Arduino IDE Setup Guide

**Phone (Browser) → Main ESP32 → ESP32-CAM → Telegram**

---

## Files in This Package

```
ESP32CAM_Photobooth/
  └── ESP32CAM_Photobooth.ino   → Flash to ESP32-CAM

MainESP32_Photobooth/
  └── MainESP32_Photobooth.ino  → Flash to Main ESP32
                                   (index.html is embedded inside this file)
```

---

## Wiring Reference

### Main ESP32 DevKit v1

**LCD I2C 16x2**
| LCD Pin | ESP32 Pin |
|---|---|
| VCC | 3.3V |
| GND | GND |
| SDA | GPIO21 |
| SCL | GPIO22 |

**WS2812B LED Ring**
| LED Pin | ESP32 Pin |
|---|---|
| 5V | 5V (external or from board) |
| GND | GND |
| DIN | GPIO5 *(put a 330Ω resistor on this wire!)* |

**Active Buzzer**
| Buzzer Pin | ESP32 Pin |
|---|---|
| + | GPIO18 |
| GND | GND |

**HC-SR04 Ultrasonic Sensor**
| Sensor Pin | ESP32 Pin |
|---|---|
| VCC | 5V |
| GND | GND |
| TRIG | GPIO27 |
| ECHO | GPIO14 |

> ECHO outputs 5V — use a 1kΩ/2kΩ voltage divider to bring it to ~3.3V for the ESP32 input.

### ESP32-CAM

**FTDI Adapter (for uploading firmware)**
| FTDI | ESP32-CAM |
|---|---|
| 5V | 5V |
| GND | GND |
| TX | U0R (GPIO3) |
| RX | U0T (GPIO1) |
| — | GPIO0 → GND *only during upload, remove after!* |

**Normal Operation**
- Power via **5V 2A** supply *(keep separate from Main ESP32)*
- Flash LED is onboard (GPIO4) — no extra wiring needed

---

## Step 1 — Install Arduino IDE

Download from: [https://www.arduino.cc/en/software](https://www.arduino.cc/en/software)

Install and open it.

---

## Step 2 — Add ESP32 Board Package

1. Open Arduino IDE → **File → Preferences**
2. In **"Additional Boards Manager URLs"** paste:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Click **OK**
4. Go to **Tools → Board → Boards Manager**
5. Search `esp32` → Install **"esp32 by Espressif Systems"** *(takes a few minutes)*

---

## Step 3 — Install Required Libraries

Go to **Tools → Manage Libraries**

| Library | Author | Board |
|---|---|---|
| LiquidCrystal I2C | Frank de Brabander | Main ESP32 |
| Adafruit NeoPixel | Adafruit | Main ESP32 |

> **Note:** `WiFi`, `WebServer`, `HTTPClient`, `Wire`, and `esp_camera` are all bundled with the ESP32 Arduino core — no separate install needed.

---

## Step 4 — Fill In Your Config Values

**`ESP32CAM_Photobooth.ino`** — edit the top section:

```cpp
WIFI_SSID     = "your network name"
WIFI_PASSWORD = "your password"
BOT_TOKEN     = "your Telegram bot token"
CHAT_ID       = "your Telegram group chat ID"
               // Groups have a negative ID e.g. -1001234567890
```

**`MainESP32_Photobooth.ino`** — edit the top section:

```cpp
WIFI_SSID     = "your network name"
WIFI_PASSWORD = "your password"
ESP32CAM_IP   = // leave as-is for now, set after Step 6
NUM_LEDS      = // change to match your actual LED ring count
```

---

## Step 5 — Upload to ESP32-CAM *(do this first)*

> See the [Wiring Reference](#-wiring-reference) at the top for FTDI adapter wiring before proceeding.

### Upload Steps

1. **Tools → Board** → `"AI Thinker ESP32-CAM"`
2. **Tools → Port** → select your FTDI COM port
3. **Tools → Upload Speed** → `115200` *(try lower if upload fails)*
4. Open `ESP32CAM_Photobooth.ino` and click **Upload**
5. When you see `Connecting........___` in the output, press and hold **RESET** on the ESP32-CAM, then release — upload should start
6. Wait for **"Done uploading"**
7. **Remove** the GPIO0 → GND wire
8. Open **Serial Monitor** (Tools → Serial Monitor), set **115200 baud**
9. Press **RESET** on the ESP32-CAM
10. Watch for the IP address e.g. `ESP32-CAM IP: 192.168.1.101`
11. **Copy that IP** — you need it in the next step

---

## Step 6 — Set the Cam IP in Main ESP32 Sketch

1. Open `MainESP32_Photobooth.ino`
2. Find:
   ```cpp
   const char* ESP32CAM_IP = "192.168.x.x";
   ```
3. Replace with the IP you just copied, e.g. `"192.168.1.101"`
4. Save the file

---

## Step 7 — Upload to Main ESP32

1. Connect Main ESP32 DevKit to PC via USB
2. In Arduino IDE:
   - **Tools → Board** → `"ESP32 Dev Module"`
   - **Tools → Port** → select the Main ESP32 COM port
3. Open `MainESP32_Photobooth.ino` and click **Upload**
4. Open **Serial Monitor** at **115200 baud**
5. Reset the board — watch for `"Server ready: http://..."`
6. The LCD will display the IP address

---

## Step 8 — Every Time You Use It

1. Power on **ESP32-CAM** first
2. Power on **Main ESP32**
3. Wait for LCD to show the IP address
4. On your phone — connect to the **same WiFi network**
5. Open browser → type the IP shown on LCD (e.g. `http://192.168.1.100`)
6. Tap **"3 sec"** or **"5 sec"** to start a countdown
7. Photo is taken and sent to Telegram!

---

## Troubleshooting

<details>
<summary><strong>LCD blank</strong></summary>

Check SDA/SCL wiring. Run an I2C scan in Serial Monitor:

```cpp
#include <Wire.h>
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      Serial.println(addr, HEX);
    }
  }
}
void loop() {}
```

You should see `0x27` or `0x3F`. Update `LCD_ADDR` in the sketch to match.
</details>

<details>
<summary><strong>LEDs not working</strong></summary>

Check 5V power, data wire on GPIO5, and the 330Ω resistor. Make sure `NUM_LEDS` matches your actual ring count.
</details>

<details>
<summary><strong>Camera init failed</strong></summary>

Make sure you selected **"AI Thinker ESP32-CAM"** as the board. Try a lower upload speed (**Tools → Upload Speed → 115200**).
</details>

<details>
<summary><strong>Telegram send failing</strong></summary>

- Double-check `BOT_TOKEN` (no spaces, copy exactly)
- `CHAT_ID` for groups is negative e.g. `-1001234567890`
- ESP32-CAM must be on the same WiFi with internet access
</details>

<details>
<summary><strong>Upload stuck at "Connecting..."</strong></summary>

Make sure GPIO0 is connected to GND during upload. Press RESET when you see the dots `........___`
</details>

<details>
<summary><strong>"CAM Error!" on LCD</strong></summary>

Confirm `ESP32CAM_IP` in `MainESP32_Photobooth.ino` is correct. Make sure ESP32-CAM is powered on and connected to WiFi first.
</details>

---

## How It Works

```
Browser tap "3 sec" or "5 sec"
    ↓
Browser sends: GET /start_countdown?value=3
    ↓
Main ESP32: LCD + LEDs + Buzzer count 3..2..1
    ↓
Main ESP32 sends: GET http://<ESP32CAM_IP>/capture
    ↓
ESP32-CAM: Flash → Capture JPEG
    ↓
ESP32-CAM: HTTPS POST to Telegram API
    ↓
📨 Photo appears in your Telegram group!
```
