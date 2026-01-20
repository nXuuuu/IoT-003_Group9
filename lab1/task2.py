import network
import urequests
import time
from machine import Pin

# -------- SETTINGS --------
SSID = "Robotic WIFI"
PASSWORD = "rbtWIFI@2025"

BOT_TOKEN = "8560404304:AAFCai6tF2wOeMKD-DyZhAi1Rim-c8BLxtA"
CHAT_ID = "-5282582385"

# -------- WIFI --------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

while not wifi.isconnected():
    time.sleep(1)

print("WiFi connected")

# -------- TELEGRAM --------
URL = "https://api.telegram.org/bot{}/getUpdates".format(BOT_TOKEN)
last_id = 0

# -------- MAIN LOOP --------

def send_message():
    global last_id
    while True:
        try:
            r = urequests.get(URL + "?offset={}".format(last_id + 1))
            data = r.json()
            r.close()

            for msg in data["result"]:
                last_id = msg["update_id"]

                if "message" in msg and "text" in msg["message"]:
                    chat_id = msg["message"]["chat"]["id"]
                    text = msg["message"]["text"]

                    if str(chat_id) == CHAT_ID:
                        print("Received:", text)

        except Exception as e:
            print("Error:", e)

send_message()
