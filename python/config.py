"""
Central Configuration for AI Haptic Vision Navigation Headband.
All thresholds, model settings, camera parameters, and API endpoints are configured here.
"""

# ============================================================
# CAMERA SETTINGS
# ============================================================
CAMERA_INDEX = 0             # Default laptop webcam index
FRAME_WIDTH = 640            # Capture width
FRAME_HEIGHT = 480           # Capture height
TARGET_FPS = 30              # Target camera loop FPS

# ============================================================
# YOLOv8 MODEL SETTINGS
# ============================================================
# Using lightweight YOLOv8n pretrained model for real-time laptop demonstration
import os
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, "yolov8n.pt")
YOLO_MODEL = LOCAL_MODEL_PATH if os.path.exists(LOCAL_MODEL_PATH) else "yolov8n.pt"

# Confidence threshold: ignore weak detections below this value
CONFIDENCE_THRESHOLD = 0.50

# Common objects of interest for assistive obstacle detection
TARGET_CLASSES = [
    "person", "car", "chair", "table", "bicycle", "motorcycle",
    "bus", "truck", "dog", "cat", "couch", "bed", "bottle",
    "tv", "laptop", "door", "backpack", "suitcase"
]

# ============================================================
# HORIZONTAL POSITION BOUNDARIES (Normalized 0.0 - 1.0)
# ============================================================
# 0.0 to LEFT_THRESHOLD  -> LEFT
# LEFT_THRESHOLD to RIGHT_THRESHOLD -> CENTER
# RIGHT_THRESHOLD to 1.0 -> RIGHT
LEFT_THRESHOLD = 0.33
RIGHT_THRESHOLD = 0.66

# Approximate visual proximity thresholds (Normalized bounding box area: width * height)
# > 0.18: Object takes up significant visual field -> immediate hazard -> STOP
PROXIMITY_STOP_AREA = 0.18

# > 0.07: Object ahead taking moderate visual field -> caution -> SLOW DOWN
PROXIMITY_SLOW_AREA = 0.07

# ============================================================
# TEMPORAL STABILITY & COOLDOWN SETTINGS
# ============================================================
# Number of consecutive frames a candidate command must persist before being accepted
COMMAND_CONFIRMATION_FRAMES = 3

# Minimum seconds before the same navigation command can be re-broadcasted to audio
COMMAND_COOLDOWN_SECONDS = 3.0

# Minimum seconds between 'object_detected' announcements when an obstacle appears
OBJECT_DETECTED_COOLDOWN_SECONDS = 5.0

# ============================================================
# DASHBOARD API / BRIDGE ENDPOINTS
# ============================================================
API_BASE_URL = "http://127.0.0.1:8000"
API_STATE_URL = f"{API_BASE_URL}/api/state"
API_FRAME_URL = f"{API_BASE_URL}/api/frame"

# Frame streaming settings
SEND_FRAMES_TO_SERVER = True
FRAME_JPEG_QUALITY = 75       # JPEG compression quality for fast streaming
FRAME_STREAM_FPS_LIMIT = 20   # Maximum frame POST rate to preserve bandwidth/CPU
