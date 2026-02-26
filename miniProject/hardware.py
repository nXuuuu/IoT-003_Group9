# =============================================================================
# hardware.py — Hardware Drivers & Sensor Readers
# Smart IoT Parking Management System
# =============================================================================
# This module initialises and controls all physical hardware:
#   - Ultrasonic sensor (HC-SR04)
#   - IR sensors (slot occupancy)
#   - Servo motor (gate)
#   - DHT11 (temperature & humidity)
#   - Relay module (lights)
#   - TM1637 7-segment display (slot count)
#   - LCD I2C display (system status)
# =============================================================================

import time
import machine
import dht
from machine import Pin, PWM, I2C, SoftI2C
import config

# ── Try to import TM1637 driver ───────────────────────────────────────────────
# MicroPython does not include TM1637 by default.
# Upload tm1637.py from: https://github.com/mcauser/micropython-tm1637
try:
    import tm1637
    TM1637_AVAILABLE = True
except ImportError:
    TM1637_AVAILABLE = False
    print("[HW] WARNING: tm1637 module not found — 7-seg display disabled")

# ── Try to import LCD I2C driver ─────────────────────────────────────────────
# Upload lcd_api.py and i2c_lcd.py from:
# https://github.com/dhylands/python_lcd
try:
    from i2c_lcd import I2cLcd
    LCD_AVAILABLE = True
except ImportError:
    LCD_AVAILABLE = False
    print("[HW] WARNING: i2c_lcd module not found — LCD display disabled")


# =============================================================================
# ULTRASONIC SENSOR — HC-SR04
# =============================================================================
class UltrasonicSensor:
    """
    Measures distance using HC-SR04 ultrasonic sensor.
    Used to detect vehicles arriving at the parking entrance.
    """

    def __init__(self):
        self.trig = Pin(config.ULTRASONIC_TRIG_PIN, Pin.OUT)
        self.echo = Pin(config.ULTRASONIC_ECHO_PIN, Pin.IN)
        self.trig.value(0)

    def read_distance_cm(self):
        """
        Send a 10µs pulse on TRIG, measure echo duration, return distance in cm.
        Returns -1 if measurement times out (no object detected within range).
        """
        # Send trigger pulse
        self.trig.value(0)
        time.sleep_us(2)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)

        # Wait for echo to go HIGH (with timeout)
        timeout_start = time.ticks_us()
        while self.echo.value() == 0:
            if time.ticks_diff(time.ticks_us(), timeout_start) > 30000:
                return -1  # Timeout — no object

        # Measure how long echo stays HIGH
        echo_start = time.ticks_us()
        while self.echo.value() == 1:
            if time.ticks_diff(time.ticks_us(), echo_start) > 30000:
                return -1  # Timeout — object too far

        echo_end = time.ticks_us()
        duration_us = time.ticks_diff(echo_end, echo_start)

        # Convert to centimetres: speed of sound ≈ 0.0343 cm/µs, divide by 2 (round trip)
        distance_cm = (duration_us * 0.0343) / 2
        return round(distance_cm, 1)

    def vehicle_detected(self):
        """Returns True if a vehicle is within the detection threshold."""
        d = self.read_distance_cm()
        if config.DEBUG_MODE:
            print(f"[Ultrasonic] Distance: {d} cm")
        return d != -1 and d < config.ULTRASONIC_THRESHOLD_CM


# =============================================================================
# IR SENSORS — Slot Occupancy
# =============================================================================
class IRSensors:
    """
    Reads 3 IR sensor inputs to determine occupancy of each parking slot.
    Most IR modules output LOW when object is detected (beam blocked).
    Set IR_INVERT = True in config.py for this behaviour.
    """

    def __init__(self):
        self.pins = [
            Pin(config.IR_SLOT1_PIN, Pin.IN),
            Pin(config.IR_SLOT2_PIN, Pin.IN),
            Pin(config.IR_SLOT3_PIN, Pin.IN),
        ]

    def read_all(self):
        """
        Returns a list of booleans:
          True  = slot is OCCUPIED
          False = slot is FREE
        Index 0 = Slot 1, Index 1 = Slot 2, Index 2 = Slot 3
        """
        results = []
        for i, pin in enumerate(self.pins):
            raw = pin.value()
            occupied = (raw == 0) if config.IR_INVERT else (raw == 1)
            results.append(occupied)
            if config.DEBUG_MODE:
                print(f"[IR] Slot {i+1}: raw={raw} → {'OCCUPIED' if occupied else 'FREE'}")
        return results


# =============================================================================
# SERVO MOTOR — Gate Barrier
# =============================================================================
class ServoGate:
    """
    Controls a servo motor to open or close the parking gate barrier.
    Uses PWM signal: 50Hz frequency, duty cycle maps to angle.

    Standard servo pulse range:
      0°  = ~1ms pulse  = duty 40  (out of 1023)
      90° = ~1.5ms pulse = duty 77
      180°= ~2ms pulse   = duty 115

    ✏️  Adjust SERVO_OPEN_DEG and SERVO_CLOSE_DEG in config.py to calibrate.
    """

    def __init__(self):
        self.pwm = PWM(Pin(config.SERVO_PIN), freq=50)
        self._current_angle = None

    def _angle_to_duty(self, angle):
        """Converts angle (0–180°) to PWM duty cycle (0–1023)."""
        # Map 0°→40, 180°→115 (standard SG90 servo)
        min_duty = 40
        max_duty = 115
        return int(min_duty + (angle / 180.0) * (max_duty - min_duty))

    def set_angle(self, angle):
        """Moves servo to specified angle (0–180°)."""
        duty = self._angle_to_duty(angle)
        self.pwm.duty(duty)
        self._current_angle = angle
        time.sleep_ms(500)  # Allow servo to reach position

    def open(self):
        """Opens the gate barrier."""
        if config.DEBUG_MODE:
            print(f"[Servo] Opening gate → {config.SERVO_OPEN_DEG}°")
        self.set_angle(config.SERVO_OPEN_DEG)

    def close(self):
        """Closes the gate barrier."""
        if config.DEBUG_MODE:
            print(f"[Servo] Closing gate → {config.SERVO_CLOSE_DEG}°")
        self.set_angle(config.SERVO_CLOSE_DEG)


# =============================================================================
# DHT11 SENSOR — Temperature & Humidity
# =============================================================================
class DHT11Sensor:
    """
    Reads temperature (°C) and humidity (%) from DHT11 sensor.
    DHT11 needs at least 1 second between readings.
    """

    def __init__(self):
        self.sensor = dht.DHT11(Pin(config.DHT11_PIN))
        self._last_read_time = 0
        self._last_temp = 0.0
        self._last_hum  = 0.0

    def read(self):
        """
        Reads sensor if enough time has passed since last read.
        Returns (temperature_celsius, humidity_percent).
        Returns last known values if called too soon.
        """
        now = time.time()
        if now - self._last_read_time >= config.DHT11_INTERVAL_SEC:
            try:
                self.sensor.measure()
                self._last_temp = self.sensor.temperature()
                self._last_hum  = self.sensor.humidity()
                self._last_read_time = now
                if config.DEBUG_MODE:
                    print(f"[DHT11] Temp: {self._last_temp}°C  Hum: {self._last_hum}%")
            except Exception as e:
                print(f"[DHT11] Read error: {e}")
        return self._last_temp, self._last_hum


# =============================================================================
# RELAY MODULE — Parking Lights
# =============================================================================
class RelayLight:
    """
    Controls a relay module to switch parking lights ON or OFF.
    Most relay modules are ACTIVE LOW (LOW signal = relay ON).
    Set RELAY_ACTIVE_LOW = True in config.py to match this behaviour.
    """

    def __init__(self):
        self.pin = Pin(config.RELAY_PIN, Pin.OUT)
        self.turn_off()  # Start with lights OFF

    def _write(self, state):
        """Writes pin value, inverting if relay is active-low."""
        if config.RELAY_ACTIVE_LOW:
            self.pin.value(0 if state else 1)
        else:
            self.pin.value(1 if state else 0)

    def turn_on(self):
        """Turns parking lights ON."""
        self._write(True)
        if config.DEBUG_MODE:
            print("[Relay] Lights ON")

    def turn_off(self):
        """Turns parking lights OFF."""
        self._write(False)
        if config.DEBUG_MODE:
            print("[Relay] Lights OFF")

    def toggle(self, current_state):
        """Toggles light state. Pass current state (True/False)."""
        if current_state:
            self.turn_off()
        else:
            self.turn_on()


# =============================================================================
# TM1637 7-SEGMENT DISPLAY — Slot Counter
# =============================================================================
class SlotDisplay:
    """
    Shows available parking slot count on TM1637 4-digit 7-segment display.
    Displays as: 'SL 2' meaning 'Slots: 2 available'
    Falls back gracefully if TM1637 library not installed.
    """

    def __init__(self):
        if TM1637_AVAILABLE:
            self.display = tm1637.TM1637(
                clk=Pin(config.TM1637_CLK_PIN),
                dio=Pin(config.TM1637_DIO_PIN)
            )
            self.display.brightness(config.TM1637_BRIGHTNESS)
            self.show(0)  # Initialise to 0
        else:
            self.display = None

    def show(self, available_slots):
        """
        Updates display with number of available slots.
        Format: shows the number right-aligned on the display.
        """
        if config.DEBUG_MODE:
            print(f"[TM1637] Available slots: {available_slots}")
        if self.display:
            # Show number directly (e.g. '   2' for 2 slots)
            self.display.number(available_slots)

    def show_full(self):
        """Displays 'FULL' pattern when parking is full."""
        if self.display:
            # Show 0 to indicate no slots
            self.display.number(0)


# =============================================================================
# LCD I2C DISPLAY — System Status
# =============================================================================
class StatusLCD:
    """
    Shows system status messages on a 16x2 I2C LCD display.
    Line 1: Slot count and gate status
    Line 2: Custom status messages

    ✏️  I2C address is set in config.py as LCD_I2C_ADDR
        Common addresses: 0x27 or 0x3F
    """

    def __init__(self):
        if LCD_AVAILABLE:
            try:
                i2c = SoftI2C(
                    scl=Pin(config.LCD_SCL_PIN),
                    sda=Pin(config.LCD_SDA_PIN),
                    freq=400000
                )
                self.lcd = I2cLcd(i2c, config.LCD_I2C_ADDR, config.LCD_ROWS, config.LCD_COLS)
                self.lcd.backlight_on()
                self.clear()
            except Exception as e:
                print(f"[LCD] Init error: {e}")
                self.lcd = None
        else:
            self.lcd = None

    def clear(self):
        if self.lcd:
            self.lcd.clear()

    def write_line(self, row, text):
        """Writes text to a specific row (0 or 1), padded to 16 chars."""
        if self.lcd:
            padded = text[:16].ljust(16)  # Truncate and pad to exactly 16 chars
            self.lcd.move_to(0, row)
            self.lcd.putstr(padded)

    def update(self, state):
        """
        Refreshes LCD with current system state.
        Row 0: Slots available + gate status
        Row 1: Temperature and light status
        """
        line1 = f"Slots:{state.available_slots}/{state.total_slots} {'OPEN' if state.gate_open else 'CLSD'}"
        line2 = f"T:{state.temperature:.0f}C L:{'ON' if state.light_on else 'OFF'}"
        self.write_line(0, line1)
        self.write_line(1, line2)
        if config.DEBUG_MODE:
            print(f"[LCD] Row0: {line1}")
            print(f"[LCD] Row1: {line2}")

    def show_message(self, line1="", line2=""):
        """Shows a custom two-line message on the LCD."""
        self.write_line(0, line1)
        self.write_line(1, line2)
