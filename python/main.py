"""
AI Haptic Vision Navigation Headband — Main AI Pipeline Orchestrator.
Coordinates: Laptop Webcam -> YOLOv8 Detection -> Position Analysis -> Navigation Decisions -> Dashboard Bridge.
"""

import sys
import os
import time
import socket
import threading

# Add parent directory to sys.path so modules can be imported from root or python/ dir
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from python.config import (
    CAMERA_INDEX,
    YOLO_MODEL,
    CONFIDENCE_THRESHOLD,
    API_BASE_URL,
    API_STATE_URL,
    API_FRAME_URL,
    SEND_FRAMES_TO_SERVER,
    ARDUINO_ENABLED,
    ARDUINO_PORT,
    ARDUINO_BAUD
)
from python.camera import Camera
from python.detector import ObjectDetector
from python.position_analyzer import PositionAnalyzer
from python.navigation_engine import NavigationEngine
from python.state_sender import StateSender
from python.arduino_controller import ArduinoController


def is_server_running(host="127.0.0.1", port=8000) -> bool:
    """Checks if the local dashboard HTTP server is already running."""
    try:
        with socket.create_connection((host, port), timeout=0.6):
            return True
    except OSError:
        return False


def start_background_server(port=8000):
    """Starts the dashboard server in a daemon thread if not already running."""
    try:
        from server import run_server
        server_thread = threading.Thread(
            target=run_server,
            kwargs={"port": port, "open_browser": True},
            daemon=True,
            name="DashboardServerThread"
        )
        server_thread.start()
        print(f"[BRIDGE] Started integrated dashboard server on port {port}.")
        time.sleep(1.0)
    except Exception as e:
        print(f"[BRIDGE WARNING] Could not auto-start dashboard server: {e}")


class AIPipeline:
    """Master controller orchestrating the end-to-end perception and navigation loop."""

    def __init__(self, camera_index=CAMERA_INDEX, model_name=YOLO_MODEL):
        self.camera = Camera(camera_index=camera_index)
        self.detector = ObjectDetector(model_name=model_name, conf_threshold=CONFIDENCE_THRESHOLD)
        self.analyzer = PositionAnalyzer()
        self.nav_engine = NavigationEngine()
        self.sender = StateSender(state_url=API_STATE_URL, frame_url=API_FRAME_URL)
        self.arduino = ArduinoController(port=ARDUINO_PORT, baud=ARDUINO_BAUD, enabled=ARDUINO_ENABLED)

        self.running = False
        self.last_log_print_time = 0.0
        self.last_state_send_time = 0.0
        self.last_haptic_time = 0.0
        self.last_logged_command = None

    def start(self):
        """Initializes hardware and models, then enters the real-time processing loop."""
        print("=" * 65)
        print("  AI HAPTIC VISION NAVIGATION HEADBAND — LAPTOP POC")
        print("  'See the Path. Feel the Direction. Navigate with Confidence.'")
        print("=" * 65)

        # Check if local dashboard server is running; if not, launch it seamlessly
        if not is_server_running("127.0.0.1", 8000):
            print("[BRIDGE] Dashboard server not detected on port 8000. Launching integrated bridge...")
            start_background_server(8000)
        else:
            print("[BRIDGE] Existing dashboard server detected on http://127.0.0.1:8000")

        # 1. Load YOLOv8 Model
        if not self.detector.load_model():
            print("[FATAL] Could not initialize YOLOv8. Exiting.")
            return

        # 2. Open Camera
        if not self.camera.open():
            print("[FATAL] Could not open laptop webcam. Please check camera permissions/availability. Exiting.")
            return

        # 3. Initial System Ready handshake to dashboard & Arduino
        print("[SYSTEM] Transmitting initial 'system_ready' signal...")
        self.arduino.send_navigation_command("system_ready")
        self.sender.send_state(
            command="system_ready",
            detections=[],
            log_message="System initialized — Camera, YOLOv8 & Arduino ready",
            sub="All modules ready",
            demo=False,
            arduino_status=self.arduino.status,
            arduino_command=self.arduino.last_sent_command,
            arduino_ack=self.arduino.last_ack,
            arduino_port=self.arduino.active_port or ""
        )

        self.running = True
        print("[SYSTEM] AI Vision Pipeline ACTIVE. Press Ctrl+C in terminal to stop.")
        print("-" * 65)

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n[SYSTEM] Interrupted by user. Shutting down cleanly...")
        finally:
            self.stop()

    def _main_loop(self):
        """High-performance frame processing and decision cycle."""
        while self.running:
            # 1. Read webcam frame
            success, frame = self.camera.read()
            if not success or frame is None:
                time.sleep(0.01)
                continue

            # 2. Run YOLOv8 object detection
            raw_detections, annotated_frame = self.detector.detect(frame)

            # 3. Analyze horizontal positions and spatial proximity
            enriched_detections = self.analyzer.analyze(raw_detections)

            # 4. Compute navigation guidance via decision engine
            command, log_msg, sub_msg, is_new_command = self.nav_engine.decide(enriched_detections)

            now = time.time()

            # Transmit confirmed navigation command to Arduino Nano:
            # Trigger immediately on command change OR periodically every 2.0s while obstacle/stop persists
            is_active_guidance = command in ("move_left", "move_right", "stop", "slow_down", "wait_for_a_while")
            should_repulse = is_active_guidance and (now - self.last_haptic_time >= 2.0)

            if is_new_command or should_repulse:
                self.arduino.send_navigation_command(command)
                self.last_haptic_time = now

            # 5. Broadcast state to dashboard
            # Send when command changes OR periodically every 0.25s to keep dashboard state fresh
            state_needed = is_new_command or (now - self.last_state_send_time >= 0.25)
            if state_needed:
                self.sender.send_state(
                    command=command,
                    detections=enriched_detections,
                    log_message=log_msg,
                    sub=sub_msg,
                    demo=False,
                    arduino_status=self.arduino.status,
                    arduino_command=self.arduino.last_sent_command,
                    arduino_ack=self.arduino.last_ack,
                    arduino_port=self.arduino.active_port or ""
                )
                self.last_state_send_time = now

            # 6. Stream video frame to dashboard
            if SEND_FRAMES_TO_SERVER:
                self.sender.send_frame(annotated_frame)

            # 7. Clean, throttled terminal logging
            self._log_terminal(command, enriched_detections, is_new_command)

            # Brief yield to keep CPU balanced
            time.sleep(0.005)

    def _log_terminal(self, command: str, detections: list, is_new_command: bool):
        """Displays clear, human-readable terminal updates without spamming."""
        now = time.time()
        # Print when command changes or at most once every 3 seconds for heartbeat
        if is_new_command or (now - self.last_log_print_time >= 3.0):
            det_summary = []
            for d in detections[:3]:
                det_summary.append(f"{d['object']} ({d['confidence']:.2f}) [{d['position'].upper()}]")
            det_str = ", ".join(det_summary) if det_summary else "No obstacles (Clear)"

            fps_str = f"{self.camera.current_fps} FPS" if self.camera.current_fps > 0 else ""
            bridge_status = "Connected" if self.sender.is_connected else "Connecting..."
            ard_info = f"Arduino: {self.arduino.status}"
            if self.arduino.active_port:
                ard_info += f" ({self.arduino.active_port})"
            if self.arduino.last_sent_command != "—":
                ard_info += f" [TX: {self.arduino.last_sent_command} | ACK: {self.arduino.last_ack}]"

            print(f"[NAV: {command.upper():<14}] Detections: {det_str} | Bridge: {bridge_status} | {ard_info} {fps_str}")
            self.last_log_print_time = now
            self.last_logged_command = command

    def stop(self):
        """Releases camera, Arduino serial, and network resources cleanly."""
        self.running = False
        print("[SYSTEM] Stopping pipeline...")
        self.camera.release()
        try:
            self.arduino.send_navigation_command("stop")
            self.arduino.close()
        except Exception:
            pass
        try:
            self.sender.send_state(
                command="stop",
                detections=[],
                log_message="AI Vision Pipeline Stopped",
                sub="Camera stopped",
                demo=False,
                arduino_status=self.arduino.status,
                arduino_command="S",
                arduino_ack=self.arduino.last_ack,
                arduino_port=self.arduino.active_port or ""
            )
        except Exception:
            pass
        print("[SYSTEM] AI Vision Pipeline closed.")


def main():
    pipeline = AIPipeline()
    pipeline.start()


if __name__ == "__main__":
    main()
