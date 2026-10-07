# AI Haptic Vision Navigation Headband — Laptop Proof of Concept

> **“See the Path. Feel the Direction. Navigate with Confidence.”**

An assistive vision and directional navigation system designed to empower visually impaired individuals. This repository contains the complete **Laptop Proof of Concept (POC)** demonstrating real-time obstacle perception, horizontal position analysis, rule-based navigational guidance, voice synthesis playback, and synchronized visual haptic simulation.

---

## Table of Contents
1. [Project Purpose](#1-project-purpose)
2. [Architecture](#2-architecture)
3. [Prerequisites & Python Version](#3-prerequisites--python-version)
4. [Installation & Dependencies](#4-installation--dependencies)
5. [Starting the System](#5-starting-the-system)
   - [Method A: All-in-One Automatic Launcher](#method-a-all-in-one-automatic-launcher-recommended)
   - [Method B: Separate Dashboard & AI Terminals](#method-b-separate-dashboard--ai-terminals)
6. [Webcam Requirements](#6-webcam-requirements)
7. [YOLOv8 Model & Perception](#7-yolov8-model--perception)
8. [Central Configuration](#8-central-configuration)
9. [Navigation Decision Engine Logic](#9-navigation-decision-engine-logic)
10. [Temporal Stability & Cooldowns](#10-temporal-stability--cooldowns)
11. [Audio System & ElevenLabs Voice Files](#11-audio-system--elevenlabs-voice-files)
12. [Haptic Simulation (Wristband)](#12-haptic-simulation-wristband)
13. [Demo Mode](#13-demo-mode)
14. [Dashboard REST API & MJPEG Stream](#14-dashboard-rest-api--mjpeg-stream)
15. [Known Limitations](#15-known-limitations)
16. [Future Hardware: ESP32-CAM Headband Integration](#16-future-hardware-esp32-cam-headband-integration)
17. [Future Hardware: Physical Wristband Vibration Motors](#17-future-hardware-physical-wristband-vibration-motors)

---

## 1. Project Purpose
The **AI Haptic Vision Navigation Headband** serves as a lightweight, privacy-preserving assistive perception tool. In this laptop proof-of-concept phase, the laptop's built-in webcam functions as the camera sensor (standing in for a future headband-mounted ESP32-CAM), local YOLOv8 neural inference processes visual scenes, and the system translates detected obstacles into directional guidance delivered through spatial voice output and haptic pulse animations.

> **Disclaimer:** This prototype is an assistive mobility research tool and proof-of-concept. It is **not** a certified medical device, does not provide physical range-finding/LiDAR depth measurement, and is **not** a replacement for a white cane, guide dog, or certified mobility specialist training.

---

## 2. Architecture

```
                    ┌─────────────────────────┐
                    │      LAPTOP WEBCAM      │
                    └────────────┬────────────┘
                                 │ OpenCV (BGR Frames)
                                 ▼
                    ┌─────────────────────────┐
                    │   YOLOv8 Object Model   │ (yolov8n.pt)
                    └────────────┬────────────┘
                                 │ Detections [class, conf, box]
                                 ▼
                    ┌─────────────────────────┐
                    │    Position Analyzer    │ (Left / Center / Right / Area)
                    └────────────┬────────────┘
                                 │ Enriched Spatial Coordinates
                                 ▼
                    ┌─────────────────────────┐
                    │ Navigation Decision Eng │ (Temporal Confirmation & Safety Rules)
                    └────────────┬────────────┘
                                 │ JSON State & JPEG Frames
                                 ▼
                    ┌─────────────────────────┐
                    │ Dashboard Bridge Server │ (server.py: http://127.0.0.1:8000)
                    └────────────┬────────────┘
                                 │ Polling / SSE / MJPEG
                                 ▼
                    ┌─────────────────────────┐
                    │   Web UI & Simulator    │ (index.html / app.js)
                    └─────┬─────────────┬─────┘
                          │             │
                          ▼             ▼
                 ┌────────────────┐  ┌─────────────────────┐
                 │  Voice Output  │  │  Haptic Simulation  │
                 │ (11 MP3 Files) │  │ (Directional Pulses)│
                 └────────────────┘  └─────────────────────┘
```

---

## 3. Prerequisites & Python Version
- **Operating System:** Windows 10/11, macOS, or Linux.
- **Python Version:** **Python 3.9+** (Tested on Python 3.11, 3.12, and 3.13).
- **Web Browser:** Google Chrome, Microsoft Edge, or Mozilla Firefox.
- **Hardware:** Standard laptop webcam (640x480 or 1280x720) and built-in laptop speakers.

---

## 4. Installation & Dependencies

1. Clone or extract the project folder:
   ```bash
   cd PROJECT_ABSE
   ```

2. Install the minimal Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Dependencies in `requirements.txt`:*
   - `ultralytics>=8.0.0` (YOLOv8 object detection)
   - `opencv-python>=4.8.0` (Camera capture and image processing)
   - `requests>=2.28.0` (Local bridge HTTP communication)

---

## 5. Starting the System

### Method A: All-in-One Automatic Launcher (Recommended)
You can start the entire stack with a single command:
```bash
python python/main.py
```
What happens automatically:
1. `main.py` detects if the local dashboard bridge server is running; if not, it automatically boots `server.py` in the background on port `8000`.
2. The browser automatically opens to `http://localhost:8000`.
3. The pretrained YOLOv8n model loads into memory.
4. The laptop camera activates, streams real-time frames with bounding boxes, and transmits decisions.
5. In the browser dashboard, click **▶ Start System** to enable audio output.

### Method B: Separate Dashboard & AI Terminals
If you prefer running the dashboard and AI pipeline in separate terminal windows:

**Terminal 1 (Bridge Server):**
```bash
python server.py
```
*Serves the web dashboard at `http://localhost:8000`.*

**Terminal 2 (AI Perception Pipeline):**
```bash
python python/main.py
```
*Connects to the webcam, runs YOLOv8 inference, and sends updates to the server.*

---

## 6. Webcam Requirements
- Uses the standard built-in laptop webcam (`CAMERA_INDEX = 0`).
- Tested with standard resolution `640x480` at 30 FPS.
- Incorporates Windows DirectShow (`cv2.CAP_DSHOW`) fallback for instant, reliable video stream initialization.
- Non-blocking error handling ensures that if the camera is disconnected or in use by another app, clear descriptive logs appear in the terminal instead of unhandled exceptions.

---

## 7. YOLOv8 Model & Perception
- Model: Pretrained **`yolov8n.pt`** (YOLOv8 Nano, ~6.2 MB).
- Fast CPU-based real-time inference suitable for any standard modern laptop without requiring dedicated GPU acceleration.
- Pretrained on standard COCO dataset objects (person, chair, table, bicycle, car, dog, etc.).
- Bounding-box coordinates are normalized from `0.0` to `1.0` `[x1, y1, x2, y2]` to maintain resolution independence between camera capture and dashboard rendering.

---

## 8. Central Configuration
All key parameters are centralized in [`python/config.py`](file:///python/config.py):

| Parameter | Default Value | Description |
|---|---|---|
| `CAMERA_INDEX` | `0` | Default laptop webcam device index |
| `FRAME_WIDTH` | `640` | Video frame capture width |
| `FRAME_HEIGHT` | `480` | Video frame capture height |
| `YOLO_MODEL` | `"yolov8n.pt"` | Pretrained YOLOv8 weights |
| `CONFIDENCE_THRESHOLD` | `0.50` | Rejects detections below 50% confidence |
| `LEFT_THRESHOLD` | `0.33` | Boundary between LEFT and CENTER zones |
| `RIGHT_THRESHOLD` | `0.66` | Boundary between CENTER and RIGHT zones |
| `COMMAND_CONFIRMATION_FRAMES` | `3` | Consecutive frames required to confirm navigation state |
| `COMMAND_COOLDOWN_SECONDS` | `3.0` | Minimum seconds before re-triggering voice/haptic |
| `PROXIMITY_STOP_AREA` | `0.18` | Normalized box area triggering emergency STOP |
| `PROXIMITY_SLOW_AREA` | `0.07` | Normalized box area triggering SLOW DOWN caution |
| `API_STATE_URL` | `"http://127.0.0.1:8000/api/state"` | Dashboard state endpoint |
| `API_FRAME_URL` | `"http://127.0.0.1:8000/api/frame"` | Video frame MJPEG stream endpoint |

---

## 9. Navigation Decision Engine Logic
The navigation engine follows conservative, assistive safety-first principles:

1. **Clear Scene:**
   - If path ahead has no obstacles above threshold: **`move_straight`** (*“Move straight.”*).
   - If resuming after an obstacle had stopped the user: **`start_walking`** (*“Start walking.”*).
2. **Obstacle in Center:**
   - Visual position in the central third of the camera frame represents a direct obstruction in the walking trajectory.
   - High visual proximity / large area (`>= 0.18`) or high confidence: **`stop`** (*“Stop.”*).
   - Moderate visual proximity (`>= 0.07`): **`slow_down`** (*“Slow down.”*).
3. **Obstacle on Left:**
   - Central and right zones are unobstructed: **`move_right`** (*“Move right. Path is clear on the right.”*).
4. **Obstacle on Right:**
   - Central and left zones are unobstructed: **`move_left`** (*“Move left. Path is clear on the left.”*).
5. **Multiple Obstacles:**
   - Obstacles are ranked by zone, approximate visual area (closeness), and confidence.
   - If both left and right have obstacles but center is clear: **`move_straight`** (or **`slow_down`** if path is narrow).
   - If all paths are constricted: **`wait_for_a_while`** or **`stop`**.

---

## 10. Temporal Stability & Cooldowns
In real-time computer vision, single-frame detection noise or lighting flickers can cause rapid oscillation between commands. To ensure comfortable, safe assistive guidance:
- **Frame Confirmation Window:** A candidate decision must persist across **3 consecutive frames** (`COMMAND_CONFIRMATION_FRAMES = 3`) before becoming the active confirmed command (with immediate override for emergency close-proximity stops).
- **Cooldown Debouncing:** Identical audio commands are rate-limited (`COMMAND_COOLDOWN_SECONDS = 3.0`) so the user is never subjected to repetitive, overwhelming voice prompts.

---

## 11. Audio System & ElevenLabs Voice Files
The project preserves all original **ElevenLabs** pre-generated voice recordings stored in [`audio/`](file:///audio/):

| Command Identifier | Spoken Audio Phrase | Audio File |
|---|---|---|
| `system_ready` | “System ready.” | `ElevenLabs_..._System_ready__2026-10-05T18_11_17.mp3` |
| `move_straight` | “Move straight.” | `ElevenLabs_..._Move_straight__2026-10-05T18_11_01.mp3` |
| `move_left` | “Move left.” | `ElevenLabs_..._Move_left__2026-10-05T18_10_54.mp3` |
| `move_right` | “Move right.” | `ElevenLabs_..._Move_right__2026-10-05T18_10_59.mp3` |
| `move_backward` | “Move backward.” | `ElevenLabs_..._Move_backward__2026-10-05T18_11_06.mp3` |
| `stop` | “Stop.” | `ElevenLabs_...__firm__Stop__2026-10-05T18_11_06.mp3` |
| `slow_down` | “Slow down.” | `ElevenLabs_...__firm__Slow_dow_2026-10-05T18_19_05.mp3` |
| `wait_for_a_while` | “Wait for a while.” | `ElevenLabs_..._Wait_for_a_whil_2026-10-05T18_11_12.mp3` |
| `start_walking` | “Start walking.” | `ElevenLabs_...__firm__Start_wa_2026-10-05T18_19_04.mp3` |
| `obstacle_detected`| “Obstacle detected.”| `ElevenLabs_...__firm__Obstacle_2026-10-05T18_11_17.mp3` |
| `object_detected` | “Object detected.” | `ElevenLabs_..._Object_detected_2026-10-05T18_11_24.mp3` |

*No browser Text-to-Speech synthesis is used. Audio mappings are configured in `audio-map.js`.*

---

## 12. Haptic Simulation (Wristband)
Since physical vibration hardware is part of the future implementation phase, the dashboard includes an active visual haptic simulation panel:
- When a `move_left` command triggers, the left haptic wave arcs pulse orange.
- When a `move_right` command triggers, the right haptic wave arcs pulse orange.
- When a `stop`, `slow_down`, or center command triggers, both bilateral arcs pulse simultaneously.
- State indicator toggles to **VIBRATION ACTIVE** during pulses and returns to **VIBRATION READY**.

---

## 13. Demo Mode
Demo Mode remains fully functional for testing or demonstrations without an active camera or YOLO model:
- Click **◈ Demo Mode** on the dashboard side panel.
- Cycles through a sequenced progression of simulated obstacles, zone shifts, audio cues, and haptic pulses.
- Distinctly displays the label **DEMO DATA — NOT REAL YOLO DETECTIONS**.
- When real Python AI data arrives on `/api/state`, Demo Mode gracefully disengages and the dashboard indicates **AI VISION ACTIVE**.

---

## 14. Dashboard REST API & MJPEG Stream
The lightweight local bridge server in `server.py` exposes:

### `POST /api/state`
Receives navigation decisions and detected object metadata from the Python AI pipeline:
```json
{
  "command": "move_right",
  "detections": [
    {
      "object": "person",
      "confidence": 0.91,
      "position": "left",
      "box": [0.10, 0.20, 0.35, 0.85]
    }
  ],
  "log_message": "Person detected on left — Move right",
  "sub": "Path is clear on the right",
  "demo": false
}
```

### `POST /api/frame`
Receives raw JPEG byte stream from OpenCV (`cv2.imencode('.jpg', annotated_frame)`).

### `GET /api/state`
Returns latest JSON state, sequence number, and data freshness age in seconds.

### `GET /stream`
Streams real-time multipart MJPEG (`multipart/x-mixed-replace; boundary=f`) to the dashboard `<img id="stream">` element.

---

## 15. Known Limitations
1. **RGB Monocular Estimation:** Uses 2D bounding-box area as approximate visual proximity rather than true metric distance (LiDAR or Time-of-Flight sensor).
2. **Lighting Sensitivity:** In very dim or backlit lighting conditions, standard RGB cameras may experience lower confidence detections.
3. **Field of View:** Standard laptop webcams provide approximately 60° to 75° field of view, narrower than human peripheral vision.

---

## 16. Future Hardware: ESP32-CAM Headband Integration
In the next development phase:
- An ultra-lightweight **ESP32-CAM module** will be mounted directly onto an elastic or 3D-printed ergonomic headband.
- The ESP32-CAM will stream frames over local Wi-Fi / WebSocket or low-power wireless bridge to the processing host (laptop or wearable compute pack).
- The Python AI pipeline will seamlessly replace `cv2.VideoCapture(0)` with the ESP32-CAM stream URL (e.g. `http://192.168.4.1:81/stream`) without requiring changes to the YOLO detection, position analysis, or navigation engine.

---

## 17. Future Hardware: Physical Wristband Vibration Motors
In the physical wristband phase:
- Dual eccentric rotating mass (ERM) or linear resonant actuator (LRA) vibration motors will be embedded into a wearable wristband or armband.
- Microcontroller (ESP32 or BLE peripheral) will receive directional signals from the navigation engine via Bluetooth Low Energy (BLE) or serial bridge.
- Directional vibration patterns:
  - **Left Wrist / Left Motor:** Pulsed vibration indicates *Move Left*.
  - **Right Wrist / Right Motor:** Pulsed vibration indicates *Move Right*.
  - **Both Motors (Continuous Rapid):** Emergency *STOP* or obstacle directly ahead.
  - **Intermittent Rhythm:** *Slow Down* or *Wait*.
