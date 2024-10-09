from csv import reader
import random
from datetime import datetime, timezone, timedelta
from src.detection import detectmain

# Parameters
log_files = ["/Users/gracehunter/psu/decoupled/results/logs/activity-log_1000actions_files4folders2_2024-10-08T05:04:24Z-2024-10-08T05:52:30Z.csv"]
data_filename = "results/expr2/test2.csv"
selectivity_levels = [0, 0.05, .20, 1]
level_names = ["high", "medium", "low"]
activity_counts = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
num_constraints = 10

# BEGIN Experiment 2
# Action space generation constants
ALL_ACTIONS = ["Create", "Delete", "Edit", "Move", "Permission Change"]
PERMISSION_CHANGE_ACTION_TYPES = ["Add Permission", "Update Permission", "Remove Permission"]
INITIAL_PERMISSION_LEVELS = {
    "Add Permission": "none",
    "Remove Permission": "writer",
    "Update Permission": "writer",
}
FINAL_PERMISSION_LEVELS = {
    "Add Permission": "writer",
    "Remove Permission": "none",
    "Update Permission": "can_view/can_comment",
}

# Action Constraint (AC) generation constraints
CONSTRAINT_TYPES = [("Can Create", "Create"),
                    ("Can Move", "Move"),
                    ("Can Delete", "Delete"),
                    ("Can Edit", "Edit"),
                    ("Add Permission", "Permission Change"),
                    ("Remove Permission", "Permission Change"),
                    ("Update Permission", "Permission Change")]
PERMISSION_OPERATORS = ["not in", "in"]


def increase_selectivity(ac, users, resources):
    """Add one elemnent to an attribute that supports grouping"""
    resource_names, resource_ids, action, action_type, actors, listlike, operator, owner, targets = ac
    group_index_choices = [0, 4]
    if ac[2] == "Permission Change":
        group_index_choices.append(8)
    chosen_group_index = random.choice(group_index_choices)
    if chosen_group_index == 8:
        if ac[6] == "not in":
            if len(ac[8]) > 0:
                targets = ac[8][1:]
        elif ac[6] == "in":
            if len(ac[8]) < len(users):
                new_user = random.choice(users)
                while new_user in ac[8]:
                    new_user = random.choice(users)
                targets = (*targets, new_user)
    elif chosen_group_index == 0:
        if len(ac[1]) < len(resources):
            new_resource = random.choice(resources)
            while new_resource[1] in ac[1]:
                new_resource = random.choice(resources)
            resource_names = (*resource_names, new_resource[0])
            resource_ids = (*resource_ids, new_resource[1])
    elif chosen_group_index == 4:
        if len(ac[4]) < len(users):
            new_user = random.choice(users)
            while new_user in ac[4]:
                new_user = random.choice(users)
            actors = (*actors, new_user)
    return (resource_names, resource_ids, action, action_type, actors, listlike, operator, owner, targets)

def decrease_selectivity(ac, users, resources):
    """Remove one elemnent from an attribute that supports grouping"""
    resource_names, resource_ids, action, action_type, actors, listlike, operator, owner, targets = ac
    group_index_choices = [0, 4]
    if ac[2] == "Permission Change":
        group_index_choices.append(8)
    chosen_group_index = random.choice(group_index_choices)
    if chosen_group_index == 8:
        if ac[6] == "not in":
            if len(ac[8]) < len(users):
                new_user = random.choice(users)
                while new_user in ac[8]:
                    new_user = random.choice(users)
                targets = (*targets, new_user)
        elif ac[6] == "in":
            if len(ac[8]) > 0:
                targets = ac[8][1:]
    elif chosen_group_index == 0:
        if len(ac[1]) > 0:
            resource_names = resource_names[1:]
            resource_ids = resource_ids[1:]
    elif chosen_group_index == 4:
        if len(ac[4]) > 0:
            actors = actors[1:]
    return (resource_names, resource_ids, action, action_type, actors, listlike, operator, owner, targets)

def actions_selected_by_ac(constraints, activities):
    """Return the number of actions that this AC selects, using the detection algorithm"""
    parsed_constraints = []
    for (resource_names, resource_ids, action, action_type, actors, deprecated, operator, owner, targets) in constraints:
        parsed_constraints.append([
                list(resource_names),
                list(resource_ids),
                action,
                action_type,
                list(actors),
                deprecated,
                operator,
                owner,
                list(targets)
        ])
    conflicts = detectmain(activities, parsed_constraints)
    return sum(conflicts)

random.seed()

data_file = open(data_filename, "w+")
data_file.write("log_file,activity_count,selectivity_level,selectivity,detection_time\n")

for log_file in log_files:

    with open(log_file, "r") as csv_file:
        logs = list(reader(csv_file))[1:] # Skip header row

    for activity_count in activity_counts:
        logs_subset = logs[:activity_count]
        # Determine action space from logs
        all_resources = set()
        users = set()
        for log in logs_subset[1:]:
            all_resources.add((log[3], log[2]))
            users.add(log[5])
        all_resources = list(all_resources)
        users = list(users)
        space_size = len(users) * len(all_resources) * (4 + 3 * len(users))
        all_activities = []
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for user in users:
            for resource in all_resources:
                for action in ALL_ACTIONS:
                    if action == "Permission Change":
                        for action_type in PERMISSION_CHANGE_ACTION_TYPES:
                            initial_permission = INITIAL_PERMISSION_LEVELS[action_type]
                            final_permission = FINAL_PERMISSION_LEVELS[action_type]
                            for target in users:
                                action_attr = action + "-to:" + final_permission + "-from:" + initial_permission + "-for:" + target
                                activity = [timestamp, action_attr, resource[1], resource[0], "0", user]
                                all_activities.append(activity)
                    elif action == "Move":
                        action_attr = action + ":FolderS:FolderD"
                        activity = [timestamp, action_attr, resource[1], resource[0], "0", user]
                        all_activities.append(activity)
                    else:
                        activity = [timestamp, action, resource[1], resource[0], "0", user]
                        all_activities.append(activity)
        print(all_activities)
        print(len(all_resources), users, len(all_activities))
        assert len(all_activities) == space_size

        for i in range(1, len(selectivity_levels)):
            regenerate = True
            while regenerate:
                # Randomly generate action constraints from action space with no grouping
                constraints = set()
                while len(constraints) < num_constraints:
                    owner = random.choice(users)
                    resource = random.choice(all_resources)
                    resource_names = (resource[0], )
                    resource_ids = (resource[1], )
                    actors = (random.choice(users), )
                    action_type, action = random.choice(CONSTRAINT_TYPES)
                    operator, targets = None, ()
                    if action == "Permission Change":
                        operator = random.choice(PERMISSION_OPERATORS)
                        if operator == "in":
                            targets = (random.choice(users), )
                        elif operator == "not in":
                            targets = tuple(random.sample(users, k=(len(users) - 1)))

                    ac = ((resource_names), resource_ids, action, action_type, actors, '', operator, owner, targets)
                    constraints.add(ac)
                constraints_list = list(constraints)

                # Randomly increase grouping until selectivity threshold is hit
                range_floor = selectivity_levels[i - 1]
                range_ceil = selectivity_levels[i]
                range_name = level_names[i - 1]
                delta_per_constraint = 1 / space_size
                selectivity = actions_selected_by_ac(constraints, all_activities) / space_size
                print(range_name, range_floor, range_ceil)
                attempts = 0
                while (selectivity < range_floor or selectivity > range_ceil) and attempts < 100:
                    attempts += 1
                    if selectivity < range_floor:
                        print("increasing", selectivity)
                        for _ in range(int((range_floor - selectivity) / delta_per_constraint)):
                            ac_index = random.randint(0, len(constraints_list) - 1)
                            ac = constraints_list[ac_index]
                            constraints.remove(ac)
                            ac = increase_selectivity(ac, users, all_resources)
                            constraints.add(ac)
                            constraints_list[ac_index] = ac
                    else:
                        print("decreasing", selectivity)
                        for _ in range(int((range_ceil - selectivity) / delta_per_constraint)):
                            ac_index = random.randint(0, len(constraints_list) - 1)
                            ac = constraints_list[ac_index]
                            constraints.remove(ac)
                            ac = decrease_selectivity(ac, users, all_resources)
                            constraints.add(ac)
                            constraints_list[ac_index] = ac
                    selectivity = actions_selected_by_ac(constraints, all_activities) / space_size
                if attempts < 100:
                    regenerate = False

            # Time detection algorithm
            print("detecting")
            parsed_constraints = []
            for (resource_names, resource_ids, action, action_type, actors, deprecated, operator, owner, targets) in constraints:
                parsed_constraints.append([
                    list(resource_names),
                    list(resource_ids),
                    action,
                    action_type,
                    list(actors),
                    deprecated,
                    operator,
                    owner,
                    list(targets)
                ])

            t0 = datetime.now()
            result = detectmain(logs_subset, parsed_constraints)
            t1 = datetime.now()

            detection_time = t1 - t0
            detection_time_ms = detection_time.seconds * 1000 + (detection_time.microseconds / 1000) # Ignore "days" property
            data_line = ",".join([log_file, str(activity_count), range_name, str(selectivity), str(detection_time_ms)])
            data_file.write(data_line + "\n")
            print("done")