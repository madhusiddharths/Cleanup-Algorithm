import json
import pandas as pd

CHECKPOINT_FILE = "checkpoint.json"
CONFIG_FILE = "cleanup_config.json"
EXCEL_FILE = "actives.xlsx"
OUTPUT_FILE = "summary.xlsx"

# ---------------------------
# Load config
# ---------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

cleanup_types = config["cleanup_types"]
global_base = config["global_base"]
base_by_inhouse = config["base_by_inhouse"]

# ---------------------------
# Load checkpoint
# ---------------------------
with open(CHECKPOINT_FILE, "r") as f:
    checkpoint = json.load(f)

assigned_so_far = checkpoint["assigned_so_far"]
names = list(assigned_so_far.keys())

# ---------------------------
# Load Excel & normalize inhouse
# ---------------------------
df = pd.read_excel(EXCEL_FILE)

def normalize_inhouse(val):
    try:
        return str(int(val))
    except (ValueError, TypeError):
        return "1"  # default: out-of-house

inhouse_map = {
    row["name"]: normalize_inhouse(row["inhouse"])
    for _, row in df.iterrows()
}

# ---------------------------
# 1️⃣ Illegal assignment checks
# ---------------------------
illegal_rows = []

for name in names:
    inhouse_val = inhouse_map.get(name, "1")
    person_base = base_by_inhouse.get(inhouse_val, global_base)

    for c, count in assigned_so_far[name].items():
        if c not in person_base and count > 0:
            illegal_rows.append({
                "name": name,
                "cleanup": c,
                "assigned": count,
                "allowed": "NO"
            })

illegal_df = pd.DataFrame(illegal_rows)

# ---------------------------
# 2️⃣ Deviation warnings (|diff| > 1)
# ---------------------------
deviation_warning_rows = []

for name in names:
    inhouse_val = inhouse_map.get(name, "1")
    person_base = base_by_inhouse.get(inhouse_val, global_base)

    for c, expected in person_base.items():
        assigned = int(assigned_so_far[name].get(c, 0))
        diff = assigned - expected

        if abs(diff) > 1:
            deviation_warning_rows.append({
                "name": name,
                "cleanup": c,
                "assigned": assigned,
                "expected": expected,
                "diff": diff
            })

deviation_warning_df = pd.DataFrame(deviation_warning_rows)

# ---------------------------
# 3️⃣ Assigned cleanups per person
# ---------------------------
summary = pd.DataFrame.from_dict(
    assigned_so_far,
    orient="index"
).fillna(0)

summary = summary.reindex(columns=cleanup_types, fill_value=0)
summary["total"] = summary.sum(axis=1)

# ---------------------------
# 4️⃣ Deviation from theoretical base (PER PERSON)
# ---------------------------
deviation = pd.DataFrame(index=summary.index)

for name in names:
    inhouse_val = inhouse_map.get(name, "1")
    person_base = base_by_inhouse.get(inhouse_val, global_base)

    for c in cleanup_types:
        if c in person_base:
            deviation.loc[name, c] = summary.loc[name, c] - person_base[c]
        else:
            deviation.loc[name, c] = ""  # not applicable

deviation["total"] = summary["total"]

# ---------------------------
# Save everything to Excel
# ---------------------------
with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
    illegal_df.to_excel(
        writer,
        index=False,
        sheet_name="Illegal Assignments"
    )
    deviation_warning_df.to_excel(
        writer,
        index=False,
        sheet_name="Deviation Warnings"
    )
    summary.to_excel(
        writer,
        index=True,
        sheet_name="Assignments"
    )
    deviation.to_excel(
        writer,
        index=True,
        sheet_name="Deviation From Base"
    )

print(f"✅ Summary saved to {OUTPUT_FILE}")
