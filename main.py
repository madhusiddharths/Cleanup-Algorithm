import subprocess
import json
import sys

CONFIG_FILE = "cleanup_config.json"

# ---------------------------
# Helper to run scripts
# ---------------------------
def run_script(script_name):
    print(f"\n▶ Running {script_name}...")
    result = subprocess.run(
        [sys.executable, script_name],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"\n❌ {script_name} failed with exit code {result.returncode}")
        print("\n--- STDOUT ---")
        print(result.stdout)
        print("\n--- STDERR ---")
        print(result.stderr)
        raise RuntimeError(f"{script_name} failed")

    print(result.stdout)

# ---------------------------
# 1️⃣ Run init.py (fresh semester setup)
# ---------------------------
run_script("init.py")

# ---------------------------
# 2️⃣ Load number of weeks
# ---------------------------
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

num_weeks = config["num_weeks"]
print(f"\n📅 Total weeks to schedule: {num_weeks}")

# ---------------------------
# 3️⃣ Run schedule.py for all weeks
# ---------------------------
for week in range(1, num_weeks + 1):
    print(f"\n📆 Scheduling week {week}/{num_weeks}")
    run_script("schedule.py")

# ---------------------------
# 4️⃣ Run summary.py
# ---------------------------
print("\n📊 Final summary:")
run_script("summary.py")

print("\n✅ Automated semester run completed successfully.")
