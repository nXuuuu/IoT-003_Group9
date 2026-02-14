import network
import time
import machine
import dht
import urequests as requests
import math

# ---------- CONFIG ----------
WIFI_SSID = "Bunchhith Vesna02"
WIFI_PASS = "vs22224444"

BLYNK_TOKEN = "AXLHua5Akq9qdlm3L9z4dTcq0-QaA8MF"
BLYNK_API   = "http://blynk.cloud/external/api"

LED_PIN = 2
DHT_PIN = 4

# ---------- HARDWARE ----------
led = machine.Pin(LED_PIN, machine.Pin.OUT)
sensor = dht.DHT11(machine.Pin(DHT_PIN))

# ---------- WIFI ----------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASS)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)
print("WiFi connected!")

# ---------- BLYNK ----------
def read_button_v0():
    r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&V0")
    value = int(str(r.text).strip('[]"{}'))
    r.close()
    return value

def send_temperature_v1(temp):
    url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V1={temp}"
    r = requests.get(url)
    r.close()

def send_ir_signal(ir):
     url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V0={ir}"
     r = requests.get(url)
     r.close()

def send_ir_signal_str(ir):
     url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V1={ir}"
     r = requests.get(url)
     r.close()

def get_rotate_angle():
    try:
        r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&V2")
        n = int(str(r.text).strip('[]"{}'))
        
        r.close()
        n = int(n*0.56 + 26)

    except:
        n = 0
    print(n)
    return n
        
    

# ---------- MAIN ----------
print("Running Blynk control...")

ir = machine.Pin(12, machine.Pin.IN)
servo = machine.PWM(machine.Pin(13), freq=50)

while True:
    # task1
    value = ir.value()
    if value == 0:
        send_ir_signal(0)
        #send_ir_signal("Obstacle detected",'1')
        send_ir_signal_str("Detected")
        print("Obstacle detected")
    else:
        send_ir_signal(1)
        send_ir_signal_str("NotDetected")
        #send_ir_signal("No obstacle", '1')
        print("No obstacle")
    
    # task2
    rotate = get_rotate_angle()
    servo.duty(rotate)
    
    time.sleep(1)
