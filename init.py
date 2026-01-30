import pandas as pd
import json
import math
from datetime import datetime
import os

# ---------------------------
# 1️⃣ Print credits
# ---------------------------
print("\n🧹 Cleanup Scheduling System Credits")
print("This cleanup algorithm was made possible thanks to the efforts of Madhu Siddharth and Ronal.")
print("Their work ensures that weekly cleanups are distributed fairly and efficiently.\n")

# ---------------------------
# 2️⃣ Clear old checkpoint
# ---------------------------
CHECKPOINT_FILE = "checkpoint.json"
if os.path.exists(CHECKPOINT_FILE):
    os.remove(CHECKPOINT_FILE)
    print("✅ checkpoint.json cleared (fresh semester start)")

WEEKLY_EXCEL_FILE = "weekly_assignments.xlsx"
if os.path.exists(WEEKLY_EXCEL_FILE):
    os.remove(WEEKLY_EXCEL_FILE)
    print(f"✅ {WEEKLY_EXCEL_FILE} cleared (fresh semester start)")

# ---------------------------
# 3️⃣ Load Excel & initialize cleanup counts
# ---------------------------
df = pd.read_excel("actives.xlsx")

cleanup_types = [
    'kitchen',
    'deck_0',
    'stairs',
    'deck_brush',
    'deck_1',
    'bathroom_2',
    'bathroom_3',
]

for c in cleanup_types:
    df[c] = 0

df.to_excel("actives.xlsx", index=False)
print("✅ Cleanup count columns initialized in actives.xlsx")

# ---------------------------
# 4️⃣ Compute weeks & people
# ---------------------------
num_people = len(df[df["inhouse"].isin([2,3])])  # only count in-house for per-week actual
start_date_str = "2026-01-15"
end_date_str = "2026-05-07"

start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

total_days = (end_date - start_date).days + 1
num_weeks = math.ceil(total_days / 7)
print(f"Total weeks: {num_weeks}")

# ---------------------------
# 5️⃣ Minimum & actual per-week requirements
# ---------------------------
min_per_week = {
    "deck_0": 3,
    "kitchen": 5,
    "stairs": 2,
    "deck_brush": 2,
    "deck_1": 2,
    "bathroom_2": 2,
    "bathroom_3": 2,
}

# Only in-house (2 & 3) count for extra distribution
inhouse_count = num_people
extra_per_week = inhouse_count - sum(min_per_week.values())
cleanup_order = list(min_per_week.keys())

per_week_actual = min_per_week.copy()
i = 0
while extra_per_week > 0:
    cleanup = cleanup_order[i % len(cleanup_order)]

    # Special case: bathroom pair must be incremented together
    if cleanup == "bathroom_2":
        if extra_per_week >= 2:
            per_week_actual["bathroom_2"] += 1
            per_week_actual["bathroom_3"] += 1
            extra_per_week -= 2
        else:
            # Not enough people to increment both bathrooms; skip bathroom_2 for now
            i += 1
            continue
    elif cleanup == "deck_brush":
        # Increment by 2 unless only 1 person left
        inc = 2 if extra_per_week >= 2 else 1
        per_week_actual["deck_brush"] += inc
        extra_per_week -= inc
    else:
        per_week_actual[cleanup] += 1
        extra_per_week -= 1

    i += 1

print(f"Per-week actual cleanup distribution (in-house only):")
for k, v in per_week_actual.items():
    print(f"{k}: {v}")

# ---------------------------
# 6️⃣ Compute global theoretical base
# ---------------------------
exact = {k: (v * num_weeks) / inhouse_count for k, v in per_week_actual.items()}
global_base = {k: int(exact[k]) for k in exact}

missing = num_weeks - sum(global_base.values())
fractions = sorted(exact.keys(), key=lambda k: exact[k] - global_base[k], reverse=True)
for k in fractions[:missing]:
    global_base[k] += 1

print(f"Theoretical per-person cleanup target for {num_weeks} weeks (global base):")
for k, v in global_base.items():
    print(f"{k}: {v}")

# ---------------------------
# 7️⃣ Compute base by inhouse group (only 2 & 3)
# ---------------------------
base_by_inhouse = {}

# deck 2: cannot do bathroom_3
b2 = global_base.copy()
b2["bathroom_2"] += b2.get("bathroom_3",0)
b2.pop("bathroom_3", None)
base_by_inhouse[2] = b2

# deck 3: cannot do bathroom_2
b3 = global_base.copy()
b3["bathroom_3"] += b3.get("bathroom_2",0)
b3.pop("bathroom_2", None)
base_by_inhouse[3] = b3

print("Base targets by in-house group (2 & 3 only):")
print(json.dumps(base_by_inhouse, indent=2))

# ---------------------------
# 8️⃣ Save to cleanup_config.json
# ---------------------------
output = {
    "num_people": len(df),
    "num_weeks": num_weeks,
    "cleanup_types": cleanup_types,
    "min_per_week": min_per_week,
    "per_week_actual": per_week_actual,
    "global_base": global_base,
    "base_by_inhouse": base_by_inhouse
}

with open("cleanup_config.json", "w") as f:
    json.dump(output, f, indent=4)

print("✅ cleanup_config.json saved with per-inhouse theoretical bases")
