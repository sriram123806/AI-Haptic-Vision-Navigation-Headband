"""
Safe Standalone Serial Communication Test for Arduino Nano (Phase 1).
Sends: C -> L -> R -> S -> C
Verifies matching acknowledgements (ACK:C, ACK:L, ACK:R, ACK:S, ACK:C).
Runs without starting the webcam or YOLOv8 models.
"""

import sys
import os
import time
import serial
import serial.tools.list_ports

# Add root directory to sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from python.config import ARDUINO_PORT, ARDUINO_BAUD
from python.arduino_controller import find_arduino_port


def run_serial_test(port_override=None):
    print("=" * 65)
    print("  AI HAPTIC VISION HEADBAND — ARDUINO NANO SERIAL TEST (PHASE 1)")
    print("  Protocol Sequence: C -> L -> R -> S -> C")
    print("=" * 65)

    # 1. Resolve Target COM Port
    target_port = port_override or ARDUINO_PORT
    if not target_port or str(target_port).upper() == "AUTO":
        print("[TEST] Searching for connected Arduino Nano...")
        target_port = find_arduino_port()

    if not target_port:
        print("\n[ERROR] No Arduino Nano detected or port not specified.")
        print("Available COM ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  - {p.device}: {p.description}")
        print("\nSet ARDUINO_PORT = 'COMX' in python/config.py or pass port as argument:")
        print("  python test_arduino.py COM7\n")
        return False

    print(f"[TEST] Opening {target_port} at {ARDUINO_BAUD} baud...")

    try:
        ser = serial.Serial(
            port=target_port,
            baudrate=ARDUINO_BAUD,
            timeout=1.5,
            write_timeout=1.0
        )
    except serial.SerialException as e:
        print(f"\n[ERROR] Could not open {target_port}: {e}")
        print("  - If another program (Arduino IDE Serial Monitor, main.py) is using this port, close it first.")
        print("  - Verify USB cable connection.\n")
        return False

    try:
        # Give Arduino time to reset after DTR toggle
        print("[TEST] Waiting for Arduino bootloader & ready signal (approx 2s)...")
        time.sleep(2.0)

        # Check for HAPTIC_READY
        boot_msg = ""
        if ser.in_waiting:
            boot_msg = ser.readline().decode("ascii", errors="replace").strip()
            print(f"[TEST] Arduino initial message: '{boot_msg}'")

        ser.reset_input_buffer()
        ser.reset_output_buffer()

        test_sequence = [
            ("C", "ACK:C", "Move Straight / Clear Path"),
            ("L", "ACK:L", "Move Left"),
            ("R", "ACK:R", "Move Right"),
            ("S", "ACK:S", "Stop / Hazard"),
            ("C", "ACK:C", "Resume Clear Path"),
        ]

        print("-" * 65)
        print(f"{'STEP':<6}{'CMD':<6}{'EXPECTED':<12}{'RECEIVED':<14}{'LATENCY':<12}{'RESULT'}")
        print("-" * 65)

        all_passed = True

        for idx, (cmd, expected_ack, desc) in enumerate(test_sequence, 1):
            time.sleep(0.4)  # Small pause between commands
            t0 = time.time()
            ser.write(f"{cmd}\n".encode("ascii"))
            ser.flush()

            # Read response
            response = ser.readline().decode("ascii", errors="replace").strip()
            elapsed_ms = (time.time() - t0) * 1000

            is_match = (response == expected_ack)
            status_text = "PASS" if is_match else "FAIL"
            if not is_match:
                all_passed = False

            print(f"#{idx:<5}{cmd:<6}{expected_ack:<12}{response:<14}{elapsed_ms:>6.1f} ms    {status_text} ({desc})")

        print("-" * 65)
        if all_passed:
            print("[SUCCESS] All 5 communication steps verified successfully!")
            print(f"          Arduino Nano on {target_port} is fully operational.")
        else:
            print("[NOTICE] One or more commands did not receive the expected ACK.")
            print("         Please ensure 'nano_haptic_test.ino' is uploaded to the Arduino.")
        print("-" * 65)
        return all_passed

    finally:
        ser.close()
        print(f"[TEST] Port {target_port} closed cleanly.\n")


if __name__ == "__main__":
    cli_port = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_serial_test(cli_port)
    sys.exit(0 if success else 1)
