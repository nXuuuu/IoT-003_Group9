# LAB 5: Smart Color Detection & Control with MIT App

## Overview

This project implements a color-based IoT control system using an **ESP32** microcontroller and **MicroPython** (via Thonny IDE). The system reads RGB color data from a **TCS34725** color sensor, classifies the detected color, and responds by controlling a **NeoPixel RGB LED** and a **DC motor** via PWM. Real-time monitoring and manual override are handled through a **MIT App Inventor** mobile application over Bluetooth/Wi-Fi.

---

## Hardware Components

| Component        | Pin(s) on ESP32         |
|------------------|--------------------------|
| TCS34725 (SDA)   | D21                      |
| TCS34725 (SCL)   | D22                      |
| TCS34725 (VCC)   | 3.3V                     |
| TCS34725 (GND)   | GND                      |
| NeoPixel (Data)  | D23                      |
| NeoPixel (VCC)   | 5V                       |
| NeoPixel (GND)   | GND                      |
| Motor Driver ENA | D14                      |
| Motor Driver IN1 | D26                      |
| Motor Driver IN2 | D27                      |
| Motor Driver GND | GND                      |
| Motor Driver PWR | External Power Supply    |

---

## System Logic

The ESP32 runs a continuous loop that:

1. Reads raw RGB values from the TCS34725 sensor over I2C.
2. Classifies the dominant color using the following rules:
   - **RED**: `R > G` and `R > B`
   - **GREEN**: `G > R` and `G > B`
   - **BLUE**: `B > R` and `B > G`
3. Sets the NeoPixel LED to match the detected color.
4. Adjusts the DC motor speed via PWM based on the detected color.
5. Sends the detected color string to the MIT App Inventor app.
6. Listens for manual override commands from the app (motor direction + custom NeoPixel color).

---

## Color-to-Output Mapping

| Detected Color | NeoPixel Color | Motor PWM Duty |
|----------------|----------------|----------------|
| RED            | Red            | 700            |
| GREEN          | Green          | 500            |
| BLUE           | Blue           | 300            |

---

## Tasks & Checkpoints

### Task 1 — RGB Reading
- Read raw RGB values from the TCS34725 color sensor over I2C.
- Print the R, G, and B values continuously to the Serial Monitor (Thonny shell).

### Task 2 — Color Classification
Implement rule-based logic to classify the dominant color:
- **RED**: `R > G` and `R > B`
- **GREEN**: `G > R` and `G > B`
- **BLUE**: `B > R` and `B > G`

### Task 3 — NeoPixel Control
Map the classified color to the NeoPixel LED output:
- RED detected → NeoPixel displays **Red**
- GREEN detected → NeoPixel displays **Green**
- BLUE detected → NeoPixel displays **Blue**

### Task 4 — Motor Control (PWM)
Adjust DC motor speed based on the classified color using PWM duty cycle:
- RED → PWM = **700**
- GREEN → PWM = **500**
- BLUE → PWM = **300**

### Task 5 — MIT App Integration
Build a mobile app in MIT App Inventor with the following features:
- A **Label** that displays the currently detected color received from the ESP32.
- **Buttons**: Forward, Stop, Backward — for manual motor direction control.
- **RGB input boxes** (R, G, B) with a **Set Color** button to manually control the NeoPixel.
  
---

## MIT App Inventor — App Features

The companion mobile app provides:

- **Color Label**: Displays the currently detected color in real time.
- **Motor Control Buttons**: Forward, Stop, Backward.
- **Manual NeoPixel Control**: Input boxes for R, G, B values with a "Set Color" button.

---

## How to Run

1. Connect all hardware components as described in the wiring table above.
2. Open **Thonny IDE** and connect to the ESP32 via USB.
3. Upload `main.py` to the ESP32's root directory.
4. Run `main.py` — the system will start reading sensor data immediately.
5. Open MIT App Inventor website and import the `lab5_app.aia` as a new project.
7. Install the MIT App Inventor app on your Android device and connect to the ESP32.
8. Use the app to monitor color detection and send manual control commands.

---

## Dependencies

- `machine` — GPIO, PWM, I2C (built-in MicroPython)
- `neopixel` — NeoPixel LED control (built-in MicroPython)
- `tcs34725` — TCS34725 color sensor driver (third-party MicroPython library)
- MIT App Inventor (for mobile app)

---

## Demo

Watch the demonstration video [HERE]().
