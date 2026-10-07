"""
YOLOv8 Object Detector Module:
Runs real-time inference using the lightweight pretrained YOLOv8n model,
filters by confidence threshold, normalizes bounding box coordinates,
and draws clear HUD annotations on the frame.
"""

import os
import cv2
import numpy as np
from ultralytics import YOLO
from python.config import (
    YOLO_MODEL,
    CONFIDENCE_THRESHOLD,
    LEFT_THRESHOLD,
    RIGHT_THRESHOLD
)

# Colors for bounding boxes and UI overlay (BGR format)
COLOR_LEFT = (235, 99, 37)      # Blueish-cyan
COLOR_CENTER = (34, 197, 94)    # Green
COLOR_RIGHT = (68, 68, 239)     # Red
COLOR_LINE = (180, 180, 180)    # Soft gray for zone dividers


class ObjectDetector:
    """Manages the YOLOv8 model inference and frame annotation."""

    def __init__(self, model_name=YOLO_MODEL, conf_threshold=CONFIDENCE_THRESHOLD):
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        self.model = None
        self.is_ready = False

    def load_model(self) -> bool:
        """Loads the pretrained YOLOv8 model from local storage or downloads it."""
        print(f"[YOLO] Loading pretrained model '{self.model_name}'...")
        try:
            self.model = YOLO(self.model_name)
            self.is_ready = True
            print(f"[YOLO] Pretrained model '{self.model_name}' ready. Confidence threshold: {self.conf_threshold:.2f}")
            return True
        except Exception as e:
            print(f"[YOLO ERROR] Failed to load model '{self.model_name}': {e}")
            self.is_ready = False
            return False

    def detect(self, frame: np.ndarray):
        """
        Runs YOLOv8 object detection on a BGR OpenCV frame.

        Returns:
            detections (list of dicts):
                [
                    {
                        "object": str (e.g. "person"),
                        "confidence": float (0.0 - 1.0),
                        "box": [x1_norm, y1_norm, x2_norm, y2_norm],
                        "box_pixels": [x1, y1, x2, y2],
                        "area": float (normalized area 0.0 - 1.0)
                    }, ...
                ]
            annotated_frame: np.ndarray with bounding boxes, labels, and zone markers.
        """
        if not self.is_ready or self.model is None or frame is None:
            return [], frame

        h, w = frame.shape[:2]
        annotated_frame = frame.copy()

        # Draw subtle vertical zone lines (Left 0..33%, Center 33..66%, Right 66..100%)
        lx = int(w * LEFT_THRESHOLD)
        rx = int(w * RIGHT_THRESHOLD)
        cv2.line(annotated_frame, (lx, 0), (lx, h), COLOR_LINE, 1, cv2.LINE_AA)
        cv2.line(annotated_frame, (rx, 0), (rx, h), COLOR_LINE, 1, cv2.LINE_AA)

        # Label the zones at the top
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(annotated_frame, "LEFT", (lx // 2 - 25, 24), font, 0.55, COLOR_LINE, 1, cv2.LINE_AA)
        cv2.putText(annotated_frame, "CENTER", ((lx + rx) // 2 - 35, 24), font, 0.55, COLOR_LINE, 1, cv2.LINE_AA)
        cv2.putText(annotated_frame, "RIGHT", ((rx + w) // 2 - 25, 24), font, 0.55, COLOR_LINE, 1, cv2.LINE_AA)

        # Run YOLO inference
        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            verbose=False
        )

        detections = []
        if not results or len(results) == 0:
            return detections, annotated_frame

        result = results[0]
        boxes = result.boxes

        if boxes is None or len(boxes) == 0:
            return detections, annotated_frame

        for box in boxes:
            conf = float(box.conf[0].item())
            if conf < self.conf_threshold:
                continue

            cls_id = int(box.cls[0].item())
            class_name = self.model.names.get(cls_id, f"obj_{cls_id}").lower()

            # Coordinates in pixels
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = xyxy

            # Normalize to 0.0 - 1.0 clamped
            x1_norm = max(0.0, min(1.0, x1 / w))
            y1_norm = max(0.0, min(1.0, y1 / h))
            x2_norm = max(0.0, min(1.0, x2 / w))
            y2_norm = max(0.0, min(1.0, y2 / h))

            norm_w = max(0.0, x2_norm - x1_norm)
            norm_h = max(0.0, y2_norm - y1_norm)
            area = round(norm_w * norm_h, 4)

            detection_entry = {
                "object": class_name,
                "confidence": round(conf, 2),
                "box": [round(x1_norm, 3), round(y1_norm, 3), round(x2_norm, 3), round(y2_norm, 3)],
                "box_pixels": [int(x1), int(y1), int(x2), int(y2)],
                "area": area
            }
            detections.append(detection_entry)

            # Draw visual bounding box on the frame
            px1, py1, px2, py2 = int(x1), int(y1), int(x2), int(y2)
            center_x = (x1_norm + x2_norm) / 2.0
            if center_x < LEFT_THRESHOLD:
                box_color = COLOR_LEFT
            elif center_x > RIGHT_THRESHOLD:
                box_color = COLOR_RIGHT
            else:
                box_color = COLOR_CENTER

            cv2.rectangle(annotated_frame, (px1, py1), (px2, py2), box_color, 2)

            # Label text with background tag
            label_text = f"{class_name.capitalize()} {int(conf * 100)}%"
            (txt_w, txt_h), baseline = cv2.getTextSize(label_text, font, 0.5, 1)
            tag_y1 = max(0, py1 - txt_h - 6)
            tag_y2 = py1
            tag_x2 = min(w, px1 + txt_w + 8)

            cv2.rectangle(annotated_frame, (px1, tag_y1), (tag_x2, tag_y2), box_color, -1)
            cv2.putText(annotated_frame, label_text, (px1 + 4, tag_y2 - 4), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return detections, annotated_frame
