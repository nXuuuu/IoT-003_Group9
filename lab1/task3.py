import network
import urequests
import time
from machine import Pin
import dht
import gc

# -------- SETTINGS --------
SSID = ""
PASSWORD = ""

BOT_TOKEN = ""
CHAT_ID = ""

# -------- HARDWARE --------
relay = Pin(2, Pin.OUT)
relay.off()  # Relay OFF initially

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

gc.collect()
time.sleep(2)  # let sensor stabilize

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
    global last_id
    while True:
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

                # -------- COMMANDS --------
                if text == "/on":
                    relay.on()
                    reply("✅ Relay turned ON")

                elif text == "/off":
                    relay.off()
                    reply("❌ Relay turned OFF")

                elif text == "/status":
                    try:
                        sensor.measure()
                        temp = sensor.temperature()
                        hum = sensor.humidity()
                    except Exception:
                        temp = "N/A"
                        hum = "N/A"

                    state = "OFF" if not relay.value() else "ON"

                    reply(
                        "STATUS \nTemp: {} °C \nHumidity: {}% \nRelay: {}".format(temp, hum, state)
                    )

        except Exception as e:
            print("Loop error:", e)

        gc.collect()
        time.sleep(2)

send_message()
