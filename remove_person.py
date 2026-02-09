import sys
import json
import os
import shutil
import math
from datetime import datetime
import pandas as pd
from collections import defaultdict

# ---------------------------
# Arguments
# ---------------------------
if len(sys.argv) != 2:
    raise RuntimeError("Usage: python remove_person.py 'Person Name'")

PERSON = sys.argv[1]

# ---------------------------
# Files
# ---------------------------
WEEKLY_FILE = "weekly_assignments.xlsx"
ACTIVES_FILE = "actives.xlsx"
CHECKPOINT_FILE = "checkpoint.json"
CONFIG_FILE = "cleanup_config.json"

# ---------------------------
# Backup
# ---------------------------
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = f"backup_remove_{PERSON}_{ts}"
os.makedirs(backup_dir, exist_ok=True)

for f in [WEEKLY_FILE, ACTIVES_FILE, CHECKPOINT_FILE, CONFIG_FILE]:
    if os.path.exists(f):
        shutil.copy(f, os.path.join(backup_dir, f))

print(f"✅ Backup created: {backup_dir}")

# ---------------------------
# 1️⃣ Update weekly_assignments.xlsx
# ---------------------------
weekly_df = pd.read_excel(WEEKLY_FILE)

if PERSON not in weekly_df.columns:
    raise RuntimeError(f"❌ {PERSON} not found in weekly_assignments.xlsx")

weekly_df = weekly_df.drop(columns=[PERSON])
weekly_df.to_excel(WEEKLY_FILE, index=False)

print(f"✅ Removed {PERSON} from weekly_assignments.xlsx")

# ---------------------------
# 2️⃣ Rebuild checkpoint.json
# ---------------------------
person_columns = [c for c in weekly_df.columns if c != "week"]

assigned_so_far = {p: defaultdict(int) for p in person_columns}
last_cleanup = {p: None for p in person_columns}
weekly_history = {}

for _, row in weekly_df.sort_values("week").iterrows():
    week = int(row["week"])
    w_assign = {}
    for p in person_columns:
        if pd.notna(row[p]):
            c = str(row[p])
            assigned_so_far[p][c] += 1
            last_cleanup[p] = c
            w_assign[p] = c
    weekly_history[str(week)] = w_assign

checkpoint = {
    "current_week": int(weekly_df["week"].max()),
    "assigned_so_far": {p: dict(assigned_so_far[p]) for p in assigned_so_far},
    "last_cleanup": last_cleanup,
    "weekly_history": weekly_history
}

with open(CHECKPOINT_FILE, "w") as f:
    json.dump(checkpoint, f, indent=4)

print("✅ checkpoint.json rebuilt")

# ---------------------------
# 3️⃣ Update actives.xlsx
# ---------------------------
df = pd.read_excel(ACTIVES_FILE)

df = df[df["name"] != PERSON].reset_index(drop=True)

cleanup_cols = [c for c in df.columns if c not in ["name", "inhouse"]]

for idx, row in df.iterrows():
    name = row["name"]
    for c in cleanup_cols:
        df.at[idx, c] = assigned_so_far.get(name, {}).get(c, 0)

df.to_excel(ACTIVES_FILE, index=False)
print("✅ actives.xlsx updated")

# ---------------------------
# 4️⃣ Recompute cleanup_config.json
# ---------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

cleanup_types = config["cleanup_types"]
min_per_week = config["min_per_week"]

# only inhouse 2 & 3 count
inhouse_df = df[df["inhouse"].isin([2, 3])]
inhouse_count = len(inhouse_df)

extra = inhouse_count - sum(min_per_week.values())
per_week_actual = min_per_week.copy()

order = list(min_per_week.keys())
i = 0
while extra > 0:
    c = order[i % len(order)]

    if c == "bathroom_2":
        if extra >= 2:
            per_week_actual["bathroom_2"] += 1
            per_week_actual["bathroom_3"] += 1
            extra -= 2
    elif c == "deck_brush":
        if extra >= 2:
            per_week_actual["deck_brush"] += 2
            extra -= 2
    else:
        per_week_actual[c] += 1
        extra -= 1

    i += 1

# global base
num_weeks = config["num_weeks"]
exact = {k: (v * num_weeks) / inhouse_count for k, v in per_week_actual.items()}
global_base = {k: int(exact[k]) for k in exact}

missing = inhouse_count - sum(global_base.values())
fractions = sorted(exact, key=lambda k: exact[k] - global_base[k], reverse=True)
for k in fractions[:missing]:
    global_base[k] += 1

# base by inhouse
b2 = global_base.copy()
b2["bathroom_2"] += b2.get("bathroom_3", 0)
b2.pop("bathroom_3", None)

b3 = global_base.copy()
b3["bathroom_3"] += b3.get("bathroom_2", 0)
b3.pop("bathroom_2", None)

config.update({
    "num_people": len(df),
    "per_week_actual": per_week_actual,
    "global_base": global_base,
    "base_by_inhouse": {
        "2": b2,
        "3": b3
    }
})

with open(CONFIG_FILE, "w") as f:
    json.dump(config, f, indent=4)

print("✅ cleanup_config.json recalculated")

print(f"\n🎯 {PERSON} fully removed from system safely.")
