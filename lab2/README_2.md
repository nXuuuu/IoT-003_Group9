# 🛜LAB2: IoT Webserver with LED, Sensors, and LCD Control
Lab instruction is [HERE](https://theara-seng.github.io/files/IOT/LAB2_Webserver_LCD_Control.pdf)

## 🧰Overview
In this lab, we will design an ESP32-based IoT system using MicroPython that bridges the gap between a web interface and physical hardware. We will also build a system to control an LED, monitor sensor data, and push custom text to an LCD display directly from a web browser. <br>
By focusing on event-driven IoT design, we will gain hands-on experience in making hardware respond in real-time to digital commands through a custom web server.
### Features
• Implement a MicroPython webserver to serve HTML controls. <br>
• Control an LED from the web page. <br>
• Read data from DHT11 and ultrasonic sensors and expose it on the webserver. <br>
• Use web buttons to selectively show temperature and distance on an LCD (I²C). <br>
• Send custom text from a textbox to display on the LCD. <br>
• Document wiring, interface behavior, and system operation.<br>
### Equipments
• ESP32 Dev Board (MicroPython firmware flashed) <br>
• DHT11 sensor (temperature/humidity) <br>
• HC-SR04 ultrasonic distance sensor <br>
• LCD 16×2 with I²C backpack <br>
• Breadboard, jumper wires <br>
• USB cable + laptop with Thonny<br> 
• Wi-Fi access<br>
### Wiring
<img width="1447" height="726" alt="image" src="https://github.com/user-attachments/assets/9cb466df-2b4b-4e00-8303-4e24ed74069d" />

### Set Up
...
## Task 1 - LED Control
• Add two buttons (ON/OFF) on the web page. <br>
• When clicked, LED on GPIO2 should turn ON or OFF. <br>
• Video link is [HERE]()
## Task 2 - Sensor Read
• Read DHT11 temperature and ultrasonic distance.  <br>
• Show values on the web page (refresh every 1-2 seconds).  <br>
<img width="1600" height="670" alt="image" src="https://github.com/user-attachments/assets/3c24183f-40f4-4282-b857-377c76786d80" />
## Task 3 - Sensor → LCD
• Add two buttons:  <br>
  - Show Distance → writes distance to LCD line 1. 
  - Show Temp → writes temperature to LCD line 2. 
<img width="1225" height="1280" alt="image" src="https://github.com/user-attachments/assets/8a36922c-e937-4aed-ae56-6513e76ea0da" /> <br>
## Task 4 - Textbox → LCD
• Add a textbox + “Send” button on the web page. <br> 
• User enters custom text → LCD displays it (scroll if >16 chars).  <br>
• Video link is [HERE]() <br>
