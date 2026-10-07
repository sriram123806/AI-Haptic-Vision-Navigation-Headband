"""
Position Analyzer Module:
Calculates horizontal position (LEFT, CENTER, RIGHT) and visual proximity metrics
for detected objects based on normalized bounding box coordinates.
"""

from typing import List, Dict, Any
from python.config import LEFT_THRESHOLD, RIGHT_THRESHOLD


class PositionAnalyzer:
    """Classifies detected objects into horizontal zones and calculates spatial metrics."""

    def __init__(self, left_thresh=LEFT_THRESHOLD, right_thresh=RIGHT_THRESHOLD):
        self.left_thresh = left_thresh
        self.right_thresh = right_thresh

    def analyze(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes raw detections and assigns position ('left', 'center', 'right'),
        computes center_x, center_y, and visual area metrics.

        Returns list of enriched detection dictionaries.
        """
        enriched = []
        for det in detections:
            box = det.get("box", [0, 0, 0, 0])
            x1, y1, x2, y2 = box

            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            width = max(0.0, x2 - x1)
            height = max(0.0, y2 - y1)
            area = round(width * height, 4)

            # Horizontal zone classification
            if center_x < self.left_thresh:
                position = "left"
            elif center_x > self.right_thresh:
                position = "right"
            else:
                position = "center"

            item = {
                "object": det.get("object", "object"),
                "confidence": det.get("confidence", 0.0),
                "position": position,
                "box": box,
                "center_x": round(center_x, 3),
                "center_y": round(center_y, 3),
                "area": area,
                "height": round(height, 3)
            }
            enriched.append(item)

        return enriched

    def get_zone_summary(self, detections: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Groups detections by zone: 'left', 'center', 'right'.
        """
        summary = {"left": [], "center": [], "right": []}
        for d in detections:
            pos = d.get("position", "center")
            if pos in summary:
                summary[pos].append(d)
        return summary
