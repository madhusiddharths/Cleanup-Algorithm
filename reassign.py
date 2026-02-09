import json
import pandas as pd
from collections import defaultdict
import os

# ---------------------------
# Inputs
# ---------------------------
PERSON = input("Person name: ").strip()
WEEK = int(input("Week number: ").strip())
NEW_CLEANUP = input("New cleanup: ").strip()

ACTIVES_FILE = "actives.xlsx"
WEEKLY_FILE = "weekly_assignments.xlsx"
CHECKPOINT_FILE = "checkpoint.json"

# ---------------------------
# Load weekly_assignments.xlsx
# ---------------------------
weekly_df = pd.read_excel(WEEKLY_FILE)

if "week" not in weekly_df.columns:
    raise RuntimeError("❌ weekly_assignments.xlsx missing 'week' column")

if PERSON not in weekly_df.columns:
    raise RuntimeError(f"❌ {PERSON} not found in weekly_assignments.xlsx")

row_idx = weekly_df.index[weekly_df["week"] == WEEK]
if len(row_idx) == 0:
    raise RuntimeError(f"❌ Week {WEEK} not found")

row_idx = row_idx[0]
OLD_CLEANUP = weekly_df.at[row_idx, PERSON]

if pd.isna(OLD_CLEANUP):
    raise RuntimeError(f"❌ {PERSON} had no assignment in week {WEEK}")

if OLD_CLEANUP == NEW_CLEANUP:
    raise RuntimeError("❌ Old and new cleanup are the same")

# Apply change
weekly_df.at[row_idx, PERSON] = NEW_CLEANUP
weekly_df.to_excel(WEEKLY_FILE, index=False)

print(f"📘 weekly_assignments.xlsx updated: {PERSON} {OLD_CLEANUP} → {NEW_CLEANUP}")

# ---------------------------
# Load checkpoint.json
# ---------------------------
with open(CHECKPOINT_FILE, "r") as f:
    checkpoint = json.load(f)

weekly_history = checkpoint["weekly_history"]

if str(WEEK) not in weekly_history:
    raise RuntimeError(f"❌ Week {WEEK} missing in checkpoint")

weekly_history[str(WEEK)][PERSON] = NEW_CLEANUP

# ---------------------------
# Recompute assigned_so_far from history
# ---------------------------
assigned_so_far = defaultdict(lambda: defaultdict(int))
last_cleanup = defaultdict(lambda: None)

weeks_sorted = sorted(weekly_history.keys(), key=int)

for wk in weeks_sorted:
    for person, cleanup in weekly_history[wk].items():
        assigned_so_far[person][cleanup] += 1
        last_cleanup[person] = cleanup

checkpoint["assigned_so_far"] = {
    p: dict(c) for p, c in assigned_so_far.items()
}
checkpoint["last_cleanup"] = dict(last_cleanup)

with open(CHECKPOINT_FILE, "w") as f:
    json.dump(checkpoint, f, indent=4)

print("🧠 checkpoint.json updated")

# ---------------------------
# Update actives.xlsx
# ---------------------------
df = pd.read_excel(ACTIVES_FILE)

if PERSON not in df["name"].values:
    raise RuntimeError(f"❌ {PERSON} not found in actives.xlsx")

# Ensure columns exist
for c in [OLD_CLEANUP, NEW_CLEANUP]:
    if c not in df.columns:
        df[c] = 0

idx = df.index[df["name"] == PERSON][0]
df.at[idx, OLD_CLEANUP] -= 1
df.at[idx, NEW_CLEANUP] += 1

df.to_excel(ACTIVES_FILE, index=False)

print("📊 actives.xlsx updated")

print(f"\n✅ Reassignment complete: {PERSON}, week {WEEK}")
