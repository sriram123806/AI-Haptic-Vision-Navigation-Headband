"""Unit test for Position Analyzer and Navigation Decision Engine."""
import sys
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from python.config import COMMAND_CONFIRMATION_FRAMES
from python.position_analyzer import PositionAnalyzer
from python.navigation_engine import NavigationEngine

analyzer = PositionAnalyzer()
engine = NavigationEngine()

print("--- Running Test 1: Obstacle on LEFT ---")
left_det = [{"object": "person", "confidence": 0.91, "box": [0.05, 0.2, 0.25, 0.85]}]
enriched = analyzer.analyze(left_det)
assert enriched[0]["position"] == "left", f"Expected left, got {enriched[0]['position']}"
for _ in range(COMMAND_CONFIRMATION_FRAMES):
    cmd, log, sub, is_new = engine.decide(enriched)
assert cmd == "move_right", f"Expected move_right, got {cmd}"
print(f"PASS: Command: {cmd} | Log: {log}")

print("--- Running Test 2: Obstacle on RIGHT ---")
right_det = [{"object": "car", "confidence": 0.88, "box": [0.70, 0.3, 0.95, 0.75]}]
enriched = analyzer.analyze(right_det)
assert enriched[0]["position"] == "right"
for _ in range(COMMAND_CONFIRMATION_FRAMES):
    cmd, log, sub, is_new = engine.decide(enriched)
assert cmd == "move_left", f"Expected move_left, got {cmd}"
print(f"PASS: Command: {cmd} | Log: {log}")

print("--- Running Test 3: Obstacle in CENTER ---")
center_det = [{"object": "chair", "confidence": 0.85, "box": [0.35, 0.2, 0.60, 0.8]}]
enriched = analyzer.analyze(center_det)
assert enriched[0]["position"] == "center"
for _ in range(COMMAND_CONFIRMATION_FRAMES):
    cmd, log, sub, is_new = engine.decide(enriched)
assert cmd == "stop", f"Expected stop, got {cmd}"
print(f"PASS: Command: {cmd} | Log: {log}")

print("--- Running Test 4: Clear Scene (Path Clear) ---")
for _ in range(COMMAND_CONFIRMATION_FRAMES):
    cmd, log, sub, is_new = engine.decide([])
assert cmd in ("start_walking", "move_straight"), f"Expected start_walking or move_straight, got {cmd}"
print(f"PASS: Command: {cmd} | Log: {log}")

print("--- Running Test 5: Temporal Stability Prevention of Single-Frame Flicker ---")
# Reset engine
engine2 = NavigationEngine(confirmation_frames=3)
# Initial state
engine2.decide([])
# Single frame blip on left
candidate_cmd, _, _, is_new = engine2.decide(enriched)
# Should NOT change confirmed command on a single frame blip!
assert is_new is False, "Candidate command should not be confirmed on 1st frame"
print(f"PASS: Flickering prevention working properly (is_new={is_new})")

print("\n>>> ALL 5 CORE NAVIGATION LOGIC TESTS PASSED SUCCESSFULLY! <<<")
