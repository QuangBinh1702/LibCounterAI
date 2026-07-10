from unittest.mock import patch
from tracker import IoUTracker

def test_iou_perfect_overlap():
    t = IoUTracker()
    box = [0, 0, 10, 10]
    assert t._iou(box, box) == 1.0

def test_iou_no_overlap():
    t = IoUTracker()
    assert t._iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0

def test_iou_half_overlap():
    t = IoUTracker()
    box1 = [0, 0, 10, 10]
    box2 = [5, 0, 15, 10]
    iou = t._iou(box1, box2)
    assert 0.33 < iou < 0.34

def test_iou_edge_touch():
    t = IoUTracker()
    assert t._iou([0, 0, 10, 10], [10, 0, 20, 10]) == 0.0

def test_iou_contained():
    t = IoUTracker()
    box1 = [0, 0, 20, 20]
    box2 = [5, 5, 15, 15]
    iou = t._iou(box1, box2)
    assert iou == 0.25

def test_iou_zero_area():
    t = IoUTracker()
    assert t._iou([0, 0, 0, 0], [0, 0, 10, 10]) == 0.0

def test_iou_negative_coords():
    t = IoUTracker()
    iou = t._iou([-10, -10, 0, 0], [-5, -5, 5, 5])
    assert iou > 0

def test_tracking_point_default():
    t = IoUTracker()
    pt = t._tracking_point([10, 20, 30, 40])
    assert pt == (20.0, 40.0)

def test_tracking_point_no_line():
    t = IoUTracker()
    pt = t._tracking_point([10, 20, 30, 40], None)
    assert pt == (20.0, 40.0)

def test_tracking_point_with_horizontal_line():
    t = IoUTracker()
    pt = t._tracking_point([10, 20, 30, 40], [[0, 30], [40, 30]])
    assert pt == (20.0, 40.0)

def test_tracking_point_with_vertical_line():
    t = IoUTracker()
    pt = t._tracking_point([10, 20, 30, 40], [[20, 0], [20, 50]])
    assert pt == (20.0, 30.0)

def test_predict_bbox_no_velocity():
    t = IoUTracker()
    predicted = t._predict_bbox([10, 20, 30, 40], [0, 0, 0, 0])
    assert predicted == [10.0, 20.0, 30.0, 40.0]

def test_predict_bbox_with_velocity():
    t = IoUTracker()
    predicted = t._predict_bbox([10, 20, 30, 40], [2, 3, 2, 3])
    assert predicted == [12.0, 23.0, 32.0, 43.0]

def test_smooth_velocity_initial():
    t = IoUTracker()
    prev_bbox = [0, 0, 10, 10]
    curr_bbox = [2, 2, 12, 12]
    prev_vel = [0, 0, 0, 0]
    smoothed = t._smooth_velocity(prev_bbox, curr_bbox, prev_vel)
    expected = [0.35 * 0 + 0.65 * 2] * 4
    assert smoothed == expected

def test_smooth_velocity_with_history():
    t = IoUTracker()
    prev_bbox = [0, 0, 10, 10]
    curr_bbox = [2, 2, 12, 12]
    prev_vel = [1, 1, 1, 1]
    smoothed = t._smooth_velocity(prev_bbox, curr_bbox, prev_vel)
    expected = [0.35 * 1 + 0.65 * 2] * 4
    assert smoothed == expected

def test_update_new_tracks():
    t = IoUTracker()
    dets = [[10, 10, 50, 50, 0.9], [70, 70, 120, 120, 0.8]]
    tracks, events = t.update(dets)
    assert len(tracks) == 2
    assert len(events) == 0
    assert tracks[0]["track_id"] == 1
    assert tracks[1]["track_id"] == 2
    assert t.next_id == 3

def test_update_empty_detections():
    t = IoUTracker(max_lost=0)
    dets = [[10, 10, 50, 50, 0.9]]
    tracks, _ = t.update(dets)
    assert len(tracks) == 1
    tracks, _ = t.update([])
    assert len(tracks) == 0

def test_update_track_reacquire():
    t = IoUTracker(max_lost=5)
    dets = [[10, 10, 50, 50, 0.9]]
    t.update(dets)
    tracks, _ = t.update(dets)
    assert len(tracks) == 1
    assert tracks[0]["track_id"] == 1

def test_update_track_lost_then_reacquire():
    t = IoUTracker(max_lost=5)
    t.update([[10, 10, 50, 50, 0.9]])
    t.update([])
    t.update([])
    tracks, _ = t.update([[10, 10, 50, 50, 0.9]])
    assert len(tracks) == 1
    assert tracks[0]["track_id"] == 1

def test_update_cleanup_deleted_tracks():
    t = IoUTracker(max_lost=1)
    t.update([[10, 10, 50, 50, 0.9]])
    t.update([])
    t.update([])
    t.update([])
    assert len(t.tracks) == 0

def test_update_track_predicted_flag():
    t = IoUTracker(max_lost=2)
    t.update([[10, 10, 50, 50, 0.9]])
    tracks, _ = t.update([])
    assert tracks[0]["predicted"] == True

def test_update_track_confidence_decay():
    t = IoUTracker(max_lost=2)
    t.update([[10, 10, 50, 50, 0.9]])
    tracks, _ = t.update([])
    assert tracks[0]["confidence"] == 0.9 * 0.9

def test_update_multiple_detections_match():
    t = IoUTracker()
    dets1 = [[10, 10, 50, 50, 0.9], [70, 70, 120, 120, 0.8]]
    tracks1, _ = t.update(dets1)
    id1 = tracks1[0]["track_id"]
    id2 = tracks1[1]["track_id"]
    assert id1 == 1
    assert id2 == 2

    dets2 = [[12, 12, 52, 52, 0.95], [72, 72, 122, 122, 0.85]]
    tracks2, _ = t.update(dets2)
    assert len(tracks2) == 2
    track_ids = [tr["track_id"] for tr in tracks2]
    assert id1 in track_ids
    assert id2 in track_ids

def test_update_trajectory_maintained():
    t = IoUTracker()
    t.update([[10, 10, 50, 50, 0.9]])
    assert 1 in t.trajectories
    assert len(t.trajectories[1]) == 1

    t.update([[12, 12, 52, 52, 0.9]])
    assert len(t.trajectories[1]) == 2

def test_update_trajectory_truncated():
    t = IoUTracker()
    for _ in range(10):
        t.update([[10, 10, 50, 50, 0.9]])
    assert len(t.trajectories[1]) <= 5

def _make_crossing_tracker():
    return IoUTracker(debounce_seconds=10, iou_threshold=0.01)

def test_update_crossing_event():
    t = _make_crossing_tracker()
    line = [[0, 30], [40, 30]]
    dets = [[10, 10, 50, 28, 0.9]]
    t.update(dets, line)
    dets = [[10, 25, 50, 55, 0.9]]
    tracks, events = t.update(dets, line)
    assert len(events) == 1
    assert events[0]["direction"] == "ENTRY"
    assert events[0]["track_id"] == 1

def test_update_crossing_exit():
    t = _make_crossing_tracker()
    line = [[0, 30], [40, 30]]
    dets = [[10, 25, 50, 55, 0.9]]
    t.update(dets, line)
    dets = [[10, 10, 50, 28, 0.9]]
    tracks, events = t.update(dets, line)
    assert len(events) == 1
    assert events[0]["direction"] == "EXIT"

def test_update_crossing_debounce():
    t = _make_crossing_tracker()
    t.debounce_seconds = 5
    line = [[0, 30], [40, 30]]
    dets = [[10, 10, 50, 28, 0.9]]
    t.update(dets, line)
    dets = [[10, 25, 50, 55, 0.9]]
    with patch("time.time") as mock_time:
        mock_time.side_effect = [100.0, 100.5]
        tracks, events = t.update(dets, line)
    assert len(events) == 1
    assert events[0]["direction"] == "ENTRY"

    dets = [[12, 28, 52, 58, 0.9]]
    with patch("time.time") as mock_time:
        mock_time.side_effect = [101.0, 101.5]
        tracks, events2 = t.update(dets, line)
    assert len(events2) == 0

def test_update_crossing_no_debounce_after_timeout():
    t = _make_crossing_tracker()
    t.debounce_seconds = 1
    line = [[0, 30], [40, 30]]
    dets = [[10, 10, 50, 28, 0.9]]
    t.update(dets, line)
    dets = [[10, 25, 50, 55, 0.9]]
    with patch("time.time") as mock_time:
        mock_time.side_effect = [100.0, 100.5]
        t.update(dets, line)
    dets = [[10, 18, 50, 28, 0.9]]
    with patch("time.time") as mock_time:
        mock_time.side_effect = [102.0, 102.5]
        tracks, events = t.update(dets, line)
    assert len(events) == 1
    assert events[0]["direction"] == "EXIT"

def test_update_identity_attached():
    t = IoUTracker()
    t.update([[10, 10, 50, 50, 0.9]])
    t.identities[1] = {"person_id": 42, "person_name": "Alice", "identity_type": "KNOWN"}
    tracks, _ = t.update([[12, 12, 52, 52, 0.9]])
    assert tracks[0]["person_id"] == 42
    assert tracks[0]["person_name"] == "Alice"

def test_update_identity_cleaned_on_track_loss():
    t = IoUTracker(max_lost=1)
    t.update([[10, 10, 50, 50, 0.9]])
    t.identities[1] = {"person_id": 42, "person_name": "Alice", "identity_type": "KNOWN"}
    t.last_crossing[1] = {"timestamp": 100.0, "direction": "ENTRY"}
    t.trajectories[1] = [(20, 40)]
    t.update([])
    t.update([])
    assert 1 not in t.identities
    assert 1 not in t.last_crossing
    assert 1 not in t.trajectories

def test_update_detections_is_none():
    t = IoUTracker()
    tracks, events = t.update(None)
    assert tracks == []
    assert events == []
