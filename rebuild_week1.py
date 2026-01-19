import json
import pandas as pd
from collections import defaultdict

CHECKPOINT_FILE = "checkpoint.json"
EXCEL_FILE = "actives.xlsx"
CONFIG_FILE = "cleanup_config.json"

# ---------------------------
# Load config
# ---------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

cleanup_types = config["cleanup_types"]

# ---------------------------
# Load actives.xlsx (source of truth)
# ---------------------------
df = pd.read_excel(EXCEL_FILE)

if "name" not in df.columns:
    raise RuntimeError("❌ actives.xlsx must contain a 'name' column")

missing_cols = [c for c in cleanup_types if c not in df.columns]
if missing_cols:
    raise RuntimeError(f"❌ Missing cleanup columns in actives.xlsx: {missing_cols}")

# ---------------------------
# Load existing checkpoint
# ---------------------------
with open(CHECKPOINT_FILE, "r") as f:
    checkpoint = json.load(f)

weekly_history = checkpoint.get("weekly_history", {})

if list(weekly_history.keys()) != ["1"]:
    raise RuntimeError(
        "❌ This repair script only works when EXACTLY one week exists"
    )

# ---------------------------
# Rebuild assigned_so_far from actives.xlsx
# ---------------------------
assigned_so_far = {}

for _, row in df.iterrows():
    name = row["name"]
    counts = defaultdict(int)
    for c in cleanup_types:
        val = row[c]
        if pd.notna(val):
            counts[c] = int(val)
    assigned_so_far[name] = dict(counts)

# ---------------------------
# Rebuild weekly_history for week 1
# ---------------------------
# For each person, figure out the last cleanup they did in week 1
# We assume only one cleanup per person per week
week1_assignments = {}

for _, row in df.iterrows():
    name = row["name"]
    for c in cleanup_types:
        if int(row[c]) > 0:
            week1_assignments[name] = c
            break  # assume only one per person per week

weekly_history = {"1": week1_assignments}

# ---------------------------
# Rebuild last_cleanup from week1
# ---------------------------
last_cleanup = dict(week1_assignments)  # same as assignments

# ---------------------------
# Assemble clean checkpoint
# ---------------------------
new_checkpoint = {
    "current_week": 1,
    "assigned_so_far": assigned_so_far,
    "last_cleanup": last_cleanup,
    "weekly_history": weekly_history
}

# ---------------------------
# Save checkpoint
# ---------------------------
with open(CHECKPOINT_FILE, "w") as f:
    json.dump(new_checkpoint, f, indent=4)

print("✅ checkpoint.json fully rebuilt from actives.xlsx + week 1")
print("⚠️ This script should NEVER be run again.")
