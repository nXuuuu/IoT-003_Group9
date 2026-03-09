# send data to node-red

import network, time, ujson
from umqtt.simple import MQTTClient
from machine import Pin, I2C, ADC
#from bmp280 import BMP280

SSID = "TP-LINK_56C612"
PASSWORD = "06941314"

BROKER = "test.mosquitto.org"
PORT = 1883
CLIENT_ID = b"esp32_random_1"
TOPIC = b"/aupp/esp32/songhabot"
KEEPALIVE = 30


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
    return MQTTClient(client_id=CLIENT_ID, server=BROKER, port=PORT, keepalive=KEEPALIVE)


def connect_mqtt(c):
    time.sleep(0.5)
    c.connect()
    print("MQTT connected")

def average(l):
    return sum(l)/len(l)

def risk_level(gas=0):
    risk = 'SAFE'
    if gas >= 2100:
        risk = 'WARNING'
    elif gas >= 2600:
        risk = 'DANGER'
    return risk

def main():
    wifi_connect()

    # Setup BMP280
    #i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    #sensor = BMP280(i2c)
    
    # task 1
    # Configure ADC pin
    mq5 = ADC(Pin(33))
    mq5.atten(ADC.ATTN_11DB)      
    mq5.width(ADC.WIDTH_12BIT)
    
    vol_data = []
    
        
    client = make_client()
    while True:
        try:
            connect_mqtt(client)
            while True:
    
                '''data = {
                    "temperature": round(sensor.temperature, 2),
                    "pressure": round(sensor.pressure / 100, 2),
                    "altitude": round(sensor.altitude, 2)
                }'''
                
                #task1
                gas_value = mq5.read()
                voltage = (gas_value / 4095) * 3.3
                
                vol_data.insert(0, voltage)
                if len(vol_data) > 5:
                    vol_data = vol_data[0:5]
                avg_vol = average(vol_data)
                print(f"\nTask1: Raw VS Average voltages: \n\tRaw: {round(voltage, 3)}V \n\tAverage: {round(avg_vol, 3)}V")
                
                #task2
                risk = risk_level(gas_value)
                print(f"\nTask2: \n\tRisk Level: {risk}")
                # data to send
                data = {
                    "avg_voltage": avg_vol,
                    'risk_level': risk
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
            time.sleep(1)


main()
