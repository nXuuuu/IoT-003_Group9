# LAB 3: IoT Smart Gate Control with Blynk, IR Sensor, Servo Motor, and TM1637

## Overview

This project implements an ESP32-based IoT system that simulates a smart gate control using MicroPython and the Blynk platform. The system integrates an IR sensor for object detection, a servo motor for physical actuation (gate opening/closing), and a TM1637 7-segment display for real-time local feedback.

## Features

- **Automatic Gate Control**: IR sensor detects objects and automatically opens/closes the gate
- **Remote Monitoring**: Real-time status monitoring via Blynk mobile app
- **Manual Override**: Control servo motor position manually through Blynk app
- **Event Counting**: Tracks and displays the number of detection events
- **Dual Display**: Shows counter on both TM1637 display and Blynk app

## Hardware Requirements

- ESP32 Development Board
- IR Sensor Module
- SG90 Servo Motor
- TM1637 4-Digit 7-Segment Display
- Jumper Wires
- Breadboard
- USB Cable for ESP32

## Pin Connections

<img width="1068" height="650" alt="image" src="https://github.com/user-attachments/assets/db1a80d9-8afc-43ed-9228-8f6930992a3e" />


## Software Requirements

- MicroPython firmware for ESP32
- Blynk mobile app (iOS/Android)
- Required MicroPython libraries:
  - `urequests`
  - `tm1637` (TM1637 display driver)

## Blynk Configuration

### Virtual Pins Setup

| Virtual Pin | Widget Type | Purpose |
|-------------|-------------|---------|
| V0 | LED/Value Display | IR sensor digital status (0/1) |
| V1 | Label | IR sensor status text ("Detected"/"NotDetected") |
| V2 | Slider (0-180) | Manual servo control |
| V3 | Value Display | Detection event counter |
| V4 | Switch | Manual/Automatic mode toggle |

### Blynk Setup Steps

1. Create a new Blynk project
2. Copy the authentication token
3. Add the widgets listed above
4. Update `BLYNK_TOKEN` in the code with your token

## Installation & Setup

### 1. WiFi Configuration

Update the WiFi credentials in the code:

```python
WIFI_SSID = "Your_WiFi_Name"
WIFI_PASS = "Your_WiFi_Password"
```

### 2. Upload Required Files

Upload the following files to your ESP32:
- `main.py` (your task code)
- `tm1637.py` (TM1637 library)

### 3. Blynk Token

Replace the token with your own:

```python
BLYNK_TOKEN = "Your_Blynk_Auth_Token"
```

## Usage Instructions

### Task 1: IR Sensor Reading
- The system continuously reads the IR sensor
- Status is displayed on Blynk app (V0 and V1)
- "Detected" appears when an object is in front of the sensor <br>
<img width="960" height="1280" alt="image" src="https://github.com/user-attachments/assets/131565c8-ffc3-4af3-868a-0cd3c4aa7ad6" />


### Task 2: Manual Servo Control
- Use the Blynk slider (V2) to control servo position
- Range: 0° to 180°
- Servo moves in real-time with slider changes <br>
Watch the demo video [HERE](https://youtube.com/shorts/AevJjuhg4zk?si=W8ba5XsR6YgpDwht).

### Task 3: Automatic Gate Operation
- When IR sensor detects an object, servo automatically rotates to 180° (gate opens)
- After 2-second delay, servo returns to 0° (gate closes)
- Fully automatic response to detection <br>
Watch the demo video [HERE](https://youtube.com/shorts/23EK4_0-hws?si=HIqal6pPDDeOj3kM).

### Task 4: Event Counting with Display
- Each IR detection increments a counter
- Counter value displayed on:
  - TM1637 local display
  - Blynk app (V3)
- Both displays show synchronized values<br>
Watch the demo video [HERE](https://youtube.com/shorts/rctSG3n23fk?si=bo708k--j-2ZKF2F).

### Task 5: Manual Override Mode
- Toggle the switch (V4) in Blynk app
- **Manual Mode (ON)**: IR sensor is ignored, counter doesn't increment
- **Automatic Mode (OFF)**: IR sensor active, normal operation resumes <br>
Watch the demo video [HERE](https://youtube.com/shorts/9Ho65accz5U?si=cKjMJkisCjSfI1VX).

## Code Structure

### Task Progression

Each task file builds upon the previous one:

1. **Task 1**: Basic IR sensor reading and Blynk integration
2. **Task 2**: Adds servo motor control via Blynk slider
3. **Task 3**: Implements automatic gate opening on IR detection
4. **Task 4**: Adds TM1637 display and event counter
5. **Task 5**: Implements manual override functionality

### Main Functions

```python
send_ir_signal(ir)           # Send IR digital status to Blynk
send_ir_signal_str(ir)       # Send IR text status to Blynk
get_rotate_angle(deg)        # Convert angle to PWM duty cycle
send_ir_detect_count(count)  # Send counter to Blynk
is_manual()                  # Check manual override status
```

## Troubleshooting

### WiFi Connection Issues
- Verify SSID and password are correct
- Check if ESP32 is within WiFi range
- Monitor serial output for connection status

### Servo Not Moving
- Check power supply (servo requires sufficient current)
- Verify GPIO 13 connection
- Test with manual slider control first

### TM1637 Display Not Working
- Check CLK and DIO pin connections
- Verify 5V power supply
- Ensure `tm1637.py` library is uploaded

### Blynk Connection Failed
- Verify auth token is correct
- Check internet connectivity
- Ensure Blynk server URL is accessible

### IR Sensor False Triggers
- Adjust sensor sensitivity using onboard potentiometer
- Ensure proper 5V power supply
- Check for electromagnetic interference

## System Behavior

### Normal Operation Flow

1. System connects to WiFi
2. Connects to Blynk cloud
3. Initializes TM1637 display (shows 0)
4. Enters main loop:
   - Checks manual override status
   - If automatic mode:
     - Reads IR sensor
     - If object detected:
       - Increments counter
       - Updates displays
       - Opens gate (180°)
       - Waits 2 seconds
       - Closes gate (0°)
   - Updates Blynk status
   - Waits 1 second
## Diagram
```mermaid
flowchart TD
    Start([Start System]) --> Init[Initialize Hardware<br/>- WiFi Connection<br/>- Blynk Connection<br/>- IR Sensor GPIO 12<br/>- Servo GPIO 13<br/>- TM1637 Display GPIO 16/17]
    Init --> Reset[Reset Counter to 0<br/>Display on TM1637<br/>Send to Blynk V3]
    Reset --> Loop{Main Loop}
    
    Loop --> CheckMode{Check Manual<br/>Override Status<br/>Blynk V4}
    
    CheckMode -->|Manual Mode ON<br/>V4 = 1| Ignore[Ignore IR Sensor<br/>Print: 'IR is ignored']
    Ignore --> Wait1[Wait 1 second]
    Wait1 --> Loop
    
    CheckMode -->|Automatic Mode<br/>V4 = 0| ReadIR[Read IR Sensor<br/>GPIO 12]
    
    ReadIR --> IRCheck{Object<br/>Detected?<br/>value = 0}
    
    IRCheck -->|Yes<br/>Detected| Increment[Increment Counter<br/>count += 1]
    Increment --> UpdateTM[Update TM1637<br/>Display counter]
    UpdateTM --> SendCount[Send Counter to Blynk<br/>V3 = count]
    SendCount --> SendStatus0[Send IR Status to Blynk<br/>V0 = 0]
    SendStatus0 --> SendText0[Send Text Status<br/>V1 = 'Detected']
    SendText0 --> PrintDetect[Print: 'Obstacle detected'<br/>with count]
    PrintDetect --> Wait2[Wait 1 second]
    Wait2 --> Loop
    
    IRCheck -->|No<br/>Not Detected| SendStatus1[Send IR Status to Blynk<br/>V0 = 1]
    SendStatus1 --> SendText1[Send Text Status<br/>V1 = 'NotDetected']
    SendText1 --> PrintNo[Print: 'No obstacle']
    PrintNo --> Wait3[Wait 1 second]
    Wait3 --> Loop
    
    style Start fill:#90EE90,stroke:#333,stroke-width:2px,color:#000
    style Loop fill:#FFE4B5,stroke:#333,stroke-width:2px,color:#000
    style CheckMode fill:#87CEEB,stroke:#333,stroke-width:2px,color:#000
    style Ignore fill:#FFB6C1,stroke:#333,stroke-width:2px,color:#000
    style IRCheck fill:#DDA0DD,stroke:#333,stroke-width:2px,color:#000
    style Increment fill:#98FB98,stroke:#333,stroke-width:2px,color:#000
    style UpdateTM fill:#FFDAB9,stroke:#333,stroke-width:2px,color:#000
    style SendCount fill:#FFDAB9,stroke:#333,stroke-width:2px,color:#000
    style Wait1 fill:#E0E0E0,stroke:#333,stroke-width:2px,color:#000
    style Wait2 fill:#E0E0E0,stroke:#333,stroke-width:2px,color:#000
    style Wait3 fill:#E0E0E0,stroke:#333,stroke-width:2px,color:#000
