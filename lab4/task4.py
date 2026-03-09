# send data to node-red
import network, time, ujson, math
from umqtt.simple import MQTTClient
from machine import Pin, I2C, ADC
from bmp280 import BMP280          
import mlx90614                    
from ds3231 import DS3231         

SSID       = "TP-LINK_56C612"
PASSWORD   = "06941314"
BROKER     = "test.mosquitto.org"
PORT       = 1883
CLIENT_ID  = b"esp32_random_1"
TOPIC      = b"/aupp/esp32/songhabot"
KEEPALIVE  = 30

FEVER_THRESHOLD  = 32.5    # °C
SEA_LEVEL_PA     = 101325  # standard sea-level pressure in Pa

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
    if gas >= 2600:
        return 'DANGER'
    elif gas >= 2100:
        return 'WARNING'
    return 'SAFE'

def detect_fever(body_temp):
    return 1 if body_temp >= FEVER_THRESHOLD else 0

def calc_altitude(pressure_pa):
    """Barometric formula: altitude in meters from pressure in Pa."""
    return round(44330.0 * (1.0 - (pressure_pa / SEA_LEVEL_PA) ** 0.1903), 2)

def get_timestamp(rtc):
    """Return ISO-8601 timestamp string from DS3231."""
    dt = rtc.datetime()          # [year, month, day, hour, minute, second]
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        dt[0], dt[1], dt[2], dt[3], dt[4], dt[5])

# ── main
def main():
    wifi_connect()

    # Shared I2C bus (SDA=21, SCL=22)
    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100_000)

    # Sensors
    mlx    = mlx90614.MLX90614(i2c)       # IR body temperature
    bmp    = BMP280(i2c)                  # pressure & altitude  (addr=0x76)
    rtc    = DS3231(sdapin=21, sclpin=22) # real-time clock      (addr=0x68)

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

                # ── Task 3: Fever detection (MLX90614)
                body_temp  = round(mlx.read_object_temp(),  2)
                amb_temp   = round(mlx.read_ambient_temp(), 2)
                fever_flag = detect_fever(body_temp)
                print(f"\nTask3 (Fever Detection):"
                      f"\n\tAmbient Temp: {amb_temp} °C"
                      f"\n\tBody Temp   : {body_temp} °C"
                      f"\n\tFever Flag  : {fever_flag} "
                      f"{'FEVER' if fever_flag else 'NORMAL'}")

                # ── Task 4: Pressure, Altitude & Timestamp
                pressure_pa  = bmp.pressure                    # Pa (raw)
                pressure_hpa = round(pressure_pa / 100, 2)    # convert → hPa
                altitude_m   = calc_altitude(pressure_pa)     # meters
                timestamp    = get_timestamp(rtc)             # DS3231 datetime

                print(f"\nTask4 (BMP280 + DS3231):"
                      f"\n\tPressure : {pressure_hpa} hPa"
                      f"\n\tAltitude : {altitude_m} m"
                      f"\n\tTimestamp: {timestamp}")

                # ── Publish to Node-RED / Grafana
                data = {
                    "timestamp"    : timestamp,      # DS3231 RTC
                    "avg_voltage"  : round(avg_vol, 3),
                    "risk_level"   : risk,
                    "ambient_temp" : amb_temp,
                    "body_temp"    : body_temp,
                    "fever_flag"   : fever_flag,     # 1=fever | 0=normal
                    "pressure_hpa" : pressure_hpa,   # Task 4 ↓
                    "altitude_m"   : altitude_m
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