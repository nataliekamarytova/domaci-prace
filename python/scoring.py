from datetime import datetime
LATE_PENALTY_RATIO = 0.10 #každý uběhnutý den strhne body o 10%
MIN_POINTS_RATIO = 0.25

def get_points(base_points,task_deadline,task_completed_at):
    if (task_deadline is None) or task_completed_at <= task_deadline:
        received_points = base_points
    else:
        days_late = (task_completed_at - task_deadline).days
        received_points = round((1 - days_late*LATE_PENALTY_RATIO)*base_points)
        if received_points < MIN_POINTS_RATIO*base_points:
            received_points = round(MIN_POINTS_RATIO*base_points)
    return(received_points)


if __name__ == "__main__":
    deadline = datetime(2026, 11, 2, 18, 0)

    print(get_points(20, deadline, datetime(2026, 11, 2, 15, 0)))   # včas → 20b
    print(get_points(20, deadline, datetime(2026, 11, 3, 6, 0)))    # 12 h pozdě → 20b
    print(get_points(20, deadline, datetime(2026, 11, 3, 20, 0)))    # 26 h pozdě → 18b
    print(get_points(20, deadline, datetime(2026, 11, 6, 15, 0)))    # 3 dny pozdě → 14b
    print(get_points(20, deadline, datetime(2026, 11, 12, 15, 0)))    # 10 dní pozdě → 5b
    print(get_points(20, None, datetime(2026, 11, 12, 15, 0)))    # bez termínu → 20b



