from machine import Pin, I2C, PWM
import time
import tcs34725
import neopixel
import bluetooth
from micropython import const

# ─────────────────────────────────────────
# BLE UART SERVICE SETUP (Nordic UART Service)
# Matches .aia UUIDs exactly:
#   Service : 6E400001-B5B3-F393-E0A9-E50E24DCCA9E
#   TX (notify, ESP32->App) : 6E400003-B5B3-F393-E0A9-E50E24DCCA9E
#   RX (write,  App->ESP32) : 6E400002-B5B3-F393-E0A9-E50E24DCCA9E
# ─────────────────────────────────────────
_UART_SERVICE_UUID = bluetooth.UUID("6E400001-B5B3-F393-E0A9-E50E24DCCA9E")
_UART_RX_CHAR_UUID = bluetooth.UUID("6E400002-B5B3-F393-E0A9-E50E24DCCA9E")  # App -> ESP32
_UART_TX_CHAR_UUID = bluetooth.UUID("6E400003-B5B3-F393-E0A9-E50E24DCCA9E")  # ESP32 -> App

_IRQ_CENTRAL_CONNECT    = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE        = const(3)

_FLAG_NOTIFY = const(0x0010)
_FLAG_WRITE  = const(0x0008)

UART_SERVICE = (
    _UART_SERVICE_UUID,
    (
        (_UART_TX_CHAR_UUID, _FLAG_NOTIFY),
        (_UART_RX_CHAR_UUID, _FLAG_WRITE),
    ),
)

class BLEUART:
    def __init__(self, ble, name="ESP32-Color"):
        self._ble  = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._tx, self._rx),) = self._ble.gatts_register_services((UART_SERVICE,))
        self._conn   = None
        self._rx_buf = b""
        self._advertise(name)
        print("BLE advertising as:", name)

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self._conn, _, _ = data
            print("BLE connected")
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self._conn = None
            self._advertise()
            print("BLE disconnected, re-advertising...")
        elif event == _IRQ_GATTS_WRITE:
            self._rx_buf += self._ble.gatts_read(self._rx)

    def _advertise(self, name="ESP32-Color"):
        name_bytes = name.encode()

        # Advertisement payload: Flags + Complete Local Name
        adv = (
            b"\x02\x01\x06"                          # Flags: LE General Discoverable, BR/EDR not supported
            + bytes([len(name_bytes) + 1, 0x09])     # AD type 0x09 = Complete Local Name
            + name_bytes
        )

        # Scan response: include full 128-bit Nordic UART Service UUID in little-endian
        # MIT BluetoothLE ConnectToDeviceWithServiceAndName needs this UUID in scan response
        # 6E400001-B5B3-F393-E0A9-E50E24DCCA9E reversed per BLE spec
        uuid_le = b"\x9e\xca\xdc\x24\x0e\xe5\xa9\xe0\x93\xf3\xb3\xb5\x01\x00\x40\x6e"
        resp = (
            bytes([len(uuid_le) + 1, 0x07])          # AD type 0x07 = Complete list of 128-bit UUIDs
            + uuid_le
        )

        self._ble.gap_advertise(100000, adv_data=adv, resp_data=resp)

    def send(self, text):
        if self._conn is not None:
            try:
                self._ble.gatts_notify(self._conn, self._tx, text.encode())
            except:
                pass

    def readline(self):
        # FIX: MIT BLE WriteStrings does NOT append \n
        # Flush entire buffer whenever data arrives
        if self._rx_buf:
            line = self._rx_buf.decode("utf-8", "ignore").strip()
            self._rx_buf = b""
            return line if line else None
        return None

    def connected(self):
        return self._conn is not None


# ─────────────────────────────────────────
# HARDWARE SETUP
# ─────────────────────────────────────────
led = neopixel.NeoPixel(Pin(23), 24)

i2c    = I2C(0, scl=Pin(22), sda=Pin(21))
sensor = tcs34725.TCS34725(i2c)

IN1 = Pin(27, Pin.OUT)
IN2 = Pin(26, Pin.OUT)
ENA = PWM(Pin(14))
ENA.freq(1000)

def motor_forward(speed):
    IN1.value(1)
    IN2.value(0)
    ENA.duty(speed)

def motor_backward(speed):
    IN1.value(0)
    IN2.value(1)
    ENA.duty(speed)

def motor_stop():
    IN1.value(0)
    IN2.value(0)
    ENA.duty(0)

def set_neopixel(r, g, b):
    for i in range(24):
        led[i] = (r, g, b)
    led.write()


# ─────────────────────────────────────────
# BLE INIT
# ─────────────────────────────────────────
ble  = bluetooth.BLE()
uart = BLEUART(ble, name="ESP32-Color")


# ─────────────────────────────────────────
# STATE
# ─────────────────────────────────────────
manual_mode = False
color       = 'nothing'
colorRGB    = (0, 0, 0)
speed       = 0

print("Ready. Waiting for BLE connection...")

# ─────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────
while True:

    # ── 1. Handle incoming BLE command from MIT App ──────────────────
    cmd = uart.readline()
    if cmd:
        print("BLE cmd:", cmd)

        if cmd == "FORWARD":
            # Matches ForwardBtn.Click → WriteStrings "FORWARD"
            manual_mode = True
            motor_forward(speed if speed > 0 else 500)

        elif cmd == "BACKWARD":
            # Matches BackwardBtn.Click → WriteStrings "BACKWARD"
            manual_mode = True
            motor_backward(speed if speed > 0 else 500)

        elif cmd == "STOP":
            # Matches StopBtn.Click → WriteStrings "STOP"
            manual_mode = True
            motor_stop()

        elif cmd == "AUTO":
            # No AUTO button in .aia but kept for future use
            manual_mode = False

        elif cmd.startswith("NEO:"):
            # Matches SetColorBtn.Click → WriteStrings "NEO:" + R + "," + G + "," + B
            try:
                parts = cmd[4:].split(",")
                set_neopixel(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception as e:
                print("Bad NEO command:", cmd, e)

    # ── 2. Read color sensor ─────────────────────────────────────────
    r, g, b, c = sensor.read_raw()

    color    = 'nothing'
    colorRGB = (0, 0, 0)

    if r > g and r > b:
        color    = 'Red'
        colorRGB = (255, 0, 0)
        speed    = 700
    elif g > r and g > b:
        color    = 'Green'
        colorRGB = (0, 255, 0)
        speed    = 500
    elif b > r and b > g:
        color    = 'Blue'
        colorRGB = (0, 0, 255)
        speed    = 300
    else:
        speed = 0   # FIX: only reset speed when no color detected

    print("R:", r, " G:", g, " B:", b, "=>", color)

    # ── 3. Auto mode: NeoPixel + motor follow sensor ─────────────────
    if not manual_mode:
        set_neopixel(*colorRGB)
        if speed > 0:
            motor_forward(speed)
        else:
            motor_stop()

    # ── 4. Send color data to MIT App ────────────────────────────────
    # Matches StringsReceived block in .aia:
    #   split(stringValues, ",") → select item 1 → compare to "Red"/"Green"/"Blue"
    #   so color name MUST be at index [1] (index 1 = second item, 1-based in MIT)
    #   Format: "DATA,<colorName>,<r>,<g>,<b>"
    #   MIT index [1] = "Red"/"Green"/"Blue" → ColorBox changes color correctly
    uart.send("DATA," + color + "," + str(r) + "," + str(g) + "," + str(b))

    time.sleep(1)
