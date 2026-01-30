import json
import os
import pandas as pd
from collections import defaultdict

CHECKPOINT_FILE = "checkpoint.json"
EXCEL_FILE = "actives.xlsx"
WEEKLY_EXCEL_FILE = "weekly_assignments.xlsx"

# ---------------------------
# Sanity checks
# ---------------------------
if not os.path.exists(CHECKPOINT_FILE):
    raise RuntimeError("❌ checkpoint.json not found. No weeks to rollback.")

with open(CHECKPOINT_FILE, "r") as f:
    checkpoint = json.load(f)

current_week = checkpoint.get("current_week", 0)
weekly_history = checkpoint.get("weekly_history", {})

if current_week == 0 or not weekly_history:
    raise RuntimeError("❌ No scheduled weeks found to rollback.")

# ---------------------------
# Identify week to rollback
# ---------------------------
week_to_delete = str(current_week)
if week_to_delete not in weekly_history:
    raise RuntimeError(f"❌ Inconsistent checkpoint: week {week_to_delete} not found.")

week_assignments = weekly_history[week_to_delete]

# ---------------------------
# Roll back assigned_so_far
# ---------------------------
assigned_so_far = {
    name: defaultdict(int, data)
    for name, data in checkpoint["assigned_so_far"].items()
}

for person, cleanup in week_assignments.items():
    if cleanup is not None:
        assigned_so_far[person][cleanup] -= 1
        if assigned_so_far[person][cleanup] <= 0:
            del assigned_so_far[person][cleanup]

# ---------------------------
# Delete the week from history
# ---------------------------
del checkpoint["weekly_history"][week_to_delete]
checkpoint["current_week"] -= 1

# Roll back round-robin index
if "round_robin_index" in checkpoint and checkpoint["round_robin_index"] > 0:
    checkpoint["round_robin_index"] -= 1

# ---------------------------
# Recompute last_cleanup from remaining weeks
# ---------------------------
last_cleanup = {name: None for name in assigned_so_far}
if checkpoint["weekly_history"]:
    sorted_weeks = sorted(int(w) for w in checkpoint["weekly_history"].keys())
    for person in last_cleanup:
        # iterate backwards to find the last cleanup this person did
        for wk in reversed(sorted_weeks):
            wk_assignments = checkpoint["weekly_history"][str(wk)]
            if person in wk_assignments:
                last_cleanup[person] = wk_assignments[person]
                break

# ---------------------------
# Update checkpoint
# ---------------------------
checkpoint["assigned_so_far"] = {
    name: dict(assigned_so_far[name]) for name in assigned_so_far
}
checkpoint["last_cleanup"] = last_cleanup

with open(CHECKPOINT_FILE, "w") as f:
    json.dump(checkpoint, f, indent=4)

print(f"🧹 Rolled back week {week_to_delete} successfully.")

# ---------------------------
# Update weekly_assignments.xlsx
# ---------------------------
if os.path.exists(WEEKLY_EXCEL_FILE):
    weekly_df = pd.read_excel(WEEKLY_EXCEL_FILE)
    weekly_df = weekly_df[weekly_df["week"] != int(week_to_delete)]
    weekly_df.to_excel(WEEKLY_EXCEL_FILE, index=False)
    print(f"📘 Removed week {week_to_delete} from {WEEKLY_EXCEL_FILE}")

# ---------------------------
# Update actives.xlsx properly
# ---------------------------
df = pd.read_excel(EXCEL_FILE)

# Ensure all cleanup columns exist in the Excel
cleanup_columns = set()
for counts in assigned_so_far.values():
    cleanup_columns.update(counts.keys())

for col in cleanup_columns:
    if col not in df.columns:
        df[col] = 0

# Update counts in place
for idx, row in df.iterrows():
    name = row["name"]
    if name in assigned_so_far:
        for c in cleanup_columns:
            df.at[idx, c] = assigned_so_far[name].get(c, 0)

df.to_excel(EXCEL_FILE, index=False)
print(f"📘 Updated {EXCEL_FILE} with rolled-back counts")
