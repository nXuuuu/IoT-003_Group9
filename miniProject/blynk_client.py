# =============================================================================
# blynk_client.py — Blynk IoT Platform Integration
# Smart IoT Parking Management System
# =============================================================================
# Protocol based on:
#
#   def read_button_v0():
#       r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&V0")
#       value = int(str(r.text).strip('[]"{}'))
#       r.close()
#       return value
#
#   def send_temperature_v1(temp):
#       url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V1={temp}"
#       r = requests.get(url)
#       r.close()
#
# Virtual Pin assignments (must match your Blynk app widgets):
#   V0 → Gate button      (read  — app sends 0 or 1)
#   V1 → Light button     (read  — app sends 0 or 1)
#   V2 → Available slots  (write — display widget)
#   V3 → Temperature °C   (write — display widget)
#   V4 → Humidity %       (write — display widget)
#   V5 → Gate status      (write — display widget)
# =============================================================================

import urequests as requests
import time
import config

# Blynk API base URL — plain HTTP, no SSL, no memory errors
BLYNK_API   = "http://blynk.cloud/external/api"
BLYNK_TOKEN = config.BLYNK_AUTH_TOKEN


# =============================================================================
# LOW-LEVEL READ / WRITE — matching the exact protocol
# =============================================================================

def read_pin(pin):
    """
    Reads a virtual pin from Blynk app.
    Matches the protocol:
        r = requests.get(f"{BLYNK_API}/get?token={BLYNK_TOKEN}&V0")
        value = int(str(r.text).strip('[]"{}'))
        r.close()
        return value

    Returns integer value (0 or 1 for buttons), or None on error.
    """
    try:
        r = requests.get(BLYNK_API + "/get?token=" + BLYNK_TOKEN + "&" + pin)
        value = int(str(r.text).strip('[]"{}'))
        r.close()
        return value
    except Exception as e:
        if config.DEBUG_MODE:
            print("[Blynk] GET error", pin + ":", e)
        return None


def write_pin(pin, value):
    """
    Writes a value to a Blynk display widget.
    Matches the protocol:
        url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&V1={value}"
        r = requests.get(url)
        r.close()
    """
    try:
        url = f"{BLYNK_API}/update?token={BLYNK_TOKEN}&{pin}={value}"
        r = requests.get(url)
        r.close()
        if config.DEBUG_MODE:
            print("[Blynk] PUT", pin, "=", value)
    except Exception as e:
        if config.DEBUG_MODE:
            print("[Blynk] PUT error", pin + ":", e)


# =============================================================================
# NAMED PIN FUNCTIONS — one function per pin, matching the protocol style
# =============================================================================

def read_gate_button():
    """Reads V0 — Gate control button from Blynk app. Returns 0 or 1."""
    return read_pin(config.BLYNK_VP_GATE_BTN)

def read_light_button():
    """Reads V1 — Light control button from Blynk app. Returns 0 or 1."""
    return read_pin(config.BLYNK_VP_LIGHT_BTN)

def send_slots(available):
    """Writes V2 — Available slot count to Blynk display widget."""
    write_pin(config.BLYNK_VP_SLOTS, available)

def send_temperature(temp):
    """Writes V3 — Temperature value to Blynk display widget."""
    write_pin(config.BLYNK_VP_TEMP, round(temp, 1))

def send_humidity(hum):
    """Writes V4 — Humidity value to Blynk display widget."""
    write_pin(config.BLYNK_VP_HUMIDITY, round(hum, 1))

def send_gate_status(is_open):
    """Writes V5 — Gate status string to Blynk display widget."""
    write_pin(config.BLYNK_VP_GATE_STATUS, "OPEN" if is_open else "CLOSED")


# =============================================================================
# BLYNK CLIENT CLASS — wraps the pin functions with timing and state logic
# =============================================================================


class BlynkClient:
    """
    Manages periodic push and read cycles for all Blynk virtual pins.
    Uses the named pin functions above internally.
    """

    def __init__(self, state, hardware):
        self.state = state
        self.hw    = hardware

        self._last_push = 0
        self._last_read = 0
        self._push_interval = 5   # ✏️  Push display data every N seconds
        self._read_interval = 2   # ✏️  Read button state every N seconds

        # Remember last button values to detect changes only
        self._last_gate_val  = None
        self._last_light_val = None

    # ── Push all display widgets ──────────────────────────────────────────────

    def push_state(self):
        """
        Pushes current system values to all Blynk display widgets.
        Calls each named send function in sequence.
        """
        s = self.state
        send_slots(s.available_slots)
        send_temperature(s.temperature)
        send_humidity(s.humidity)
        send_gate_status(s.gate_open)

    # ── Read all button widgets ───────────────────────────────────────────────

    def read_commands(self):
        """
        Reads gate and light button pins from Blynk app.
        Only triggers hardware action when the value CHANGES —
        prevents the gate from repeatedly toggling on every poll.
        """

        # ── Gate button (V0) ──────────────────────────────────────────────
        gate_val = read_gate_button()
        if gate_val is not None and gate_val != self._last_gate_val:
            self._last_gate_val = gate_val
            if gate_val == 1 and not self.state.gate_open:
                self.hw['servo'].open()
                self.state.gate_open = True
                print("[Blynk] Gate OPENED via app")
            elif gate_val == 0 and self.state.gate_open:
                self.hw['servo'].close()
                self.state.gate_open = False
                print("[Blynk] Gate CLOSED via app")

        # ── Light button (V1) ─────────────────────────────────────────────
        light_val = read_light_button()
        if light_val is not None and light_val != self._last_light_val:
            self._last_light_val = light_val
            if light_val == 1 and not self.state.light_on:
                self.hw['relay'].turn_on()
                self.state.light_on = True
                print("[Blynk] Lights ON via app")
            elif light_val == 0 and self.state.light_on:
                self.hw['relay'].turn_off()
                self.state.light_on = False
                print("[Blynk] Lights OFF via app")

    # ── Main poll (called from main loop) ─────────────────────────────────────

    def poll(self):
        """
        Called every main loop iteration.
        Push and read run on their own independent intervals.
        """
        now = time.time()

        if now - self._last_push >= self._push_interval:
            self.push_state()
            self._last_push = now

        if now - self._last_read >= self._read_interval:
            self.read_commands()
            self._last_read = now
