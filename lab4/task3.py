# send data to node-red
import network, time, ujson
from umqtt.simple import MQTTClient
from machine import Pin, I2C, ADC
import mlx90614                          # ← MLX90614 MicroPython driver

SSID = "TP-LINK_56C612"
PASSWORD = "06941314"
BROKER     = "test.mosquitto.org"
PORT       = 1883
CLIENT_ID  = b"esp32_random_1"
TOPIC      = b"/aupp/esp32/songhabot"
KEEPALIVE  = 30

FEVER_THRESHOLD = 32.5   # °C  (object/skin temperature)

# ── helpers
def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                raise RuntimeError("Wi-Fi connect timeout")
            time.sleep(0.3)
    print("WiFi OK:", wlan.ifconfig())
    return wlan

def make_client():
    return MQTTClient(client_id=CLIENT_ID, server=BROKER,
                      port=PORT, keepalive=KEEPALIVE)

def connect_mqtt(c):
    time.sleep(0.5)
    c.connect()
    print("MQTT connected")

def average(lst):
    return sum(lst) / len(lst)

def risk_level(gas=0):
    if gas >= 2600:          # DANGER must be checked first
        return 'DANGER'
    elif gas >= 2100:
        return 'WARNING'
    return 'SAFE'

def detect_fever(body_temp):
    """Return 1 if fever (body_temp ≥ FEVER_THRESHOLD), else 0."""
    return 1 if body_temp >= FEVER_THRESHOLD else 0

# ── main
def main():
    wifi_connect()

    # MLX90614 — I2C on the default ESP32 pins (SDA=21, SCL=22)
    i2c    = I2C(0, scl=Pin(22), sda=Pin(21), freq=100_000)
    sensor = mlx90614.MLX90614(i2c)

    # MQ-5 gas sensor on GPIO 33
    mq5 = ADC(Pin(33))
    mq5.atten(ADC.ATTN_11DB)
    mq5.width(ADC.WIDTH_12BIT)

    vol_data = []
    client   = make_client()

    while True:
        try:
            connect_mqtt(client)
            while True:

                # ── Task 1: Gas sensor
                gas_value = mq5.read()
                voltage   = (gas_value / 4095) * 3.3

                vol_data.insert(0, voltage)
                if len(vol_data) > 5:
                    vol_data = vol_data[:5]
                avg_vol = average(vol_data)

                print(f"\nTask1: Raw VS Average voltages:"
                      f"\n\tRaw    : {round(voltage,  3)} V"
                      f"\n\tAverage: {round(avg_vol, 3)} V")

                # ── Task 2: Gas risk level
                risk = risk_level(gas_value)
                print(f"\nTask2:\n\tRisk Level: {risk}")

                # ── Task 3: Fever detection via MLX90614
                body_temp  = round(sensor.read_object_temp(),  2)   # skin / object temp
                amb_temp   = round(sensor.read_ambient_temp(), 2)   # ambient / room temp
                fever_flag = detect_fever(body_temp)

                print(f"\nTask3 (MLX90614 Fever Detection):"
                      f"\n\tAmbient Temp: {amb_temp} °C"
                      f"\n\tBody Temp   : {body_temp} °C"
                      f"\n\tFever Flag  : {fever_flag}  "
                      f"{'FEVER' if fever_flag else 'NORMAL'}")

                # ── Publish to Node-RED
                data = {
                    "avg_voltage" : round(avg_vol, 3),
                    "risk_level"  : risk,
                    "ambient_temp": amb_temp,
                    "body_temp"   : body_temp,
                    "fever_flag"  : fever_flag     # 1 = fever  |  0 = normal
                }
                msg = ujson.dumps(data)
                client.publish(TOPIC, msg)
                print("\nSent:", msg)

                time.sleep(2)

        except OSError as e:
            print("MQTT error:", e)
            try:
                client.close()
            except:
                pass
            print("Retrying MQTT in 3s...")
            time.sleep(3)

main()