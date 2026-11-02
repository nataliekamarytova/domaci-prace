from datetime import datetime
URGENT_PRIORITY = 1
PRIORITY_BONUS = 1.2
LATE_PENALTY_RATIO = 0.10 #každý uběhnutý den strhne body o 10%
LATE_PENALTY_URGENT_RATIO = 0.2
MIN_POINTS_RATIO = 0.25

def get_points(base_points,task_deadline,task_completed_at,task_priority):
    if (task_deadline is None) or task_completed_at <= task_deadline:
        received_points = base_points
        if task_priority == URGENT_PRIORITY:
            received_points = round(received_points*PRIORITY_BONUS) #bonus za vcasne splneni prioritne oznaceneho ukolu
    else:
        days_late = (task_completed_at - task_deadline).days
        if task_priority == URGENT_PRIORITY:
            penalty = LATE_PENALTY_URGENT_RATIO
        else:
            penalty = LATE_PENALTY_RATIO

        received_points = round((1 - days_late*penalty)*base_points)
        if received_points < MIN_POINTS_RATIO*base_points:
            received_points = round(MIN_POINTS_RATIO*base_points)
    return(received_points)


if __name__ == "__main__":
    deadline = datetime(2026, 11, 2, 18, 0)

    print(get_points(20, deadline, datetime(2026, 11, 2, 15, 0),2 ))   # včas → 20b
    print(get_points(20, deadline, datetime(2026, 11, 2, 15, 0),1 ))   # včas s vysokou prioritou → 24b
    print(get_points(20, deadline, datetime(2026, 11, 3, 6, 0),2 ))    # 12 h pozdě → 20b
    print(get_points(20, deadline, datetime(2026, 11, 3, 20, 0),2 ))    # 26 h pozdě → 18b
    print(get_points(20, deadline, datetime(2026, 11, 6, 15, 0),2 ))    # 3 dny pozdě → 14b
    print(get_points(20, deadline, datetime(2026, 11, 12, 18, 0),2 ))    # 10 dní pozdě → 5b
    print(get_points(20, None, datetime(2026, 11, 12, 15, 0),2 ))    # bez termínu → 20b
    print(get_points(20, deadline, datetime(2026, 11, 3, 20, 0),1 ))    # 26 h pozdě s vysokou prioritou→ 16b



