from geometry import ccw, intersects, get_crossing_direction

def test_ccw_positive():
    assert ccw((0, 0), (4, 0), (2, 2)) == True

def test_ccw_negative():
    assert ccw((0, 0), (4, 0), (2, -2)) == False

def test_ccw_collinear():
    assert ccw((0, 0), (2, 2), (4, 4)) == False

def test_intersects_cross():
    assert intersects((0, 1), (4, 1), (2, 0), (2, 2)) == True

def test_intersects_parallel():
    assert intersects((0, 0), (4, 0), (0, 2), (4, 2)) == False

def test_intersects_no_touch():
    assert intersects((0, 0), (2, 2), (3, 3), (5, 5)) == False

def test_intersects_vertical_horizontal():
    assert intersects((2, 0), (2, 4), (0, 2), (4, 2)) == True

def test_crossing_direction_none():
    assert get_crossing_direction((0, 1), (4, 1), (2, 0), (6, 0)) == 0

def test_crossing_direction_right_to_left():
    line_start = (0, 1)
    line_end = (4, 1)
    traj_start = (2, 0)
    traj_end = (2, 2)
    result = get_crossing_direction(line_start, line_end, traj_start, traj_end)
    assert result == 1

def test_crossing_direction_left_to_right():
    line_start = (0, 1)
    line_end = (4, 1)
    traj_start = (2, 2)
    traj_end = (2, 0)
    result = get_crossing_direction(line_start, line_end, traj_start, traj_end)
    assert result == -1

def test_crossing_direction_diagonal():
    line_start = (0, 0)
    line_end = (4, 4)
    traj_start = (0, 1)
    traj_end = (1, 0)
    result = get_crossing_direction(line_start, line_end, traj_start, traj_end)
    assert result != 0

def test_crossing_direction_reverse_line():
    line_start = (4, 1)
    line_end = (0, 1)
    traj_start = (2, 0)
    traj_end = (2, 2)
    result = get_crossing_direction(line_start, line_end, traj_start, traj_end)
    assert result == -1

def test_crossing_horizontal_line():
    line_start = (0, 2)
    line_end = (4, 2)
    assert get_crossing_direction(line_start, line_end, (1, 1), (1, 3)) == 1
    assert get_crossing_direction(line_start, line_end, (1, 3), (1, 1)) == -1

def test_crossing_vertical_line():
    line_start = (2, 0)
    line_end = (2, 4)
    assert get_crossing_direction(line_start, line_end, (1, 2), (3, 2)) == -1
    assert get_crossing_direction(line_start, line_end, (3, 2), (1, 2)) == 1
