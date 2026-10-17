"""
Arduino Nano Serial Controller Module (Phase 1):
Manages non-blocking serial communication between the AI Navigation Engine and the Arduino Nano.
Sends directional command codes (L, R, S, C) and monitors acknowledgements (ACK:L, ACK:R, ACK:S, ACK:C).
"""

import time
import queue
import threading
from typing import Optional, Dict
import serial
import serial.tools.list_ports


# Mapping from existing navigation decision engine commands to Phase 1 serial codes
COMMAND_TO_SERIAL: Dict[str, str] = {
    "move_left": "L",
    "move_right": "R",
    "stop": "S",
    "slow_down": "S",
    "wait_for_a_while": "S",
    "obstacle_detected": "S",
    "move_backward": "S",
    "move_straight": "C",
    "start_walking": "C",
    "system_ready": "C",
}


def find_arduino_port() -> Optional[str]:
    """
    Scans available COM ports for an Arduino Nano (including CH340, FTDI, and official boards).
    Returns the port string (e.g. 'COM7') if a unique match is found, otherwise None.
    """
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("[ARDUINO] No serial ports found on this system.")
        return None

    candidates = []
    # Known VID/PID or keywords for Arduino Nano and clones (CH340, FTDI, Atmega)
    nano_keywords = ["ch340", "arduino", "ftdi", "usb-serial", "1a86:7523", "2341:", "0403:6001"]

    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        combined = f"{desc} {hwid}"
        if any(kw in combined for kw in nano_keywords):
            candidates.append(p)

    if len(candidates) == 1:
        match = candidates[0]
        print(f"[ARDUINO] Auto-detected Arduino device on {match.device} ({match.description})")
        return match.device

    if len(candidates) > 1:
        print(f"[ARDUINO WARNING] Multiple potential Arduino devices detected:")
        for c in candidates:
            print(f"  - {c.device}: {c.description} ({c.hwid})")
        print("  Please specify ARDUINO_PORT in python/config.py to select one explicitly.")
        return None

    # No obvious match among ports
    print("[ARDUINO] Could not automatically identify an Arduino Nano among available ports:")
    for p in ports:
        print(f"  - {p.device}: {p.description}")
    print("  Set ARDUINO_PORT = 'COMX' in python/config.py to specify your port manually.")
    return None


class ArduinoController:
    """
    Handles background, non-blocking serial communication with the Arduino Nano.
    Transmits L/R/S/C commands and logs acknowledgements without stalling the AI video loop.
    """

    def __init__(self, port: Optional[str] = "AUTO", baud: int = 115200, enabled: bool = True):
        self.configured_port = port
        self.baud = baud
        self.enabled = enabled

        # Connection and state tracking
        self.active_port: Optional[str] = None
        self.status: str = "Disconnected"  # "Disconnected" | "Connecting" | "Connected"
        self.last_sent_command: str = "—"
        self.last_ack: str = "—"
        self.last_ack_time: float = 0.0

        # Background worker management
        self._serial: Optional[serial.Serial] = None
        self._tx_queue: queue.Queue = queue.Queue(maxsize=16)
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        if self.enabled:
            self._start_worker()

    def _start_worker(self):
        """Starts the background serial communication worker thread."""
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._communication_loop,
            name="ArduinoSerialWorker",
            daemon=True
        )
        self._worker_thread.start()

    def send_navigation_command(self, nav_command: str) -> bool:
        """
        Translates a confirmed navigation command into its serial counterpart (L/R/S/C)
        and queues it for non-blocking transmission to the Arduino.
        """
        if not self.enabled:
            return False

        serial_code = COMMAND_TO_SERIAL.get(nav_command)
        if not serial_code:
            # Unknown command; safety-first: do not assume clear path
            return False

        # Avoid redundant rapid queue flood if same code is already pending
        try:
            # Drop older unsent items if queue is full to ensure lowest latency
            if self._tx_queue.full():
                try:
                    self._tx_queue.get_nowait()
                except queue.Empty:
                    pass
            self._tx_queue.put_nowait(serial_code)
            return True
        except queue.Full:
            return False

    def _resolve_port(self) -> Optional[str]:
        """Resolves target port either from configuration or auto-detection."""
        if not self.configured_port or self.configured_port.upper() == "AUTO":
            return find_arduino_port()
        return self.configured_port

    def _communication_loop(self):
        """
        Dedicated background worker: manages connect/reconnect, non-blocking TX, and incoming RX.
        """
        reconnect_delay = 3.0
        last_reconnect_attempt = 0.0

        while self._running:
            # 1. Ensure serial port is connected
            if self._serial is None or not self._serial.is_open:
                now = time.time()
                if now - last_reconnect_attempt >= reconnect_delay:
                    last_reconnect_attempt = now
                    port_to_try = self._resolve_port()
                    if port_to_try:
                        self._connect(port_to_try)
                    else:
                        self.status = "Disconnected"
                time.sleep(0.1)
                continue

            # 2. Process outgoing commands from the queue
            try:
                while not self._tx_queue.empty():
                    code = self._tx_queue.get_nowait()
                    message = f"{code}\n".encode("ascii")
                    self._serial.write(message)
                    self._serial.flush()
                    self.last_sent_command = code
                    # Debug log throttled
                    # print(f"[ARDUINO TX] Sent: {code}")
            except Exception as e:
                print(f"[ARDUINO ERROR] Write error: {e}")
                self._disconnect()
                continue

            # 3. Read incoming serial responses (ACK:L, ACK:R, ACK:S, ACK:C, HAPTIC_READY)
            try:
                if self._serial and self._serial.in_waiting:
                    raw_line = self._serial.readline()
                    line = raw_line.decode("ascii", errors="replace").strip()
                    if line:
                        if line == "HAPTIC_READY":
                            self.status = "Connected"
                            self.last_ack = "HAPTIC_READY"
                            self.last_ack_time = time.time()
                            print(f"[ARDUINO RX] Arduino Nano ready: {line}")
                        elif line.startswith("ACK:"):
                            self.last_ack = line
                            self.last_ack_time = time.time()
                            # print(f"[ARDUINO RX] {line}")
                        else:
                            # Other debug outputs from Arduino
                            self.last_ack = line
                            self.last_ack_time = time.time()
            except Exception as e:
                print(f"[ARDUINO ERROR] Read error: {e}")
                self._disconnect()
                continue

            time.sleep(0.01)

    def _connect(self, port_name: str):
        """Opens the serial connection with proper DTR reset handling."""
        self.status = "Connecting"
        self.active_port = port_name
        print(f"[ARDUINO] Connecting to Arduino Nano on {port_name} at {self.baud} baud...")

        try:
            self._serial = serial.Serial(
                port=port_name,
                baudrate=self.baud,
                timeout=0.2,
                write_timeout=0.2
            )
            # Give Arduino Nano time to reset upon DTR toggle
            time.sleep(1.8)
            # Flush startup bootloader noise
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

            self.status = "Connected"
            print(f"[ARDUINO] Successfully connected to {port_name}.")
        except (serial.SerialException, OSError) as e:
            print(f"[ARDUINO] Failed to open {port_name}: {e}")
            self._disconnect()

    def _disconnect(self):
        """Closes the serial port cleanly."""
        self.status = "Disconnected"
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def close(self):
        """Stops the worker thread and releases serial resources cleanly."""
        print("[ARDUINO] Closing Arduino controller...")
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        self._disconnect()
        print("[ARDUINO] Arduino connection closed.")
