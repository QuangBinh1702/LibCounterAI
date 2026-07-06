def ccw(A, B, C):
    """
    Check if points A, B, C are in counter-clockwise order.
    """
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def intersects(A, B, C, D):
    """
    Check if line segment AB and segment CD intersect.
    A, B represent the virtual line segment.
    C, D represent the trajectory of a person (from previous position C to current position D).
    """
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

def get_crossing_direction(line_start, line_end, traj_start, traj_end):
    """
    Determine the crossing direction across the directed virtual line.
    Returns:
        1: Crossing from right-to-left (standard ENTRY if configured)
       -1: Crossing from left-to-right (standard EXIT if configured)
        0: No crossing or on the line
    """
    if not intersects(line_start, line_end, traj_start, traj_end):
        return 0
        
    # Vector of the virtual line: AB
    ab_x = line_end[0] - line_start[0]
    ab_y = line_end[1] - line_start[1]
    
    # Vector of the trajectory: CD
    cd_x = traj_end[0] - traj_start[0]
    cd_y = traj_end[1] - traj_start[1]
    
    # Cross product of AB and CD to determine sign of crossing direction
    # positive cross product means crossing right-to-left, negative means left-to-right
    cross_product = ab_x * cd_y - ab_y * cd_x
    
    if cross_product > 0:
        return 1
    elif cross_product < 0:
        return -1
    return 0
