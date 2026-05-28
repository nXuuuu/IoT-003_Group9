import network
import socket
from machine import Pin, time_pulse_us
import time
import dht
from machine import Pin, SoftI2C
from machine_i2c_lcd import I2cLcd

I2C_ADDR = 0x27
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

# ==============================
# LED SETUP
# ==============================
led = Pin(2, Pin.OUT)

led_state = False  # False = OFF, True = ON

# ==============================
# WIFI SETUP (Station Mode)
# ==============================
ssid = ""
password = ""

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

def scroll(text, row=0, width=16, delay=0.3):
    padded=" " * width + text + " " * width
    
    for i in range(len(padded) - width):
        lcd.move_to(0, row)
        lcd.putstr(padded[i:i+width])
        time.sleep(delay)
        
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
            Temperature: {temp} celsius.
            <br><br>
            Total Distance: {distance:.2f} meter(s).
        </h1>
        <div>
            <a href="/distance"><button>Distance</button></a>
            <a href="/temperature"><button>Temperature</button></a>
        </div>
        
        <form action="http://{ip}/" method="POST">
          <input name="cmd" type="text">
          <button type="submit">Send</button>
        </form>

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
    show_lcd = []
    
    if "/off" in request:
        led.off()
        led_state = False
        print("LED OFF")


    elif "/on" in request:
        led.on()
        led_state = True
        print("LED ON")
        
    if "/distance" in request:
        show_lcd.append(0)
    if "/temperature" in request:
        show_lcd.append(1)
      
        
    temperature = -280
    try:
        sensor.measure() 
        temperature = sensor.temperature()       
        print("Temperature: {} °C".format(temperature))
        
    except OSError:
        print("Failed to read from DHT11 sensor")
        
    distance = get_distance_cm()
    if distance is not None:
        print("Dis: {:.2f} cm".format(distance))
    else:
        distance = -1
        print("Out of range")
    
    for i in show_lcd:
        out = "Temp: {:.3f} °C".format(temperature) if i else "Dis: {:.2f} cm".format(distance)
        lcd.move_to(0, i)         # first row
        lcd.putstr(out)
 
  
    try:
        body = request.split("\r\n\r\n",1)[1]
        ut = body.split("=",1)[1]
        if ut:
          lcd.clear()
          scroll(ut)
    except:
        print("LCD Error")

  
    response = web_page(led_state,temperature, distance)
    conn.send("HTTP/1.1 200 OK\n")
    conn.send("Content-Type: text/html\n")
    conn.send("Connection: close\n\n")
    conn.sendall(response)
    conn.close()
    time.sleep(1)
