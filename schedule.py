import json
import os
import pandas as pd
from collections import defaultdict
from cleanup import schedule_one_week_final

EXCEL_FILE = "actives.xlsx"
CONFIG_FILE = "cleanup_config.json"
CHECKPOINT_FILE = "checkpoint.json"
WEEKLY_EXCEL_FILE = "weekly_assignments.xlsx"  # pivoted output

# ---------------------------
# Load static inputs
# ---------------------------
df = pd.read_excel(EXCEL_FILE)
names = df["name"].tolist()

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

cleanup_types = config["cleanup_types"]
num_weeks = config["num_weeks"]
per_week_actual = config["per_week_actual"]
base_by_inhouse = config["base_by_inhouse"]

# ---------------------------
# Build per-person base (ONE-TIME mapping)
# ---------------------------
base_by_person = {}
out_house_people = []
for _, row in df.iterrows():
    name = row["name"]

    # Read inhouse strictly and normalize
    try:
        inhouse_int = int(float(row["inhouse"]))
    except ValueError:
        raise ValueError(f"Invalid inhouse value for {name}: {row['inhouse']}")

    inhouse = str(inhouse_int).strip()
    if inhouse not in {"0", "1", "2", "3"}:
        raise ValueError(f"Invalid inhouse value for {name}: {row['inhouse']}")

    if inhouse in {"2", "3"}:
        base_by_person[name] = base_by_inhouse[inhouse]
    else:
        base_by_person[name] = {}  # out-of-house follow round-robin
        out_house_people.append(name)

# ---------------------------
# Load or initialize checkpoint
# ---------------------------
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r") as f:
        checkpoint = json.load(f)
else:
    checkpoint = {
        "current_week": 0,
        "assigned_so_far": {},
        "last_cleanup": {},
        "weekly_history": {},
        "round_robin_index": 0  # track out-of-house rotation
    }

current_week = checkpoint["current_week"] + 1

if current_week > num_weeks:
    raise RuntimeError("All weeks have already been scheduled.")

assigned_so_far = {
    name: defaultdict(int, checkpoint["assigned_so_far"].get(name, {}))
    for name in names
}

last_cleanup = {
    name: checkpoint["last_cleanup"].get(name)
    for name in names
}

# Ensure all allowed cleanup keys exist per person
for name in names:
    for c in base_by_person[name]:
        assigned_so_far[name][c] += 0

# ---------------------------
# Run ONE week (ALL logic inside cleanup.py)
# ---------------------------
weekly_assignments, round_robin_index = schedule_one_week_final(
    current_week,
    df,
    cleanup_types,
    per_week_actual,
    base_by_person,
    assigned_so_far,
    last_cleanup,
    num_weeks,
    out_house_people,
    checkpoint.get("round_robin_index", 0)
)

# ---------------------------
# Update checkpoint
# ---------------------------
checkpoint["round_robin_index"] = round_robin_index
checkpoint["current_week"] = current_week
checkpoint["assigned_so_far"] = {name: dict(assigned_so_far[name]) for name in names}
checkpoint["last_cleanup"] = last_cleanup
checkpoint["weekly_history"][str(current_week)] = weekly_assignments

with open(CHECKPOINT_FILE, "w") as f:
    json.dump(checkpoint, f, indent=4)

# ---------------------------
# Update actives.xlsx
# ---------------------------
df.to_excel(EXCEL_FILE, index=False)
print(f"✅ Week {current_week} scheduled and saved.")
print("📘 actives.xlsx updated with latest counts")

# ---------------------------
# Save pivoted weekly assignments Excel
# ---------------------------
all_weeks = []
for wk, assignments in checkpoint["weekly_history"].items():
    row = {"week": int(wk)}
    row.update(assignments)
    all_weeks.append(row)

weekly_df = pd.DataFrame(all_weeks)
weekly_df = weekly_df.sort_values("week").reset_index(drop=True)
weekly_df.to_excel(WEEKLY_EXCEL_FILE, index=False)
print(f"✅ Weekly assignments saved to {WEEKLY_EXCEL_FILE}")
