import json
import os
import pandas as pd
from collections import defaultdict

# ---------------------------
# File paths
# ---------------------------
WEEKLY_EXCEL_FILE = "weekly_assignments.xlsx"  # source of truth
CHECKPOINT_FILE = "checkpoint.json"
ACTIVES_FILE = "actives.xlsx"
CONFIG_FILE = "cleanup_config.json"

# ---------------------------
# Sanity check
# ---------------------------
if not os.path.exists(WEEKLY_EXCEL_FILE):
    raise RuntimeError(f"❌ {WEEKLY_EXCEL_FILE} not found. Cannot rebuild.")

# ---------------------------
# Load config
# ---------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

cleanup_types = config["cleanup_types"]

# ---------------------------
# Load weekly assignments
# ---------------------------
weekly_df = pd.read_excel(WEEKLY_EXCEL_FILE)

# Validate columns
if "week" not in weekly_df.columns:
    raise RuntimeError("❌ weekly_assignments.xlsx must have a 'week' column")

person_columns = [c for c in weekly_df.columns if c != "week"]

# ---------------------------
# Load actives.xlsx to preserve all original columns
# ---------------------------
df = pd.read_excel(ACTIVES_FILE)
names_in_df = df["name"].tolist()

# ---------------------------
# Initialize assigned_so_far and last_cleanup
# ---------------------------
assigned_so_far = {name: defaultdict(int) for name in names_in_df}
last_cleanup = {name: None for name in names_in_df}
weekly_history = {}

# ---------------------------
# Process each week in order
# ---------------------------
for _, row in weekly_df.sort_values("week").iterrows():
    week = int(row["week"])
    weekly_assignments = {}
    for person in person_columns:
        cleanup = row[person]
        if pd.notna(cleanup):
            cleanup = str(cleanup)
            assigned_so_far[person][cleanup] += 1
            last_cleanup[person] = cleanup
            weekly_assignments[person] = cleanup
    weekly_history[str(week)] = weekly_assignments

current_week = weekly_df["week"].max()

# ---------------------------
# Save checkpoint.json
# ---------------------------
checkpoint = {
    "current_week": int(current_week),
    "assigned_so_far": {p: dict(assigned_so_far[p]) for p in assigned_so_far},
    "last_cleanup": last_cleanup,
    "weekly_history": weekly_history,
    "round_robin_index": int(current_week)
}

with open(CHECKPOINT_FILE, "w") as f:
    json.dump(checkpoint, f, indent=4)

print(f"✅ checkpoint.json rebuilt from {WEEKLY_EXCEL_FILE} with round-robin info")

# ---------------------------
# Rebuild actives.xlsx WITHOUT dropping existing columns
# ---------------------------
# Ensure all cleanup columns exist
for c in cleanup_types:
    if c not in df.columns:
        df[c] = 0

# Fill counts from assigned_so_far
for idx, row in df.iterrows():
    name = row["name"]
    if name in assigned_so_far:
        for c in cleanup_types:
            df.at[idx, c] = assigned_so_far[name].get(c, 0)

df.to_excel(ACTIVES_FILE, index=False)
print(f"✅ {ACTIVES_FILE} rebuilt with cumulative counts (all original columns preserved)")
