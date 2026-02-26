# =============================================================================
# telegram_bot.py — Telegram Bot Handler
# Smart IoT Parking Management System
# =============================================================================
# Implements polling-based Telegram bot with commands:
#   /status    → Full system status report
#   /open      → Manually open the gate
#   /close     → Manually close the gate
#   /slots     → Show slot availability
#   /temp      → Show temperature & humidity
#   /light_on  → Turn parking lights ON
#   /light_off → Turn parking lights OFF
#
# Uses HTTP GET polling — no WebSocket or asyncio needed on MicroPython.
# =============================================================================

import urequests
import ujson
import time
import config


class TelegramBot:
    """
    Handles Telegram Bot API communication via long-polling.

    How it works:
    1. Polls /getUpdates with an offset to receive new messages
    2. Parses command text from incoming messages
    3. Executes the matching command and sends a reply
    4. Sends outbound notifications when triggered by the system
    """

    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, state, hardware):
        """
        state    → shared ParkingState object
        hardware → dict of hardware drivers (servo, relay, etc.)
        """
        self.state    = state
        self.hw       = hardware
        self.token    = config.TELEGRAM_TOKEN
        self.chat_id  = config.TELEGRAM_CHAT_ID
        self.offset   = 0       # Tracks last processed update ID
        self._last_poll = 0     # Timestamp of last poll

        # ✏️  Add or remove commands from this dict to extend bot functionality
        self.commands = {
            "/status":    self._cmd_status,
            "/open":      self._cmd_open,
            "/close":     self._cmd_close,
            "/slots":     self._cmd_slots,
            "/temp":      self._cmd_temp,
            "/light_on":  self._cmd_light_on,
            "/light_off": self._cmd_light_off,
            "/help":      self._cmd_help,
        }

    # ── API Helpers ───────────────────────────────────────────────────────────

    def _api_url(self, method):
        return f"{self.BASE_URL}{self.token}/{method}"

    def send_message(self, text, chat_id=None):
        """Sends a text message to the configured chat ID."""
        target = chat_id or self.chat_id
        try:
            url = self._api_url("sendMessage")
            payload = ujson.dumps({
                "chat_id": target,
                "text": text,
                "parse_mode": "HTML"   # Allows <b>bold</b> and <code>code</code>
            })
            r = urequests.post(url, data=payload,
                               headers={"Content-Type": "application/json"})
            r.close()
            if config.DEBUG_MODE:
                print(f"[Telegram] Sent: {text[:60]}")
        except Exception as e:
            print(f"[Telegram] Send error: {e}")

    def _get_updates(self):
        """Polls Telegram for new messages since last offset."""
        try:
            url = self._api_url(f"getUpdates?offset={self.offset}&timeout=1&limit=5")
            r = urequests.get(url)
            data = ujson.loads(r.text)
            r.close()
            return data.get("result", [])
        except Exception as e:
            print(f"[Telegram] Poll error: {e}")
            return []

    # ── Command Handlers ──────────────────────────────────────────────────────

    def _cmd_status(self, chat_id):
        """Replies with a full system status report."""
        s = self.state
        slots_detail = "\n".join(
            f"  Slot {i+1}: {'🔴 Occupied' if s.slot_status[i] else '🟢 Free'}"
            for i in range(s.total_slots)
        )
        msg = (
            f"<b>🅿️ Parking Status</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🚗 Available: <b>{s.available_slots}/{s.total_slots}</b>\n"
            f"{slots_detail}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🚧 Gate: <b>{'OPEN' if s.gate_open else 'CLOSED'}</b>\n"
            f"💡 Lights: <b>{'ON' if s.light_on else 'OFF'}</b>\n"
            f"🌡 Temp: <b>{s.temperature:.1f}°C</b>\n"
            f"💧 Humidity: <b>{s.humidity:.1f}%</b>"
        )
        self.send_message(msg, chat_id)

    def _cmd_open(self, chat_id):
        """Manually opens the gate barrier."""
        self.hw['servo'].open()
        self.state.gate_open = True
        self.send_message("🚧 Gate is now <b>OPEN</b>.", chat_id)

    def _cmd_close(self, chat_id):
        """Manually closes the gate barrier."""
        self.hw['servo'].close()
        self.state.gate_open = False
        self.send_message("🔒 Gate is now <b>CLOSED</b>.", chat_id)

    def _cmd_slots(self, chat_id):
        """Reports available slot count."""
        s = self.state
        if s.is_full:
            msg = "🚫 <b>Parking is FULL</b> — no slots available."
        else:
            msg = f"🟢 <b>{s.available_slots} slot(s) available</b> out of {s.total_slots}."
        self.send_message(msg, chat_id)

    def _cmd_temp(self, chat_id):
        """Reports current temperature and humidity."""
        s = self.state
        msg = (
            f"🌡 Temperature: <b>{s.temperature:.1f}°C</b>\n"
            f"💧 Humidity: <b>{s.humidity:.1f}%</b>"
        )
        self.send_message(msg, chat_id)

    def _cmd_light_on(self, chat_id):
        """Turns parking lights ON via relay."""
        self.hw['relay'].turn_on()
        self.state.light_on = True
        self.send_message("💡 Parking lights turned <b>ON</b>.", chat_id)

    def _cmd_light_off(self, chat_id):
        """Turns parking lights OFF via relay."""
        self.hw['relay'].turn_off()
        self.state.light_on = False
        self.send_message("🌑 Parking lights turned <b>OFF</b>.", chat_id)

    def _cmd_help(self, chat_id):
        """Sends the command list."""
        msg = (
            "<b>📋 Available Commands</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            "/status    — Full system status\n"
            "/slots     — Available slot count\n"
            "/open      — Open the gate\n"
            "/close     — Close the gate\n"
            "/temp      — Temperature & humidity\n"
            "/light_on  — Turn lights ON\n"
            "/light_off — Turn lights OFF\n"
            "/help      — Show this menu"
        )
        self.send_message(msg, chat_id)

    # ── Notification (Outbound) ───────────────────────────────────────────────

    def check_and_send_notification(self):
        """
        Checks if a notification was queued by the system (e.g. parking full alert).
        Set state.send_telegram_notification = "your message" from anywhere
        to trigger this.
        """
        if self.state.send_telegram_notification:
            self.send_message(self.state.send_telegram_notification)
            self.state.send_telegram_notification = None  # Clear after sending

    # ── Main Poll Loop (called from main.py) ──────────────────────────────────

    def poll(self):
        """
        Call this regularly from the main loop.
        Checks for new messages and handles commands.
        Respects the poll interval set in config.py.
        """
        now = time.time()
        if now - self._last_poll < config.TELEGRAM_POLL_INTERVAL:
            return  # Not time to poll yet
        self._last_poll = now

        # Check for outbound notification first
        self.check_and_send_notification()

        # Poll for incoming messages
        updates = self._get_updates()
        for update in updates:
            self.offset = update["update_id"] + 1  # Advance offset to avoid reprocessing
            try:
                msg = update.get("message", {})
                text = msg.get("text", "").strip().lower()
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if config.DEBUG_MODE:
                    print(f"[Telegram] Received: '{text}' from {chat_id}")

                # Match command (strip bot username if present, e.g. /open@MyBot → /open)
                base_cmd = text.split("@")[0]

                if base_cmd in self.commands:
                    self.commands[base_cmd](chat_id)
                elif text:
                    self.send_message(
                        "❓ Unknown command. Type /help for the command list.",
                        chat_id
                    )
            except Exception as e:
                print(f"[Telegram] Message parse error: {e}")
