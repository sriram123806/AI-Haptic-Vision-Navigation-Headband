"""
State Sender Module:
Communicates with the local dashboard HTTP server via REST endpoints.
Transmits structured JSON state and MJPEG video frames with low latency and resilient error handling.
"""

import time
import requests
import cv2
import numpy as np
from typing import List, Dict, Any
from python.config import (
    API_STATE_URL,
    API_FRAME_URL,
    FRAME_JPEG_QUALITY,
    FRAME_STREAM_FPS_LIMIT
)


class StateSender:
    """Manages HTTP bridge communication to the dashboard server."""

    def __init__(self, state_url=API_STATE_URL, frame_url=API_FRAME_URL):
        self.state_url = state_url
        self.frame_url = frame_url
        self.session = requests.Session()

        # Connection status tracking
        self.is_connected = False
        self._last_error_log_time = 0.0
        self._last_frame_post_time = 0.0
        self._min_frame_interval = 1.0 / FRAME_STREAM_FPS_LIMIT if FRAME_STREAM_FPS_LIMIT > 0 else 0.0

    def send_state(
        self,
        command: str,
        detections: List[Dict[str, Any]],
        log_message: str,
        sub: str = "",
        demo: bool = False
    ) -> bool:
        """
        Sends navigation state and detections to POST /api/state.
        """
        # Prepare clean detections without extra internal fields
        clean_dets = []
        for d in detections:
            clean_dets.append({
                "object": d.get("object", "object"),
                "confidence": d.get("confidence", 0.0),
                "position": d.get("position", "center"),
                "box": d.get("box", [0, 0, 0, 0])
            })

        payload = {
            "command": command,
            "detections": clean_dets,
            "log_message": log_message,
            "sub": sub,
            "demo": demo
        }

        try:
            res = self.session.post(self.state_url, json=payload, timeout=0.25)
            if res.status_code == 200:
                if not self.is_connected:
                    print(f"[BRIDGE] Connected to dashboard server at {self.state_url}")
                    self.is_connected = True
                return True
        except requests.exceptions.RequestException as e:
            self._handle_network_error("State send failed", e)
            return False

        return False

    def send_frame(self, frame: np.ndarray) -> bool:
        """
        Encodes frame to JPEG and sends to POST /api/frame for MJPEG streaming.
        Rate-limited to FRAME_STREAM_FPS_LIMIT to preserve CPU/network.
        """
        if frame is None:
            return False

        now = time.time()
        if now - self._last_frame_post_time < self._min_frame_interval:
            return False

        self._last_frame_post_time = now

        try:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), FRAME_JPEG_QUALITY]
            success, encoded_img = cv2.imencode('.jpg', frame, encode_param)
            if not success:
                return False

            jpeg_bytes = encoded_img.tobytes()
            headers = {"Content-Type": "image/jpeg"}
            res = self.session.post(self.frame_url, data=jpeg_bytes, headers=headers, timeout=0.25)
            return res.status_code == 200
        except requests.exceptions.RequestException:
            # Frame drop is normal if server is busy or shutting down
            return False

    def _handle_network_error(self, context: str, error: Exception):
        now = time.time()
        if self.is_connected:
            print(f"[BRIDGE] Disconnected from dashboard ({context}). Waiting for reconnect...")
            self.is_connected = False
            self._last_error_log_time = now
        elif (now - self._last_error_log_time) > 10.0:
            print(f"[BRIDGE] Dashboard at {self.state_url} not reachable yet ({error.__class__.__name__}). Retrying in background...")
            self._last_error_log_time = now
