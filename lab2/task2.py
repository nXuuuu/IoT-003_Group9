import network
import socket
from machine import Pin, time_pulse_us
import time
import dht

# ==============================
# LED SETUP
# ==============================
led = Pin(2, Pin.OUT)

led_state = False  # False = OFF, True = ON

# ==============================
# WIFI SETUP (Station Mode)
# ==============================
ssid = "Robotic WIFI"
password = "rbtWIFI@2025"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)

print("Connecting to WiFi...")
while not wifi.isconnected():
    time.sleep(1)

ip = wifi.ifconfig()[0]
print("Connected!")
print("ESP32 IP address:", ip)

# ==============================
# WEB SERVER SETUP
# ==============================
addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print("Web server running...")

# ==============================
# HTML PAGE WITH LED STATUS
# ==============================
def web_page(state,temp, distance):
    if state:
        color = "green"
        status = "LED is ON"
    else:
        color = "red"
        status = "LED is OFF"
    
    distance /= 100
    
    html = f"""
    <html>
    <head>
        <title>ESP32 LED Control</title>
        <style>
            body {{
                font-family: Arial;
                text-align: center;
            }}
            .circle {{
                width: 80px;
                height: 80px;
                background-color: {color};
                border-radius: 50%;
                margin: 20px auto;
            }}
            button {{
                width: 120px;
                height: 50px;
                font-size: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>ESP32 LED Control</h1>

        <div class="circle"></div>
        <h2>{status}</h2>

        <p><a href="/on"><button>ON</button></a></p>
        <p><a href="/off"><button>OFF</button></a></p>
        <h1>
            Temperature: {temp:.3f} celsius.
            <br><br>
            Total Distance: {distance:.2f} meter(s).
        </h1>
    </body>
    </html>
    """
    return html

#===============
#Get Temperature
#===============
sensor = dht.DHT22(Pin(33))

#==============
#Get Distance
#==============
# Pin configuration
TRIG = Pin(27, Pin.OUT)
ECHO = Pin(26, Pin.IN)
 
def get_distance_cm():
    # Ensure trigger is LOW
    TRIG.value(0)
    time.sleep_us(2)
 
    # Send 10µs pulse
    TRIG.value(1)
    time.sleep_us(10)
    TRIG.value(0)
 
    # Measure echo pulse duration
    duration = time_pulse_us(ECHO, 1, 30000)  # timeout = 30ms
 
    # Check for timeout
    if duration < 0:
        return None
 
    # Distance calculation (cm)
    distance = (duration * 0.0343) / 2
    return distance
 

# ==============================
# MAIN LOOP
# ==============================
while True:
    conn, addr = s.accept()
    request = conn.recv(1024).decode()
    print("Request:", request)
    
    if "/off" in request:
        led.off()
        led_state = False
        print("LED OFF")
    elif "/on" in request:
        led.on()
        led_state = True
        print("LED ON")
        
    temperature = -280
    try:
        sensor.measure() 
        temperature = sensor.temperature()       
        print("Temperature: {} °C".format(temperature))
    except OSError:
        print("Failed to read from DHT11 sensor")
        
    distance = get_distance_cm()
    if distance is not None:
        print("Distance: {:.2f} cm".format(distance))
    else:
        distance = -1
        print("Out of range")
 
    response = web_page(led_state, temperature, distance)
    conn.send("HTTP/1.1 200 OK\n")
    conn.send("Content-Type: text/html\n")
    conn.send("Connection: close\n\n")
    conn.sendall(response)
    conn.close()
    time.sleep(1)
