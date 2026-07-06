import numpy as np
import time
from geometry import get_crossing_direction

class IoUTracker:
    def __init__(self, max_lost=15, iou_threshold=0.3):
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.tracks = {} # track_id -> {"bbox": bbox, "lost": 0, "confidence": conf}
        self.trajectories = {} # track_id -> list of (x, y) bottom-center points
        self.identities = {} # track_id -> {"person_id": int, "person_name": str, "identity_type": str}

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

    def update(self, detections, line_config=None):
        # detections: list of [x1, y1, x2, y2, conf]
        # line_config: list of two points, e.g. [[x1, y1], [x2, y2]]
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
                updated_tracks[track_id] = {
                    "bbox": detections[best_det_idx][:4],
                    "confidence": detections[best_det_idx][4],
                    "lost": 0
                }
            else:
                # Keep lost track temporarily
                lost_count = track_data.get("lost", 0) + 1
                if lost_count <= self.max_lost:
                    updated_tracks[track_id] = {
                        "bbox": track_data["bbox"],
                        "confidence": track_data.get("confidence", 0.0),
                        "lost": lost_count
                    }
        
        # 2. Start new tracks for unmatched detections
        for idx, det in enumerate(detections):
            if idx not in matched_detections:
                updated_tracks[self.next_id] = {
                    "bbox": det[:4],
                    "confidence": det[4],
                    "lost": 0
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
        
        # 4. Update trajectories and detect crossing events
        active_tracks = []
        for track_id, data in self.tracks.items():
            if data["lost"] == 0:
                bbox = data["bbox"]
                # Bottom center point
                bc_x = (bbox[0] + bbox[2]) / 2.0
                bc_y = bbox[3]
                current_point = (bc_x, bc_y)
                
                # Check for crossing if history exists and line_config is provided
                if track_id in self.trajectories and line_config is not None:
                    prev_point = self.trajectories[track_id][-1]
                    direction = get_crossing_direction(
                        line_config[0], line_config[1], prev_point, current_point
                    )
                    if direction != 0:
                        crossing_events.append({
                            "track_id": track_id,
                            "direction": "ENTRY" if direction == 1 else "EXIT",
                            "timestamp": time.time()
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
                    "confidence": float(data["confidence"])
                }
                if track_id in self.identities:
                    track_info.update(self.identities[track_id])
                active_tracks.append(track_info)
                
        return active_tracks, crossing_events

