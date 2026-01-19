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

# ---------------------------
# 3️⃣ Load Excel & initialize cleanup counts
# ---------------------------
df = pd.read_excel("actives.xlsx")

cleanup_types = [
    'deck_1',
    'kitchen',
    'deck_0',
    'stairs',
    'deck_brush',
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
num_people = len(df)
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
    "deck_1": 1,
    "deck_0": 3,
    "kitchen": 5,
    "stairs": 2,
    "deck_brush": 2,
    "bathroom_2": 2,
    "bathroom_3": 2,
}

extra_per_week = num_people - sum(min_per_week.values())
cleanup_order = list(min_per_week.keys())

per_week_actual = min_per_week.copy()
for i in range(extra_per_week):
    per_week_actual[cleanup_order[i % len(cleanup_order)]] += 1

# ---------------------------
# 6️⃣ Compute global theoretical base
# ---------------------------
exact = {k: (v * num_weeks) / num_people for k, v in per_week_actual.items()}
global_base = {k: int(exact[k]) for k in exact}

missing = num_weeks - sum(global_base.values())
fractions = sorted(exact.keys(), key=lambda k: exact[k] - global_base[k], reverse=True)
for k in fractions[:missing]:
    global_base[k] += 1

print(f"Theoretical per-person cleanup target for {num_weeks} weeks (global base):")
for k, v in global_base.items():
    print(f"{k}: {v}")

# ---------------------------
# 7️⃣ Compute base by inhouse group
# ---------------------------
# 1 = out-of-house, 2 = 2nd deck, 3 = 3rd deck
base_by_inhouse = {}

# out-of-house: same as global
base_by_inhouse[1] = global_base.copy()

# deck 2: cannot do bathroom_3
b2 = global_base.copy()
b2["bathroom_2"] += b2["bathroom_3"]
del b2["bathroom_3"]
base_by_inhouse[2] = b2

# deck 3: cannot do bathroom_2
b3 = global_base.copy()
b3["bathroom_3"] += b3["bathroom_2"]
del b3["bathroom_2"]
base_by_inhouse[3] = b3

# ---------------------------
# 8️⃣ Save to cleanup_config.json
# ---------------------------
output = {
    "num_people": num_people,
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
