"""
Navigation Decision Engine Module:
Translates spatial detections into safety-first assistive navigation commands.
Implements temporal stability (frame confirmation), debouncing, and explainable decision logs.
"""

import time
from typing import List, Dict, Any, Tuple
from python.config import (
    COMMAND_CONFIRMATION_FRAMES,
    COMMAND_COOLDOWN_SECONDS,
    OBJECT_DETECTED_COOLDOWN_SECONDS,
    PROXIMITY_STOP_AREA,
    PROXIMITY_SLOW_AREA
)


class NavigationEngine:
    """
    Evaluates detected obstacles and outputs directional assistive guidance.
    Enforces temporal stability to prevent command flickering.
    """

    def __init__(
        self,
        confirmation_frames=COMMAND_CONFIRMATION_FRAMES,
        cooldown_seconds=COMMAND_COOLDOWN_SECONDS
    ):
        self.confirmation_frames = confirmation_frames
        self.cooldown_seconds = cooldown_seconds

        # State tracking
        self.current_confirmed_command = "system_ready"
        self.candidate_command = "system_ready"
        self.candidate_frame_count = 0

        # Cooldown timestamps
        self.last_command_time = {}
        self.last_object_detected_time = 0.0
        self.had_objects_last_frame = False

        # State history for contextual transitions (e.g. stop -> start_walking)
        self.was_stopped = False

    def decide(self, detections: List[Dict[str, Any]]) -> Tuple[str, str, str, bool]:
        """
        Processes list of enriched detections.

        Returns:
            command (str): One of the supported navigation commands.
            log_message (str): Human-readable reason for the decision.
            sub_message (str): Subtitle hint for the dashboard.
            is_new_command (bool): True if the confirmed command changed on this frame.
        """
        now = time.time()
        has_objects = len(detections) > 0

        # Initial raw proposal based on instant visual scene
        raw_cmd, raw_log, raw_sub = self._evaluate_scene(detections)

        # Check for first-time object appearance event
        if has_objects and not self.had_objects_last_frame:
            if (now - self.last_object_detected_time) > OBJECT_DETECTED_COOLDOWN_SECONDS:
                self.last_object_detected_time = now
                # Provide immediate warning if desired, or proceed to directional guidance
        self.had_objects_last_frame = has_objects

        # ============================================================
        # TEMPORAL STABILITY: Confirm candidate across consecutive frames
        # ============================================================
        if raw_cmd == self.candidate_command:
            self.candidate_frame_count += 1
        else:
            self.candidate_command = raw_cmd
            self.candidate_frame_count = 1

        is_new_command = False

        # Emergency STOP overrides immediately if high collision proximity
        is_emergency = (raw_cmd == "stop" and any(d.get("area", 0) >= PROXIMITY_STOP_AREA for d in detections if d.get("position") == "center"))

        if self.candidate_frame_count >= self.confirmation_frames or is_emergency:
            if self.candidate_command != self.current_confirmed_command:
                self.current_confirmed_command = self.candidate_command
                is_new_command = True
                self.last_command_time[self.current_confirmed_command] = now

        # Update was_stopped flag
        if self.current_confirmed_command in ("stop", "wait_for_a_while"):
            self.was_stopped = True
        elif self.current_confirmed_command in ("move_straight", "move_left", "move_right"):
            self.was_stopped = False

        return self.current_confirmed_command, raw_log, raw_sub, is_new_command

    def _evaluate_scene(self, detections: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """
        Core rule-based assistive logic.
        Safety-first priority:
        1. Clear Scene -> move_straight (or start_walking if resuming from stop)
        2. Center obstacle -> STOP or SLOW DOWN based on visual proximity
        3. Left obstacle -> move_right
        4. Right obstacle -> move_left
        5. Complex / blocked -> conservative stop or wait
        """
        if not detections:
            if self.was_stopped:
                return "start_walking", "Path is now clear — Resume walking", "Path is clear"
            return "move_straight", "Path ahead is clear — Move straight", "Path ahead is clear"

        # Separate detections by zone
        center_objs = [d for d in detections if d.get("position", "center") == "center"]
        left_objs = [d for d in detections if d.get("position", "center") == "left"]
        right_objs = [d for d in detections if d.get("position", "center") == "right"]

        # Sort within each zone by visual relevance:
        # Priority: 1. Area (closeness/size) 2. Confidence
        def sort_key(d):
            return (d.get("area", 0), d.get("confidence", 0))

        center_objs.sort(key=sort_key, reverse=True)
        left_objs.sort(key=sort_key, reverse=True)
        right_objs.sort(key=sort_key, reverse=True)

        # ------------------------------------------------------------
        # RULE 1: CENTER OBSTACLE (Direct collision risk)
        # ------------------------------------------------------------
        if center_objs:
            primary = center_objs[0]
            obj_name = primary["object"].capitalize()
            area = primary.get("area", 0)
            conf = primary.get("confidence", 0)

            # High visual proximity or high confidence center obstacle -> STOP
            if area >= PROXIMITY_STOP_AREA or area >= 0.12 or conf >= 0.70:
                return "stop", f"{obj_name} detected in center — Stop", "Obstacle very close in center path"

            # Moderate visual proximity -> SLOW DOWN caution
            if area >= PROXIMITY_SLOW_AREA:
                return "slow_down", f"{obj_name} ahead in center — Slow down", "Object ahead in direct path"

            # Low area / distant center obstacle -> STOP or SLOW DOWN (Safety-first default)
            return "stop", f"{obj_name} detected in center path — Stop", "Center path obstructed"

        # ------------------------------------------------------------
        # RULE 2: OBSTACLE ON LEFT ONLY
        # ------------------------------------------------------------
        if left_objs and not right_objs:
            primary = left_objs[0]
            obj_name = primary["object"].capitalize()
            return "move_right", f"{obj_name} on left — Move right", "Path is clear on the right"

        # ------------------------------------------------------------
        # RULE 3: OBSTACLE ON RIGHT ONLY
        # ------------------------------------------------------------
        if right_objs and not left_objs:
            primary = right_objs[0]
            obj_name = primary["object"].capitalize()
            return "move_left", f"{obj_name} on right — Move left", "Path is clear on the left"

        # ------------------------------------------------------------
        # RULE 4: OBSTACLES ON BOTH LEFT AND RIGHT (Narrow corridor)
        # ------------------------------------------------------------
        if left_objs and right_objs:
            left_primary = left_objs[0]
            right_primary = right_objs[0]
            left_area = left_primary.get("area", 0)
            right_area = right_primary.get("area", 0)

            # If both sides are heavily constricted -> caution
            if left_area > 0.15 and right_area > 0.15:
                return "wait_for_a_while", "Both sides obstructed — Wait for a while", "Waiting for narrow path to clear"

            # Steer toward the side with significantly smaller obstacle
            if left_area > right_area * 1.5:
                return "move_right", f"Larger obstacle on left — Veer right", "Steer away from left obstacle"
            elif right_area > left_area * 1.5:
                return "move_left", f"Larger obstacle on right — Veer left", "Steer away from right obstacle"
            else:
                return "slow_down", "Narrow corridor detected — Slow down", "Maintain center with caution"

        # ------------------------------------------------------------
        # RULE 5: FALLBACK (Conservative safety)
        # ------------------------------------------------------------
        return "move_straight", "Path ahead is clear — Move straight", "Path ahead is clear"
