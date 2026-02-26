# =============================================================================
# main.py — Main Entry Point
# Smart IoT Parking Management System
# ESP32 + MicroPython
# =============================================================================
#
# WiFi protocol used:
#   network.WLAN(network.STA_IF) — Station mode, connects to existing router
#   socket.getaddrinfo("0.0.0.0", 80) — binds web server to all interfaces
#
# EXECUTION ORDER:
#   1. Connect to WiFi (STA mode)
#   2. Start web server socket on port 80
#   3. Initialise all hardware drivers
#   4. Start Telegram + Blynk
#   5. Enter main loop — runs forever
#
# FILE STRUCTURE:
#   main.py         ← You are here
#   config.py       ← All settings and pin assignments
#   state.py        ← Shared system state object
#   hardware.py     ← All hardware drivers
#   telegram_bot.py ← Telegram bot handler
#   web_server.py   ← ESP32 web dashboard server
#   blynk_client.py ← Blynk IoT platform client
#
# REQUIRED LIBRARY FILES (upload to ESP32 root /):
#   tm1637.py   → https://github.com/mcauser/micropython-tm1637
#   lcd_api.py  → https://github.com/dhylands/python_lcd
#   i2c_lcd.py  → https://github.com/dhylands/python_lcd
# =============================================================================

import time
import network
import socket

import config
from state    import ParkingState
from hardware import (
    UltrasonicSensor,
    IRSensors,
    ServoGate,
    DHT11Sensor,
    RelayLight,
    SlotDisplay,
    StatusLCD,
)
from telegram_bot  import TelegramBot
from web_server    import WebServer
from blynk_client  import BlynkClient


# =============================================================================
# WIFI SETUP (Station Mode)
# =============================================================================

def connect_wifi():
    """
    Connects ESP32 to WiFi in Station (STA) mode.
    Exactly matches the protocol:

        wifi = network.WLAN(network.STA_IF)
        wifi.active(True)
        wifi.connect(ssid, password)
        while not wifi.isconnected(): time.sleep(1)
        ip = wifi.ifconfig()[0]

    Returns the connected WLAN object, or None if connection fails.
    """
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)

    # If already connected from a previous boot, skip reconnect
    if wifi.isconnected():
        ip = wifi.ifconfig()[0]
        print("Connected!")
        print("ESP32 IP address:", ip)
        return wifi

    print("Connecting to WiFi...")
    wifi.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    # Wait until connected or timeout
    start = time.time()
    while not wifi.isconnected():
        if time.time() - start > config.WIFI_TIMEOUT:
            print("WiFi connection FAILED — check SSID and password in config.py")
            return None
        time.sleep(1)

    ip = wifi.ifconfig()[0]
    print("Connected!")
    print("ESP32 IP address:", ip)
    print("Web dashboard:   http://" + ip + "/")
    return wifi


# =============================================================================
# WEB SERVER SOCKET SETUP
# =============================================================================

def create_server_socket():
    """
    Creates and binds the web server socket.
    Exactly matches the protocol:

        addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
        s = socket.socket()
        s.bind(addr)
        s.listen(1)

    Binding to "0.0.0.0" means the server listens on ALL network interfaces —
    so it works on both the WiFi IP and any other interface simultaneously.

    Returns the bound socket object, or None if setup fails.
    """
    try:
        # getaddrinfo resolves "0.0.0.0" + port into a socket address tuple
        addr = socket.getaddrinfo("0.0.0.0", config.WEB_SERVER_PORT)[0][-1]

        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow port reuse on reboot
        s.bind(addr)
        s.listen(1)
        s.settimeout(0.1)  # Non-blocking: returns immediately if no connection waiting

        print("Web server socket bound to port", config.WEB_SERVER_PORT)
        return s

    except Exception as e:
        print("Web server socket error:", e)
        return None


# =============================================================================
# PARKING LOGIC ENGINE
# =============================================================================

class ParkingLogic:
    """
    Core decision-making engine.
    Reads sensors, updates state, and controls actuators.
    Called every iteration of the main loop.
    """

    def __init__(self, state, hw):
        self.state = state
        self.hw    = hw
        self._gate_open_time = None  # Timestamp when gate was last opened

    def update_ir_sensors(self):
        """
        Reads all IR sensors and updates slot occupancy in shared state.
        Triggers a Telegram full-parking notification when parking just became full.
        Updates TM1637 and LCD immediately on any slot change.
        """
        was_full   = self.state.is_full
        new_status = self.hw['ir'].read_all()
        changed    = new_status != self.state.slot_status

        if changed:
            self.state.slot_status = new_status
            if config.DEBUG_MODE:
                print("[Logic] Slots:", new_status, "| Available:", self.state.available_slots)

            # Update local displays immediately when slots change
            self.hw['tm'].show(self.state.available_slots)
            self.hw['lcd'].update(self.state)

            # Notify Telegram if parking just became full
            if self.state.is_full and not was_full:
                self.state.send_telegram_notification = (
                    "🚫 <b>Parking FULL</b> — all slots are occupied."
                )
                self.hw['lcd'].show_message("  PARKING FULL", " No slots avail.")

    def update_environment(self):
        """
        Reads DHT11 temperature and humidity into shared state.
        DHT11 class throttles reads internally (every DHT11_INTERVAL_SEC seconds).
        """
        temp, hum = self.hw['dht'].read()
        self.state.temperature = temp
        self.state.humidity    = hum

    def run_gate_logic(self):
        """
        Automatic gate logic:
        - Vehicle detected + slots available → open gate
        - Gate open + vehicle cleared + timeout elapsed → close gate
        Manual override from Telegram / Web / Blynk also works by setting
        state.gate_open and calling servo directly from those modules.
        """
        vehicle_present = self.hw['ultrasonic'].vehicle_detected()
        self.state.vehicle_at_gate = vehicle_present

        # Auto-open when vehicle arrives and slots are free
        if vehicle_present and not self.state.gate_open:
            if self.state.available_slots > 0:
                print("[Logic] Vehicle detected → Gate opening")
                self.hw['servo'].open()
                self.state.gate_open    = True
                self._gate_open_time    = time.time()
                self.hw['lcd'].show_message(" Vehicle Detected", "  Gate OPENING...")
            else:
                print("[Logic] Vehicle detected → Parking FULL")
                self.hw['lcd'].show_message("  PARKING FULL", "  Sorry, no slots")

        # Auto-close after timeout once vehicle has cleared
        if (self.state.gate_open
                and self._gate_open_time is not None
                and not vehicle_present):
            elapsed = time.time() - self._gate_open_time
            if elapsed >= config.GATE_AUTO_CLOSE_SEC:
                print("[Logic] Auto-closing gate")
                self.hw['servo'].close()
                self.state.gate_open = False
                self._gate_open_time = None
                self.hw['lcd'].update(self.state)

    def run_light_logic(self):
        """
        Optional auto-light control.
        Set AUTO_LIGHT = True in config.py to enable.
        Lights ON when any slot is occupied, OFF when all slots are empty.
        """
        if not config.AUTO_LIGHT:
            return

        any_occupied = any(self.state.slot_status)
        if any_occupied and not self.state.light_on:
            self.hw['relay'].turn_on()
            self.state.light_on = True
            print("[Logic] Auto-lights ON")
        elif not any_occupied and self.state.light_on:
            self.hw['relay'].turn_off()
            self.state.light_on = False
            print("[Logic] Auto-lights OFF")

    def run_all(self):
        """Runs all logic in sequence. Called every main loop iteration."""
        self.update_ir_sensors()
        self.update_environment()
        self.run_gate_logic()
        self.run_light_logic()


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    print("=" * 50)
    print("  Smart IoT Parking Management System")
    print("  ESP32 + MicroPython")
    print("=" * 50)

    # ── Step 1: Connect to WiFi ───────────────────────────────────────────────
    wifi = connect_wifi()
    if not wifi:
        print("No WiFi — running hardware only (no IoT platforms)")

    # ── Step 2: Create web server socket ─────────────────────────────────────
    # Socket is created here and passed directly into WebServer so the
    # same socket object is shared — no double-binding.
    server_sock = None
    if wifi:
        server_sock = create_server_socket()

    # ── Step 3: Initialise shared state ──────────────────────────────────────
    state = ParkingState()

    # ── Step 4: Initialise all hardware drivers ───────────────────────────────
    print("[Main] Initialising hardware...")
    hw = {
        'ultrasonic': UltrasonicSensor(),
        'ir':         IRSensors(),
        'servo':      ServoGate(),
        'dht':        DHT11Sensor(),
        'relay':      RelayLight(),
        'tm':         SlotDisplay(),
        'lcd':        StatusLCD(),
    }

    # ── Step 5: Home gate to closed position ─────────────────────────────────
    print("[Main] Closing gate...")
    hw['servo'].close()
    state.gate_open = False

    # ── Step 6: Startup display ───────────────────────────────────────────────
    hw['lcd'].show_message("  Smart Parking", "  Starting...")
    time.sleep(2)
    hw['lcd'].update(state)
    hw['tm'].show(state.available_slots)

    # ── Step 7: Initialise IoT platforms ─────────────────────────────────────
    telegram = None
    web      = None
    blynk    = None

    if wifi and wifi.isconnected():
        # Web server — pass the pre-created socket directly
        if server_sock:
            web = WebServer(state, hw, server_sock)
            print("[Main] Web server ready")

        # Telegram bot
        telegram = TelegramBot(state, hw)
        print("[Main] Telegram bot ready")

        # Blynk client
        blynk = BlynkClient(state, hw)
        print("[Main] Blynk client ready")

        # Send startup notification
        ip = wifi.ifconfig()[0]
        telegram.send_message(
            "✅ <b>Smart Parking Online</b>\n"
            "🌐 Web: http://" + ip + "/\n"
            "Type /help for commands."
        )

        hw['lcd'].show_message("WiFi OK", ip)
        time.sleep(2)
        hw['lcd'].update(state)
    else:
        print("[Main] No WiFi — IoT platforms disabled")
        hw['lcd'].show_message("  WiFi OFFLINE", "  Local Mode")

    # ── Step 8: Create logic engine ───────────────────────────────────────────
    logic = ParkingLogic(state, hw)

    print("[Main] System ready. Entering main loop...")
    print("-" * 50)

    # ── Step 9: Main loop — runs forever ──────────────────────────────────────
    loop_count = 0
    while True:
        try:
            # a. Sensors + parking decision logic
            logic.run_all()

            # b. IoT platform polling (each handles its own timing internally)
            if telegram: telegram.poll()
            if web:      web.poll()
            if blynk:    blynk.poll()

            # c. Debug summary every 30 loops (~6 seconds)
            if config.DEBUG_MODE and loop_count % 30 == 0:
                print("[State]", state.summary())

            loop_count += 1
            time.sleep_ms(200)  # 200ms per loop iteration

        except KeyboardInterrupt:
            print("\n[Main] Shutting down...")
            hw['servo'].close()
            hw['relay'].turn_off()
            hw['lcd'].show_message("  System", "  Shutdown")
            if server_sock:
                server_sock.close()
            break

        except Exception as e:
            print("[Main] Loop error:", e)
            time.sleep(1)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()

