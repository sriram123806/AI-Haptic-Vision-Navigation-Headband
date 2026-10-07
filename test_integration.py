"""End-to-end integration test: Server, Camera, YOLO, Navigation, and Bridge API."""
import sys
import os
import time
import threading
import urllib.request
import json

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import run_server
from python.camera import Camera
from python.detector import ObjectDetector
from python.position_analyzer import PositionAnalyzer
from python.navigation_engine import NavigationEngine
from python.state_sender import StateSender

print("=== STARTING INTEGRATION TEST ===")

# 1. Start Server on port 8001 to avoid conflicting with any port 8000
port = 8001
server_thread = threading.Thread(target=run_server, kwargs={"port": port, "open_browser": False}, daemon=True)
server_thread.start()
time.sleep(1.0)
print(f"[TEST] Test server started on port {port}")

# 2. Test GET /api/state initial response
req = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=2)
data = json.loads(req.read().decode())
print(f"[TEST] Initial /api/state: {data}")
assert "command" in data, "Failed to get state"

# 3. Test Camera
cam = Camera()
cam_ok = cam.open()
assert cam_ok, "Camera failed to open"
ret, frame = cam.read()
assert ret and frame is not None, "Failed to read camera frame"
print(f"[TEST] Camera read frame shape: {frame.shape}")

# 4. Test YOLOv8 Detector
detector = ObjectDetector()
det_ok = detector.load_model()
assert det_ok, "YOLOv8 failed to load"
detections, annotated_frame = detector.detect(frame)
print(f"[TEST] YOLO detected {len(detections)} object(s) in live frame")

# 5. Test Position Analyzer
analyzer = PositionAnalyzer()
enriched = analyzer.analyze(detections)
print(f"[TEST] Position analyzer enriched detections: {enriched}")

# 6. Test Navigation Engine
nav_engine = NavigationEngine()
cmd, log_msg, sub_msg, is_new = nav_engine.decide(enriched)
print(f"[TEST] Navigation decision: Command='{cmd}', Log='{log_msg}'")

# 7. Test State Sender
sender = StateSender(state_url=f"http://127.0.0.1:{port}/api/state", frame_url=f"http://127.0.0.1:{port}/api/frame")
sent_state = sender.send_state(cmd, enriched, log_msg, sub_msg, demo=False)
assert sent_state, "Failed to send state"
print("[TEST] State successfully sent via POST /api/state")

sent_frame = sender.send_frame(annotated_frame)
assert sent_frame, "Failed to send frame"
print("[TEST] Frame successfully sent via POST /api/frame")

# 8. Verify GET /api/state receives updated data
time.sleep(0.1)
req2 = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=2)
data2 = json.loads(req2.read().decode())
print(f"[TEST] Verified /api/state response: command={data2.get('command')}, has_frame={data2.get('has_frame')}")
assert data2.get("command") == cmd, f"Expected command {cmd}, got {data2.get('command')}"
assert data2.get("has_frame") is True, "Expected has_frame to be True"

# Clean up
cam.release()
print("\n>>> END-TO-END INTEGRATION TEST PASSED PERFECTLY! <<<")
