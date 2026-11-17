from datetime import datetime
URGENT_PRIORITY = 1
PRIORITY_BONUS = 1.2
MIN_POINTS_RATIO = 0.25

def get_points(base_points,task_deadline,task_completed_at,task_priority,task_hard_deadline):
    if (task_deadline is None) or task_completed_at <= task_deadline:
        received_points = base_points
        if task_priority == URGENT_PRIORITY:
            received_points = round(received_points*PRIORITY_BONUS) #bonus za vcasne splneni prioritne oznaceneho ukolu
    else: #spocitame pomer bodu, klesaji linearne po uplynuti deadlinu do hard_deadlinu do 25% - minima bodu 
        points = base_points*(1-MIN_POINTS_RATIO)
        deadline_difference = (task_completed_at - task_deadline).total_seconds()/(task_hard_deadline-task_deadline).total_seconds() #aby se nam pomer bodu spocital presneji, dny by nestacily
        received_points= round(base_points - deadline_difference*points)
        if received_points < MIN_POINTS_RATIO*base_points:
            received_points = round(MIN_POINTS_RATIO*base_points)
    return(received_points)

if __name__ == "__main__":
    deadline = datetime(2026, 11, 2, 18, 0)
    hard_deadline = datetime(2026, 11, 5, 18, 0)  # deadline + 3 dny

    print(get_points(20, deadline, datetime(2026, 11, 2, 15, 0), 2, hard_deadline))   # včas → 20b
    print(get_points(20, deadline, datetime(2026, 11, 2, 15, 0), 1, hard_deadline))   # včas s vysokou prioritou → 24b
    print(get_points(20, deadline, datetime(2026, 11, 3, 6, 0), 2, hard_deadline))    # 12 h pozdě → 18b
    print(get_points(20, deadline, datetime(2026, 11, 3, 20, 0), 2, hard_deadline))   # 26 h pozdě → 15b
    print(get_points(20, deadline, datetime(2026, 11, 6, 15, 0), 2, hard_deadline))   # těsně přes hard_deadline → 5b (floor)
    print(get_points(20, deadline, datetime(2026, 11, 12, 18, 0), 2, hard_deadline))  # 10 dní pozdě → 5b (floor)
    print(get_points(20, None, datetime(2026, 11, 12, 15, 0), 2, hard_deadline))      # bez termínu → 20b
    print(get_points(20, deadline, datetime(2026, 11, 3, 20, 0), 1, hard_deadline))   # 26 h pozdě, naléhavý → 15b (stejně jako běžná priorita, protože jsme se rozhodli nerozlišovat)
   


