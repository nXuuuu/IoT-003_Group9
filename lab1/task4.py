import network
import urequests
import time
from machine import Pin
import dht
import gc

# -------- SETTINGS --------
SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

BOT_TOKEN = "8560404304:AAFCai6tF2wOeMKD-DyZhAi1Rim-c8BLxtA"
CHAT_ID = "-5282582385"

# -------- HARDWARE --------
#Relay OFF initially

sensor = dht.DHT11(Pin(18))  # Change to DHT22 if needed

# -------- WIFI --------
wifi = network.WLAN(network.STA_IF)
wifi.active(False)
time.sleep(1)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

while not wifi.isconnected():
    time.sleep(1)

print("WiFi connected")


# -------- TELEGRAM --------
BASE_URL = "https://api.telegram.org/bot{}".format(BOT_TOKEN)
URL = BASE_URL + "/getUpdates"
last_id = 0

# -------- SEND REPLY (ESP32 SAFE) --------
def reply(msg):
    try:
        time.sleep(0.5)
        payload = f"chat_id={CHAT_ID}&text={msg}" + " "*2
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = urequests.post(
            BASE_URL + "/sendMessage",
            data=payload,
            headers=headers
        )
        r.close()
    except Exception as e:
        print("Reply error:", e)


# -------- MAIN LOOP --------
def send_message():
    gc.collect()
    
    global last_id
    count = 0
    relay = Pin(2, Pin.OUT)
    
    while True:
        gc.collect()
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
        except Exception:
            temp = -274
            hum = -274
            
        count += 1
        print(count)
        print('temp:',temp)
        print('relay:', relay.value())
        
        # send message to telegram group every 5s if temperature => 30C
        if temp != -274 and temp >= 30:
            while not relay.value():
                gc.collect()
            
                reply("⚠️ Please turn the relay on  ")
                
                try:
                    r = urequests.get(URL + "?offset={}".format(last_id + 1))
                    data = r.json()
                    r.close()

                    for msg in data["result"]:
                        last_id = msg["update_id"]

                        if "message" not in msg or "text" not in msg["message"]:
                            continue

                        chat_id = msg["message"]["chat"]["id"]
                        text = msg["message"]["text"]

                        if str(chat_id) != CHAT_ID:
                            continue

                        print("Received:", text)

                        # listen for command from telegram 
                        if text == "/on":
                            relay.on()
                            reply("✅ Relay turned ON")
                            gc.collect()

                except Exception as e:
                    print("Loop error:", e)
            
        else:
            # autometically turn off the relay if temperature is under 30C
            if relay.value():
                relay.off()
                reply("❌ Relay turned OFF")
            gc.collect()
        
        time.sleep(5)

send_message()
