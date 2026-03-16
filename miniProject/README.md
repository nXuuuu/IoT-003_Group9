# Smart IoT Parking Management System
## Technical Documentation Report
### ESP32 + MicroPython

**Group 9**   
**Course:** Introduction to Internet of Things ICT 360 - 003  
**Lecturer:** Theara SENG

**Platform:** ESP32 Microcontroller + MicroPython Firmware  
**IoT Platforms:** Telegram Bot | Web Server Dashboard | Blynk Mobile App  
**Parking Capacity:** 3 Slots  

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Hardware Description](#2-hardware-description)
3. [System Architecture](#3-system-architecture)
4. [Software Architecture](#4-software-architecture)
5. [IoT Integration](#5-iot-integration)
6. [Working Process Explanation](#6-working-process-explanation)
7. [Challenges Faced](#7-challenges-faced)
8. [Future Improvements](#8-future-improvements)

---

## 1. Introduction

### 1.1 Project Overview

This project presents the design and implementation of a Smart IoT Parking Management System built on the ESP32 microcontroller programmed with MicroPython firmware. The system automates the core operations of a small parking facility by integrating multiple sensors and actuators with three independent IoT platforms. A Telegram Bot, a self-hosted Web Dashboard, and the Blynk mobile application all into one unified and continuously running embedded system.

The system monitors parking slot occupancy in real time using infrared sensors, detects vehicles at the entrance using an ultrasonic distance sensor, controls a physical gate barrier via a servo motor, monitors environmental conditions through a DHT11 temperature and humidity sensor, and controls parking lighting through a relay module. Two local display units, a TM1637 seven-segment display and a 16x2 LCD to provide immediate on-site status information, while the three IoT platforms allow remote monitoring and control from any location with network access.

### 1.2 Problem Statement

Manual parking management is inefficient, labour-intensive, and provides no real-time visibility to either operators or drivers. Drivers often waste time searching for available slots, and parking operators have no way to monitor or control the facility remotely without being physically present. Existing commercial solutions are expensive and not accessible for small-scale or educational implementations.

This project addresses these problems by building a low-cost, fully automated parking system using off-the-shelf components that provides real-time slot availability, automatic gate control, remote command capability, and live monitoring through multiple platforms simultaneously.

### 1.3 Project Objectives

- Design and implement a complete embedded IoT system using ESP32 and MicroPython
- Integrate eight hardware components into a unified sensor-actuator control system
- Automate vehicle entry detection and gate control using sensor-driven logic
- Provide real-time slot availability monitoring across local displays and cloud platforms
- Implement remote monitoring and control via Telegram Bot, Web Dashboard, and Blynk App
- Monitor environmental conditions including temperature and humidity
- Produce clean, modular, and well-documented code that is easy to maintain and modify

### 1.4 Scope

The system manages a parking facility of three slots. All software is designed to run entirely on the ESP32 with no external server or computer required during operation. The web dashboard is hosted directly on the ESP32. Telegram and Blynk communication requires an active WiFi connection with internet access, while hardware control (gate, displays, sensors) continues to function independently even if the network connection is lost.

---

## 2. Hardware Description

### 2.1 ESP32 Microcontroller

The ESP32 is the central processing unit of the entire system. It is a dual-core 32-bit microcontroller running at up to 240 MHz with built-in WiFi (802.11 b/g/n) and Bluetooth. For this project, only WiFi is used. The ESP32 runs MicroPython firmware, which provides a Python-based programming environment well suited to rapid IoT development. All sensors, actuators, and display modules connect directly to the ESP32 GPIO pins. The ESP32 simultaneously acts as a WiFi client (connecting to a router for internet access), a web server (hosting the dashboard), a Telegram polling client, and a Blynk HTTP client.

### 2.2 HC-SR04 Ultrasonic Sensor

The ultrasonic sensor is mounted at the parking entrance to detect arriving vehicles. It works by emitting a 40 kHz sound pulse on the TRIG pin and measuring the time for the echo to return on the ECHO pin. The ESP32 calculates distance using the formula:

> **distance = (echo duration in microseconds × 0.0343) / 2**

When the measured distance falls below 15 cm, the system considers a vehicle present and initiates the entry logic. Connected to GPIO 5 (TRIG) and GPIO 18 (ECHO).

### 2.3 IR Proximity Sensors (×3)

Three infrared proximity sensors each monitor one parking slot. When a vehicle is present, it blocks the IR beam and the sensor output pin goes LOW. The ESP32 reads these as digital inputs with pull-up resistors enabled, so an unconnected or disconnected sensor reads HIGH (free) by default, preventing false occupancy. Connected to GPIO 34 (Slot 1), GPIO 35 (Slot 2), and GPIO 26 (Slot 3).

### 2.4 Servo Motor

An SG90 servo motor controls the physical gate barrier. The ESP32 generates a 50 Hz PWM signal on GPIO 13 to position the servo arm. 0 degrees corresponds to gate closed and 90 degrees to gate open. The servo is powered from a dedicated 5V supply rather than the ESP32 3.3V pin to provide sufficient current and avoid voltage instability on the microcontroller.

### 2.5 DHT11 Temperature and Humidity Sensor

The DHT11 reads ambient temperature and humidity using a single-wire protocol on GPIO 4. It returns integer values with 1°C and 1% resolution. The sensor is read at a minimum interval of 10 seconds to respect its physical sampling rate. Readings are displayed on the LCD and pushed to the web dashboard and Blynk app. While temperature monitoring does not directly affect parking logic, it provides useful environmental awareness for an enclosed parking facility.

### 2.6 Relay Module

A single-channel relay module on GPIO 12 controls the parking facility lights. The relay is configured as active-low, meaning the ESP32 outputs LOW to turn the lights ON. Lights are controlled manually through Telegram commands (`/light_on`, `/light_off`), the web dashboard, and the Blynk app. An optional auto-light mode is available in the configuration that automatically turns lights on when any slot is occupied and off when the facility is empty.

### 2.7 TM1637 7-Segment Display

The TM1637 four-digit seven-segment display shows the current number of available parking slots as a large, clearly visible number. It is updated immediately whenever an IR sensor changes state, giving drivers approaching the facility instant feedback. It communicates via CLK (GPIO 14) and DIO (GPIO 27).

### 2.8 LCD I2C Display (16×2)

A 16-character by 2-row LCD connected via I2C (SDA GPIO 21, SCL GPIO 22) shows detailed system status. Row 1 displays the slot count and gate state. Row 2 displays temperature and light status. It also shows contextual messages such as "Vehicle Detected", "Gate OPENING", and "PARKING FULL" during system events. The I2C address is set to 0x27 by default.

### 2.9 GPIO Pin Assignment Table

| Component | GPIO Pin | Interface |
|---|---|---|
| Ultrasonic TRIG | GPIO 5 | Digital Output |
| Ultrasonic ECHO | GPIO 18 | Digital Input |
| IR Sensor – Slot 1 | GPIO 34 | Digital Input (Pull-up) |
| IR Sensor – Slot 2 | GPIO 35 | Digital Input (Pull-up) |
| IR Sensor – Slot 3 | GPIO 26 | Digital Input (Pull-up) |
| Servo Motor | GPIO 13 | PWM 50Hz |
| DHT11 | GPIO 4 | Single-wire |
| Relay Module | GPIO 12 | Digital Output (Active-Low) |
| TM1637 CLK | GPIO 14 | Digital Clock |
| TM1637 DIO | GPIO 27 | Digital Data |
| LCD SDA | GPIO 21 | I2C Data |
| LCD SCL | GPIO 22 | I2C Clock |

---

## 3. System Architecture

### 3.1 Overview

The system is organised into three distinct layers that separate physical hardware, processing logic, and cloud communication concerns from each other. This layered design means that a change in one layer does not require changes in the others. For example, adding a fourth parking slot only requires a new IR sensor and a one-line change in config.py — the web dashboard, Telegram bot, and Blynk app all adapt automatically.

**Physical Layer** — All sensors and actuators wired directly to the ESP32. This layer produces raw signals (distances, digital HIGH/LOW values, temperature readings) and receives control signals (PWM for servo, digital for relay).

**Processing Layer** — The ESP32 running MicroPython. This is the core of the system. It reads all sensor inputs, applies parking logic, updates shared state, drives all output devices, and communicates with all three cloud platforms. Everything runs on a single device with no external computer.

**Cloud / IoT Layer** — Three independent platforms that each provide a different mode of remote access. Telegram provides command-based control and automatic notifications. The Web Dashboard provides a visual browser interface hosted on the ESP32 itself. Blynk provides a mobile app with widgets for monitoring and control.

### 3.2 Architecture Block Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      PHYSICAL LAYER                         │
│                                                             │
│   [Ultrasonic]   [IR x3]   [DHT11]     ← Input Sensors     │
│         ↓           ↓         ↓                             │
│   ───────────────────────────────────────────────────────   │
│                      ESP32                                  │
│                 (MicroPython)                               │
│   ───────────────────────────────────────────────────────   │
│         ↓           ↓         ↓         ↓                   │
│   [Servo]       [Relay]   [TM1637]   [LCD I2C]              │
│                                        → Output Actuators   │
└─────────────────────────────────────────────────────────────┘
                        ↕ WiFi / Internet
┌─────────────────────────────────────────────────────────────┐
│                    CLOUD / IoT LAYER                        │
│                                                             │
│   [Telegram Bot]   [Web Dashboard]   [Blynk Mobile App]    │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Data Flow

Sensor data flows upward: physical sensors produce signals → ESP32 reads and processes them → shared state is updated → all displays and cloud platforms receive the updated values.

Commands flow downward: a user sends a Telegram command, clicks a web dashboard button, or presses a Blynk widget → the ESP32 receives it → the corresponding hardware actuator is triggered → the shared state is updated → all other platforms reflect the change on their next refresh.

Because all platforms read from and write to the same shared state object in memory, any action taken on one platform is immediately visible on all others. For example, if the gate is opened via Telegram, the web dashboard will show OPEN on its next 3-second data refresh, and Blynk's gate status widget will update on the next push cycle.

### 3.4 Concurrency Model

MicroPython on ESP32 is single-threaded. The system uses a cooperative polling loop running at approximately 200ms per cycle. Each module — sensors, web server, Telegram, Blynk — is called in sequence every loop iteration. Each module is designed to return quickly without blocking. Non-blocking socket operations, short timeouts, and internal interval timers ensure no single module can hold up the others for an unreasonable amount of time.

---

## 4. Software Architecture

### 4.1 Modular File Structure

The software is split into seven Python files, each with one clear responsibility. This makes the codebase easier to navigate, debug, and modify. A problem with Blynk communication means opening blynk_client.py only — none of the other files need to be touched.

| File | Responsibility |
|---|---|
| `main.py` | Entry point. WiFi connection, socket setup, hardware init, main loop |
| `config.py` | All settings in one place. Pins, credentials, timers, flags |
| `state.py` | Shared live system state object used by all modules |
| `hardware.py` | Drivers for all 7 hardware components |
| `telegram_bot.py` | Telegram command handling and outbound notifications |
| `web_server.py` | HTTP server, dashboard HTML, JSON data endpoint |
| `blynk_client.py` | Blynk HTTP REST API — push data and read button states |

### 4.2 Shared State Pattern

A single ParkingState object is created in main.py and passed by reference into every module. It holds the live values for slot occupancy, gate status, light status, temperature, and humidity. Because every module shares the same object, there is no synchronisation problem — when Telegram opens the gate and sets state.gate_open = True, the web server reads that same value on the next browser request and shows OPEN automatically. Without this pattern, each module would hold its own copy of the system state and they would quickly go out of sync with each other.

### 4.3 Main Loop Structure

The main loop in main.py runs continuously after boot. Each iteration follows this sequence:

1. Read IR sensors — update slot occupancy in shared state, refresh TM1637 and LCD if changed
2. Read DHT11 — update temperature and humidity (internally throttled to every 10 seconds)
3. Run gate logic — check ultrasonic, open servo if vehicle present and slots available, auto-close after 3 seconds
4. Run light logic — if AUTO_LIGHT enabled, toggle relay based on occupancy
5. Poll Telegram — check for new commands, send any queued notifications
6. Poll Web Server — check for waiting browser connection using uselect, handle request if ready
7. Poll Blynk — push state to display widgets and read button pin states on configured intervals
8. Sleep 200ms — yield CPU briefly before next iteration

### 4.4 Configuration Management

Every value that might need changing lives in config.py. This includes all GPIO pin numbers, WiFi credentials, IoT tokens, servo angles, timing intervals, Blynk virtual pin assignments, and behaviour flags. Changing a pin, adjusting the gate timeout, or switching WiFi networks requires editing only config.py. No other file needs to be opened. This design was deliberately chosen to make the system easy to reconfigure without risk of accidentally breaking logic code.

### 4.5 Non-Blocking Web Server Design

The web server was the most technically demanding module to implement correctly. The core requirement was that serving an HTTP request must never block the main loop long enough to affect sensor reading or IoT polling. The solution uses three layers of protection:

- **uselect.select() with timeout=0** — checks whether a browser connection is waiting before accepting it. If no connection is waiting, poll() returns in under 1ms.
- **client.settimeout(0.05)** — if a connected browser is slow to send its HTTP request headers, recv() gives up after 50ms instead of waiting indefinitely.
- **5-second overall budget** — if the entire poll() call takes longer than 5 seconds for any reason, the request is abandoned and the loop continues.

The dashboard HTML is served only once on the initial page load. After that, a JavaScript function in the browser fetches a small JSON payload from the /data endpoint every 3 seconds and updates only the changed elements on the page, keeping each subsequent request small and fast.

### 4.6 Error Handling

Every network operation — Telegram polling, Blynk HTTP requests, web server accept and recv — is wrapped in try/except blocks. A failed network call prints an error message to the serial console when DEBUG_MODE is True and then continues to the next loop iteration. This means a temporary WiFi dropout, a slow Blynk API response, or a malformed HTTP request from a browser will not crash the system. The ESP32 keeps running, keeps reading sensors, and resumes cloud communication as soon as connectivity is restored.

---

## 5. IoT Integration

### 5.1 Telegram Bot

The Telegram bot is implemented using the Telegram Bot API over HTTPS. The ESP32 acts as a polling client, periodically sending a GET request to the getUpdates endpoint to retrieve any new messages sent to the bot. Polling is used instead of webhooks because the ESP32 cannot receive unsolicited inbound connections from the internet without complex router port forwarding configuration.

Each incoming message is parsed to extract the command text and the sender's chat ID. The command is matched against a dictionary of registered handlers. If a match is found, the corresponding function executes and sends a reply. Unrecognised commands receive a prompt to type /help.

**Implemented Commands:**

| Command | Action |
|---|---|
| `/status` | Returns full system report — slots, gate, lights, temperature, humidity |
| `/open` | Manually opens the gate via servo |
| `/close` | Manually closes the gate via servo |
| `/slots` | Returns current available and total slot count |
| `/temp` | Returns current temperature and humidity readings |
| `/light_on` | Activates relay to turn parking lights ON |
| `/light_off` | Deactivates relay to turn parking lights OFF |
| `/help` | Lists all available commands |

**Automatic Notifications:**

Beyond responding to commands, the bot also sends proactive notifications without any user prompt. When all three parking slots become occupied simultaneously, the system queues a "Parking FULL" notification message. This is sent on the next Telegram poll cycle. This feature ensures operators are informed of critical status changes without having to manually check.

### 5.2 Web Server Dashboard

The web dashboard is hosted directly on the ESP32 — no external server, cloud hosting, or computer is required. The ESP32 creates a TCP socket bound to all interfaces using `socket.getaddrinfo("0.0.0.0", 80)[0][-1]`, then listens for incoming HTTP connections on port 80. The dashboard is accessible by any device on the same WiFi network by navigating to the ESP32's IP address in a browser.

**Endpoints:**

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the full HTML dashboard page |
| `/data` | GET | Returns live system state as compact JSON |
| `/gate/open` | POST | Opens gate and updates state |
| `/gate/close` | POST | Closes gate and updates state |
| `/light/on` | POST | Turns lights ON via relay |
| `/light/off` | POST | Turns lights OFF via relay |

The dashboard displays available slot count, individual slot status, gate state, temperature, humidity, and light status. Four control buttons allow manual gate and light operation directly from the browser. The page auto-refreshes data every 3 seconds using a JavaScript fetch() call to the /data endpoint, updating only the changed values on screen without reloading the full page.

### 5.3 Blynk Mobile Application

Blynk integration uses the Blynk HTTP REST API over plain HTTP on port 80. HTTPS was intentionally avoided after encountering repeated MBEDTLS_ERR_RSA_PUBLIC_FAILED SSL memory errors during development. These errors occur because the ESP32 does not have enough free heap memory to complete an RSA TLS handshake while simultaneously running a web server and polling Telegram. Plain HTTP eliminates this problem entirely with no loss of functionality.

Data is pushed to Blynk display widgets by constructing a GET request to:
```
http://blynk.cloud/external/api/update?token=AUTH_TOKEN&VX=VALUE
```

Button states are read from:
```
http://blynk.cloud/external/api/get?token=AUTH_TOKEN&VX
```

The response is parsed by stripping surrounding brackets and quotes from the returned JSON array using `.strip('[]"{}')` and converting the result to an integer.

**Virtual Pin Configuration:**

| Virtual Pin | Widget Type | Purpose |
|---|---|---|
| V10 | Button (Switch) | Light relay ON/OFF control |
| V11 | Value Display | Available slot count |
| V12 | Value Display | Temperature in °C |
| V13 | Value Display | Humidity in % |
| V14 | Value Display | Gate status (OPEN / CLOSED) |
| V15 | Button (Switch) | Gate open/close control |

---

## 6. Working Process Explanation

### 6.1 System Boot Sequence

On power-up or reset, MicroPython automatically executes main.py. The boot sequence follows a strict order to ensure hardware is ready before network operations begin:

1. WiFi connection is established in Station mode to the configured network
2. Web server socket is created and bound to port 80
3. All hardware drivers are initialised — sensors, servo, relay, displays
4. Servo is homed to 0 degrees (gate closed position)
5. LCD displays "Smart Parking — Initialising..." for 2 seconds
6. TM1637 shows current available slot count
7. Telegram bot, web server, and Blynk client modules are started
8. Telegram sends a startup notification with the ESP32 IP address
9. Main loop begins

### 6.2 Vehicle Entry Process

The complete sequence from vehicle arrival to gate close:

1. Ultrasonic sensor measures distance continuously on every loop iteration
2. Distance drops below 15 cm — vehicle detected at entrance
3. ESP32 checks available slot count from shared state
4. If slots are available — servo rotates to open position, gate_open flag set True, LCD shows "Gate OPENING"
5. If parking is full — LCD shows "PARKING FULL", Telegram notification queued
6. Vehicle passes through the gate
7. Once the ultrasonic no longer detects the vehicle AND 3 seconds have elapsed, servo returns to 0 degrees
8. gate_open flag set False, LCD updates to show current status

### 6.3 Slot Occupancy Tracking

Every main loop iteration reads all three IR sensors. Each raw pin value is compared against the previous reading stored in the shared state. If any sensor value has changed, the slot_status list is updated, the available count is recalculated, and both the TM1637 and LCD are refreshed immediately to reflect the new count. If the new state means all slots are now full, a Telegram notification is queued to alert the operator.

### 6.4 Manual Override

Any of the three IoT platforms can override automatic gate control at any time. A `/open` Telegram command, a web dashboard button click, or a Blynk gate button press all call the same servo.open() function and set the same state.gate_open flag. Because all platforms share the same state object, an override from any one platform is immediately reflected on all others on their next data refresh. The auto-close timer also activates on a manual open, so the gate will still close automatically after 3 seconds unless held open by a new command.

### 6.5 Display Updates

The TM1637 and LCD are updated immediately and synchronously whenever the slot state changes. They do not wait for the next loop iteration — the update happens inside the IR sensor reading function as soon as a change is detected. This ensures the physical displays always show the most current information with minimal latency. The web dashboard and Blynk app update on their own polling intervals — the web dashboard refreshes every 3 seconds via JavaScript and Blynk data is pushed every 5 seconds.

### 6.6 Temperature Monitoring

The DHT11 sensor is read at a minimum interval of 10 seconds enforced internally by the hardware driver. On a successful read, temperature and humidity values are stored in the shared state and will be included in the next web dashboard JSON response and Blynk push cycle. The LCD Row 2 also reflects the current temperature. If a read fails, the last known values are retained and no error is shown to the user — the system simply tries again on the next eligible iteration.

---

## 7. Challenges Faced

### 7.1 Insufficient Power Supply
Running all components from a single laptop USB port caused the servo and displays to malfunction intermittently due to insufficient current. This was resolved by using an externernal power supply.

### 7.2 Web Server Blocking the Main Loop
The web server's recv() call would block the entire system whenever a browser connected slowly. Fixed by implementing uselect.select() with zero timeout and a 5-second overall request budget.

### 7.3 Servo Malfunction
The servo behaved erratically during initial testing due to sharing power with the ESP32. Resolved by powering the servo independently and calibrating the open angle to 140 degrees for the specific gate barrier used.

### 7.4 Blynk SSL Memory Errors
HTTPS connections to Blynk caused MBEDTLS_ERR_RSA_PUBLIC_FAILED errors as the ESP32 ran out of RAM for TLS handshakes. Resolved by switching to plain HTTP which Blynk fully supports.

### 7.6 Slow WiFi Connection
Inconsistent WiFi speed caused Telegram polling and Blynk updates to lag. Addressed by increasing poll intervals and adding proper timeout handling so slow responses do not block the main loop.

---

## 8. Future Improvements

- **Expanded slot capacity** — Add more IR sensors and update TOTAL_SLOTS in config.py. No other code changes needed.
- **RFID vehicle authentication** — Allow only registered vehicles to enter by scanning RFID tags at the entrance.
- **License plate recognition** — Use an ESP32-CAM module to capture and log vehicle plate numbers on entry.
- **Time-based automatic lighting** — Use NTP internet time to schedule lights on at sunset and off at sunrise.
- **Cloud data logging** — Log occupancy events and sensor readings to a database for historical analytics.

---

## File Structure

```
/
├── main.py           # Entry point and main loop
├── config.py         # All settings and credentials
├── state.py          # Shared system state
├── hardware.py       # Sensor and actuator drivers
├── telegram_bot.py   # Telegram bot integration
├── web_server.py     # Web dashboard HTTP server
├── blynk_client.py   # Blynk mobile app integration
├── tm1637.py         # TM1637 display library
├── lcd_api.py        # LCD base library
├── i2c_lcd.py        # LCD I2C driver
└── README.md         # This file
```

## Required Libraries

Upload these to ESP32 root before running:

| File | Source |
|---|---|
| `tm1637.py` | https://github.com/mcauser/micropython-tm1637 |
| `lcd_api.py` | https://github.com/dhylands/python_lcd |
| `i2c_lcd.py` | https://github.com/dhylands/python_lcd |

## Quick Start

1. Edit `config.py` with your WiFi credentials, Telegram token, and Blynk auth token
2. Upload all 10 files to ESP32 root via Thonny
3. Hard reset the ESP32
4. Open serial monitor — IP address will be printed on boot
5. Open `http://<IP>/` in browser on same network
6. Send `/help` to your Telegram bot to verify connection
7. Check Blynk app for live data

---

*Smart IoT Parking Management System — ESP32 + MicroPython*
