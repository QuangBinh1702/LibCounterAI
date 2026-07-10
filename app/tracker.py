import numpy as np
import time
from geometry import get_crossing_direction

class IoUTracker:
    def __init__(self, max_lost=5, iou_threshold=0.2, debounce_seconds=2.0):
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self.debounce_seconds = debounce_seconds
        self.next_id = 1
        self.tracks = {} # track_id -> {"bbox": bbox, "velocity": [dx1, dy1, dx2, dy2], "lost": 0, "confidence": conf}
        self.trajectories = {} # track_id -> list of (x, y) bottom-center points
        self.identities = {} # track_id -> {"person_id": int, "person_name": str, "identity_type": str}
        self.last_crossing = {} # track_id -> {"timestamp": float, "direction": str}

    def _iou(self, box1, box2):
        # box format: [x1, y1, x2, y2]
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection
        if union <= 0:
            return 0.0
        return intersection / union

    def _tracking_point(self, bbox, line_config=None):
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        if line_config is not None:
            line_dx = line_config[1][0] - line_config[0][0]
            line_dy = line_config[1][1] - line_config[0][1]
            if abs(line_dy) > abs(line_dx):
                return (center_x, center_y)
        return (center_x, y2)

    def _predict_bbox(self, bbox, velocity):
        return [float(bbox[idx]) + float(velocity[idx]) for idx in range(4)]

    def _smooth_velocity(self, previous_bbox, current_bbox, previous_velocity):
        delta = [float(current_bbox[idx]) - float(previous_bbox[idx]) for idx in range(4)]
        return [
            (0.35 * float(previous_velocity[idx])) + (0.65 * delta[idx])
            for idx in range(4)
        ]

    def update(self, detections, line_config=None):
        # detections: list of [x1, y1, x2, y2, conf]
        # line_config: list of two points, e.g. [[x1, y1], [x2, y2]]
        detections = detections or []
        updated_tracks = {}
        matched_detections = set()
        crossing_events = []
        
        # 1. Try to match with existing tracks
        for track_id, track_data in self.tracks.items():
            best_iou = -1
            best_det_idx = -1
            for idx, det in enumerate(detections):
                if idx in matched_detections:
                    continue
                iou = self._iou(track_data["bbox"], det[:4])
                if iou > best_iou:
                    best_iou = iou
                    best_det_idx = idx
            
            if best_iou >= self.iou_threshold:
                # Update existing track
                matched_detections.add(best_det_idx)
                current_bbox = detections[best_det_idx][:4]
                previous_velocity = track_data.get("velocity", [0.0, 0.0, 0.0, 0.0])
                updated_tracks[track_id] = {
                    "bbox": current_bbox,
                    "velocity": self._smooth_velocity(track_data["bbox"], current_bbox, previous_velocity),
                    "confidence": detections[best_det_idx][4],
                    "lost": 0,
                    "predicted": False,
                }
            else:
                # Keep the overlay responsive while the detector is skipped or misses a frame.
                lost_count = track_data.get("lost", 0) + 1
                if lost_count <= self.max_lost:
                    velocity = track_data.get("velocity", [0.0, 0.0, 0.0, 0.0])
                    updated_tracks[track_id] = {
                        "bbox": self._predict_bbox(track_data["bbox"], velocity),
                        "velocity": velocity,
                        "confidence": track_data.get("confidence", 0.0) * 0.9,
                        "lost": lost_count,
                        "predicted": True,
                    }
        
        # 2. Start new tracks for unmatched detections
        for idx, det in enumerate(detections):
            if idx not in matched_detections:
                updated_tracks[self.next_id] = {
                    "bbox": det[:4],
                    "velocity": [0.0, 0.0, 0.0, 0.0],
                    "confidence": det[4],
                    "lost": 0,
                    "predicted": False,
                }
                self.next_id += 1
                
        self.tracks = updated_tracks
        
        # 3. Clean up trajectories and identities of deleted tracks
        active_track_ids = set(self.tracks.keys())
        for track_id in list(self.trajectories.keys()):
            if track_id not in active_track_ids:
                del self.trajectories[track_id]
        for track_id in list(self.identities.keys()):
            if track_id not in active_track_ids:
                del self.identities[track_id]
        for track_id in list(self.last_crossing.keys()):
            if track_id not in active_track_ids:
                del self.last_crossing[track_id]
        
        # 4. Update trajectories and detect crossing events
        active_tracks = []
        for track_id, data in self.tracks.items():
            if data["lost"] <= self.max_lost:
                bbox = data["bbox"]
                current_point = self._tracking_point(bbox, line_config)
                
                # Check for crossing if history exists and line_config is provided
                if track_id in self.trajectories and line_config is not None:
                    prev_point = self.trajectories[track_id][-1]
                    direction = get_crossing_direction(
                        line_config[0], line_config[1], prev_point, current_point
                    )
                    if direction != 0:
                        now = time.time()
                        direction_label = "ENTRY" if direction == 1 else "EXIT"
                        last_crossing = self.last_crossing.get(track_id)
                        is_duplicate = (
                            last_crossing is not None
                            and last_crossing["direction"] == direction_label
                            and now - last_crossing["timestamp"] < self.debounce_seconds
                        )
                        if not is_duplicate:
                            self.last_crossing[track_id] = {
                                "timestamp": now,
                                "direction": direction_label,
                            }
                            crossing_events.append({
                                "track_id": track_id,
                                "direction": direction_label,
                                "timestamp": now
                            })
                
                # Update trajectory history
                if track_id not in self.trajectories:
                    self.trajectories[track_id] = []
                self.trajectories[track_id].append(current_point)
                # Keep history size small
                if len(self.trajectories[track_id]) > 5:
                    self.trajectories[track_id].pop(0)
                
                track_info = {
                    "track_id": track_id,
                    "bbox": [float(x) for x in bbox],
                    "confidence": float(data["confidence"]),
                    "lost": int(data.get("lost", 0)),
                    "predicted": bool(data.get("predicted", False)),
                }
                if track_id in self.identities:
                    track_info.update(self.identities[track_id])
                active_tracks.append(track_info)
                
        return active_tracks, crossing_events
