# =============================================================================
# state.py — Global Shared System State
# Smart IoT Parking Management System
# =============================================================================
# This module holds the live state of the entire parking system.
# All modules read from and write to this single shared object so that
# every platform (Web, Telegram, Blynk) always sees the same data.
# =============================================================================

from config import TOTAL_SLOTS

class ParkingState:
    """
    Central state object.
    Import this class and create ONE instance in main.py,
    then pass it to every module that needs it.
    """

    def __init__(self):
        # ── Slot occupancy ─────────────────────────────────────────────────
        self.total_slots     = TOTAL_SLOTS  # Max capacity (from config)
        self.slot_status     = [False] * TOTAL_SLOTS
        #   slot_status[i] = True  → Slot (i+1) is OCCUPIED
        #   slot_status[i] = False → Slot (i+1) is FREE

        # ── Gate ───────────────────────────────────────────────────────────
        self.gate_open       = False  # True = gate is currently open

        # ── Lights (Relay) ─────────────────────────────────────────────────
        self.light_on        = False  # True = parking lights are ON

        # ── Environment ────────────────────────────────────────────────────
        self.temperature     = 0.0   # °C from DHT11
        self.humidity        = 0.0   # % from DHT11

        # ── Flags for inter-module communication ───────────────────────────
        self.vehicle_at_gate = False  # True = ultrasonic sees a vehicle
        self.send_telegram_notification = None
        #   Set to a string message to trigger Telegram outbound notification
        #   Cleared to None after the message is sent

    @property
    def available_slots(self):
        """Returns number of currently FREE slots (computed, not stored)."""
        return self.total_slots - sum(self.slot_status)

    @property
    def is_full(self):
        """Returns True if all slots are occupied."""
        return self.available_slots == 0

    def slot_label(self, index):
        """Returns human-readable status for slot index (0-based)."""
        return "OCCUPIED" if self.slot_status[index] else "FREE"

    def summary(self):
        """Returns a single-line summary string — useful for debugging."""
        slots_str = " | ".join(
            f"S{i+1}:{'OCC' if s else 'FREE'}"
            for i, s in enumerate(self.slot_status)
        )
        return (
            f"Slots:{self.available_slots}/{self.total_slots} "
            f"[{slots_str}] "
            f"Gate:{'OPEN' if self.gate_open else 'CLOSED'} "
            f"Light:{'ON' if self.light_on else 'OFF'} "
            f"Temp:{self.temperature:.1f}C "
            f"Hum:{self.humidity:.1f}%"
        )
