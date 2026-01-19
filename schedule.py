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
for _, row in df.iterrows():
    name = row["name"]

    # Normalize inhouse (handles 2, 2.0, "2")
    try:
        inhouse = str(int(row["inhouse"]))
    except (ValueError, TypeError):
        inhouse = "1"  # safe default (out-of-house)

    if inhouse not in base_by_inhouse:
        raise ValueError(f"Invalid inhouse value for {name}: {row['inhouse']}")

    base_by_person[name] = base_by_inhouse[inhouse]

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
        "weekly_history": {}
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
weekly_assignments = schedule_one_week_final(
    current_week,
    df,
    cleanup_types,
    per_week_actual,
    base_by_person,
    assigned_so_far,
    last_cleanup,
    num_weeks
)

print(f"\n📆 Week {current_week} assignments:")
for person, cleanup in weekly_assignments.items():
    print(f"{person}: {cleanup}")

# ---------------------------
# Update checkpoint
# ---------------------------
checkpoint["current_week"] = current_week
checkpoint["assigned_so_far"] = {
    name: dict(assigned_so_far[name]) for name in names
}
checkpoint["last_cleanup"] = last_cleanup
checkpoint["weekly_history"][str(current_week)] = weekly_assignments

with open(CHECKPOINT_FILE, "w") as f:
    json.dump(checkpoint, f, indent=4)

# ---------------------------
# Save updated actives.xlsx
# ---------------------------
df.to_excel(EXCEL_FILE, index=False)
print(f"✅ Week {current_week} scheduled and saved.")
print("📘 actives.xlsx updated with latest counts")

# ---------------------------
# Save pivoted weekly assignments Excel
# ---------------------------
# Build pivoted DataFrame: week × person
all_weeks = []
for wk, assignments in checkpoint["weekly_history"].items():
    row = {"week": int(wk)}
    row.update(assignments)  # person: cleanup
    all_weeks.append(row)

weekly_df = pd.DataFrame(all_weeks)
# Sort by week
weekly_df = weekly_df.sort_values("week").reset_index(drop=True)

# Save Excel
weekly_df.to_excel(WEEKLY_EXCEL_FILE, index=False)
print(f"✅ Weekly assignments saved to {WEEKLY_EXCEL_FILE}")
