# =============================================================================
# config.py — Central Configuration File
# Smart IoT Parking Management System
# =============================================================================
# ✏️  EDIT THIS FILE to configure your project settings.
#     All hardware pins, WiFi credentials, and platform tokens are here.
# =============================================================================

# -----------------------------------------------------------------------------
# 1. WiFi Settings (Station Mode)
# -----------------------------------------------------------------------------
WIFI_SSID     = "Robotic WIFI"         # ← WiFi network name
WIFI_PASSWORD = "rbtWIFI@2025"         # ← WiFi password
WIFI_TIMEOUT  = 15                     # Seconds to wait before giving up

# -----------------------------------------------------------------------------
# 2. Web Server Settings
# -----------------------------------------------------------------------------
WEB_SERVER_PORT = 80                   # Port 80 = no port number needed in browser
#   Access dashboard at: http://<ESP32_IP>/
#   ESP32 IP is printed to serial console on boot

# -----------------------------------------------------------------------------
# 3. Hardware Pin Assignments (GPIO Numbers)
# -----------------------------------------------------------------------------
# Ultrasonic Sensor (HC-SR04)
ULTRASONIC_TRIG_PIN     = 5    # GPIO pin connected to TRIG
ULTRASONIC_ECHO_PIN     = 18   # GPIO pin connected to ECHO
ULTRASONIC_THRESHOLD_CM = 15   # Distance in cm — below this = vehicle detected

# IR Sensors (LOW = occupied, HIGH = free — adjust IR_INVERT if opposite)
IR_SLOT1_PIN = 34    # GPIO pin for Slot 1 IR sensor
IR_SLOT2_PIN = 35    # GPIO pin for Slot 2 IR sensor
IR_SLOT3_PIN = 36    # GPIO pin for Slot 3 IR sensor
IR_INVERT    = True  # True = LOW signal means occupied (most IR modules)

# Servo Motor (Gate Barrier)
SERVO_PIN           = 13   # GPIO pin for servo signal wire
SERVO_OPEN_DEG      = 90   # Degrees to rotate for OPEN gate
SERVO_CLOSE_DEG     = 0    # Degrees to rotate for CLOSED gate
GATE_AUTO_CLOSE_SEC = 5    # Seconds before gate auto-closes after opening

# DHT11 Sensor (Temperature & Humidity)
DHT11_PIN          = 23    # GPIO pin for DHT11 data wire
DHT11_INTERVAL_SEC = 10   # How often to read DHT11 (seconds)

# Relay Module (Parking Lights)
RELAY_PIN        = 19    # GPIO pin for relay control signal
RELAY_ACTIVE_LOW = True  # True = LOW signal turns relay ON (most relay modules)

# TM1637 7-Segment Display (Slot Counter)
TM1637_CLK_PIN    = 14   # GPIO pin for TM1637 CLK
TM1637_DIO_PIN    = 27   # GPIO pin for TM1637 DIO
TM1637_BRIGHTNESS = 5    # Display brightness (0–7)

# LCD I2C Display (System Status)
LCD_SDA_PIN  = 21    # GPIO pin for I2C SDA (data)
LCD_SCL_PIN  = 22    # GPIO pin for I2C SCL (clock)
LCD_I2C_ADDR = 0x27  # I2C address of LCD (try 0x3F if 0x27 doesn't work)
LCD_COLS     = 16    # Number of columns on the LCD
LCD_ROWS     = 2     # Number of rows on the LCD

# -----------------------------------------------------------------------------
# 4. Parking System Settings
# -----------------------------------------------------------------------------
TOTAL_SLOTS = 3    # Total number of parking slots in the system

# -----------------------------------------------------------------------------
# 5. Telegram Bot Settings
# -----------------------------------------------------------------------------
TELEGRAM_TOKEN        = "8560404304:AAFCai6tF2wOeMKD-DyZhAi1Rim-c8BLxtA"   # ← From @BotFather on Telegram
TELEGRAM_CHAT_ID      = "-5282582385"     # ← Your Telegram user/group Chat ID
TELEGRAM_POLL_INTERVAL = 2                      # Seconds between polling for new messages

# -----------------------------------------------------------------------------
# 6. Blynk Settings
# -----------------------------------------------------------------------------
BLYNK_AUTH_TOKEN = "AXLHua5Akq9qdlm3L9z4dTcq0-QaA8MF"  # ← From Blynk app project settings
BLYNK_SERVER     = "blynk.cloud"
BLYNK_PORT       = 80

# Blynk Virtual Pin Assignments — match these to your Blynk app widget setup
BLYNK_VP_GATE_BTN    = "V15"  # Button widget  → Gate open/close
BLYNK_VP_LIGHT_BTN   = "V10"  # Button widget  → Light on/off
BLYNK_VP_SLOTS       = "V11"  # Value display  → Available slots
BLYNK_VP_TEMP        = "V12"  # Value display  → Temperature °C
BLYNK_VP_HUMIDITY    = "V13"  # Value display  → Humidity %
BLYNK_VP_GATE_STATUS = "V14"  # Value display  → Gate OPEN/CLOSED

# -----------------------------------------------------------------------------
# 7. System Behaviour Flags
# -----------------------------------------------------------------------------
DEBUG_MODE = True   # True = print debug messages to serial console
AUTO_LIGHT = False  # True  = lights auto-ON when slots occupied, OFF when empty
                    # False = lights only controlled manually via Telegram/Web/Blynk

