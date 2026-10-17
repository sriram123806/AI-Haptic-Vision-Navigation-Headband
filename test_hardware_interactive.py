"""
AI Haptic Vision Navigation Headband — Interactive Hardware Diagnostic Tool.
Tests serial commands, Pin 13 LED, D5 (Left), D6 (Right), and detects hardware reboots.
"""

import sys
import os
import time
import serial
import serial.tools.list_ports

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from python.arduino_controller import find_arduino_port
from python.config import ARDUINO_BAUD


def test_command(ser, cmd, desc):
    print(f"\n[TESTING] Sending '{cmd}' ({desc})...")
    ser.reset_input_buffer()
    t0 = time.time()
    ser.write(f"{cmd}\n".encode("ascii"))
    ser.flush()

    # Listen for 1.2 seconds to catch both ACK and any unexpected reboot (HAPTIC_READY)
    messages = []
    reboot_detected = False
    deadline = time.time() + 1.2

    while time.time() < deadline:
        if ser.in_waiting:
            line = ser.readline().decode("ascii", errors="replace").strip()
            if line:
                elapsed = (time.time() - t0) * 1000
                messages.append((elapsed, line))
                if "HAPTIC_READY" in line:
                    reboot_detected = True
        time.sleep(0.01)

    # Print log
    for elapsed, msg in messages:
        marker = " ⚠️ [REBOOT DETECTED!]" if "HAPTIC_READY" in msg else ""
        print(f"  + {elapsed:6.1f} ms -> {msg}{marker}")

    if not messages:
        print("  [TIMEOUT] No response from Arduino!")
    elif reboot_detected:
        print("  ❌ RESULT: HARDWARE REBOOTED! The circuit on this pin pulled down the 5V power rail.")
    else:
        print("  ✅ RESULT: PASS! Clean response, no hardware reset.")

    return not reboot_detected and len(messages) > 0


def main():
    print("=" * 65)
    print("  AI HAPTIC VISION HEADBAND — INTERACTIVE HARDWARE DIAGNOSTIC")
    print("=" * 65)

    port = find_arduino_port()
    if not port:
        print("[ERROR] Arduino Nano not detected.")
        return

    print(f"[CONNECT] Opening {port} at {ARDUINO_BAUD} baud...")
    ser = serial.Serial(port=port, baudrate=ARDUINO_BAUD, timeout=0.5)

    try:
        print("[INIT] Waiting for bootloader...")
        time.sleep(2.0)
        while ser.in_waiting:
            boot = ser.readline().decode("ascii", errors="replace").strip()
            print(f"  Boot message: {boot}")

        while True:
            print("\n" + "-" * 50)
            print("Select an option:")
            print("  [1] Test 'C' (Clear / Motors OFF)")
            print("  [2] Test 'L' (Obstacle on Left -> Steer Right -> D6 / Right Motor)")
            print("  [3] Test 'R' (Obstacle on Right -> Steer Left -> D5 / Left Motor)")
            print("  [4] Test 'S' (Hazard / Stop -> Both Motors)")
            print("  [5] Run Full Sequence (C -> L -> R -> S -> C)")
            print("  [q] Quit")
            print("-" * 50)

            choice = input("Enter choice (1-5 or q): ").strip().lower()
            if choice == "q":
                break
            elif choice == "1":
                test_command(ser, "C", "Motors OFF / Clear Path")
            elif choice == "2":
                test_command(ser, "L", "Right Channel / Pin D6")
            elif choice == "3":
                test_command(ser, "R", "Left Channel / Pin D5")
            elif choice == "4":
                test_command(ser, "S", "Both Channels / Alert")
            elif choice == "5":
                for c, d in [("C", "Motors OFF"), ("L", "Right Channel D6"), ("R", "Left Channel D5"), ("S", "Both Channels Alert"), ("C", "Motors OFF")]:
                    test_command(ser, c, d)
                    time.sleep(0.5)
            else:
                print("Invalid choice.")

    finally:
        ser.close()
        print(f"\n[DONE] Port {port} closed cleanly.")


if __name__ == "__main__":
    main()
