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
• Video link is <a href="https://youtube.com/shorts/7-j0wPhD0Rk?si=Z3Fr2QL3oJA7VomG"> CLICK ME </a>
<br>
### Diagram
```mermaid
flowchart LR
    Start([START]) --> Init1["Initialize I2C LCD<br/>SDA=Pin21, SCL=Pin22<br/>Address: 0x27, 2x16 display"]
    Init1 --> Init2["Initialize Ultrasonic Sensor<br/>TRIG=Pin27, ECHO=Pin26"]
    Init2 --> Main2["Execute main2()"]
    Main2 --> While{"While True"}
    While --> Scroll["scroll_lr() function<br/>Text: 'fuck thiefland!'<br/>Width=16, Row=0, Delay=0.1s"]
    Scroll --> Prepare["Prepare padded string:<br/>spaces + text + spaces"]
    Prepare --> ForLoop{"For each<br/>position"}
    ForLoop -->|Yes| MoveCursor["Move LCD cursor<br/>to (0, row)"]
    MoveCursor --> Display["Display 16-char<br/>window of text"]
    Display --> Delay1["Sleep 0.1s"]
    Delay1 --> Delay2["Sleep 0.1s"]
    Delay2 --> LoopBack["Continue"]
    LoopBack --> ForLoop
    ForLoop -->|Done| LoopBack2["Scroll Complete"]
    LoopBack2 --> While
    
    %% Alternative main1 function - shown as note
    Main1[main1 - UNUSED<br/>1. Clear LCD<br/>2. Display 'Distance:'<br/>3. Call get_distance_m<br/>4. Display result or 'Out of range'<br/>5. Sleep 2s<br/>6. Repeat]
    
    %% Helper function
    GetDist[get_distance_m<br/>1. Send 10µs trigger pulse<br/>2. Measure echo duration<br/>3. Calculate distance:<br/>d = duration × 0.0343/2/100<br/>4. Return distance in meters<br/>or None if timeout]
    
    %% Styling with visible text colors
    classDef terminator fill:#e8f5e9,stroke:#388e3c,stroke-width:3px,color:#000000
    classDef process fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000000
    classDef function fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#000000
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:3px,color:#000000
    classDef unused fill:#fffde7,stroke:#f9a825,stroke-width:3px,stroke-dasharray: 5 5,color:#000000
    classDef helper fill:#e8eaf6,stroke:#3f51b5,stroke-width:3px,stroke-dasharray: 5 5,color:#000000
    classDef loopNode fill:#ffebee,stroke:#c62828,stroke-width:3px,color:#000000
    
    class Start terminator
    class Init1,Init2,Prepare,MoveCursor,Display,Delay1,Delay2 process
    class Main2,Scroll function
    class While,ForLoop decision
    class Main1 unused
    class GetDist helper
    class LoopBack,LoopBack2 loopNode
```
