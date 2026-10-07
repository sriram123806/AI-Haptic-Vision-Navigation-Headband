"""
Camera Capture Module:
Handles laptop webcam initialization, frame retrieval, error handling, and resource cleanup.
"""

import time
import cv2
from python.config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT


class Camera:
    """Manages the laptop webcam capture lifecycle with robust error handling."""

    def __init__(self, camera_index=CAMERA_INDEX, width=FRAME_WIDTH, height=FRAME_HEIGHT):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None
        self.is_connected = False
        self._fps_tracker = 0
        self._frame_count = 0
        self._last_fps_time = time.time()
        self.current_fps = 0.0

    def open(self) -> bool:
        """
        Attempts to open the webcam. Tries DirectShow on Windows first for fast startup,
        then falls back to default backend.
        """
        print(f"[CAMERA] Opening laptop webcam (device index {self.camera_index})...")

        # Try opening with DirectShow backend (optimized for Windows)
        try:
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(self.camera_index)
        except Exception as e:
            print(f"[CAMERA] Notice: DirectShow fallback triggered ({e}). Using default backend.")
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap or not self.cap.isOpened():
            print(f"[CAMERA ERROR] Could not open webcam at index {self.camera_index}.")
            print("                Check if another application is using the camera or if permissions are required.")
            self.is_connected = False
            return False

        # Configure frame dimensions
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.is_connected = True
        print(f"[CAMERA] Laptop webcam active: {actual_w}x{actual_h} resolution.")
        return True

    def read(self):
        """
        Reads a single frame from the camera.
        Returns (success: bool, frame: np.ndarray or None).
        Handles empty frames, disconnects, and computes running FPS.
        """
        if not self.cap or not self.cap.isOpened():
            return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None or frame.size == 0:
            print("[CAMERA WARNING] Received empty or invalid frame from webcam.")
            return False, None

        # Track FPS
        self._frame_count += 1
        now = time.time()
        elapsed = now - self._last_fps_time
        if elapsed >= 1.0:
            self.current_fps = round(self._frame_count / elapsed, 1)
            self._frame_count = 0
            self._last_fps_time = now

        return True, frame

    def release(self):
        """Releases the webcam hardware cleanly."""
        if self.cap:
            try:
                self.cap.release()
                print("[CAMERA] Webcam released cleanly.")
            except Exception as e:
                print(f"[CAMERA] Error while releasing webcam: {e}")
            finally:
                self.cap = None
                self.is_connected = False

    def is_opened(self) -> bool:
        """Returns True if the webcam is currently open and valid."""
        return self.cap is not None and self.cap.isOpened()
