# 🧹 Cleanup Scheduling System
**Phi Kappa Sigma - Alpha Epsilon Chapter**

An automated, fair, and reliable system for scheduling weekly cleanups. This algorithm ensures that responsibilities are distributed equitably among members based on their residency status and previous contribution history.

---

## 💎 Credits
This system was developed through the joint efforts of **Madhu Siddharth** and **Ronal**. Their work ensures that the house's operational needs are met while maintaining fairness for all members.

---

## 🚀 Core Components

### 🏗️ Setup & Orchestration
- **`init.py`**: Initializes a fresh semester. It clears previous history, computes theoretical per-person targets (global base), and prepares the configuration.
- **`main.py`**: The "one-click" semester runner. It automates the entire process from initialization to final summary generation.
- **`summary.py`**: Generates a detailed `summary.xlsx` report, including assignment counts, deviation from base targets, and illegal assignment checks.

### 📅 Scheduling Logic
- **`schedule.py`**: The primary script for running a single week's assignment. It persists the state in `checkpoint.json`.
- **`cleanup.py`**: Contains the core logic. It handles residency-specific rules, task prioritization, and fair candidate selection.
- **`rollback.py`**: Safely undoes the most recent week if a correction is needed.
- **`rebuild.py`**: A recovery tool that can reconstruct the `checkpoint.json` state from the `weekly_assignments.xlsx` file.

---

## 🛠️ Assignment Logic

### 🏠 In-House Members (Groups 2 & 3)
- **Deficit-Based Allocation**: Priority is given to members who are furthest behind their theoretical targets.
- **Constrained Task Prioritization**: Tasks with fewer eligible candidates (like bathrooms) are assigned first to ensure they are always covered by the right people.
- **Milestone Awareness**: Respects group-specific constraints (e.g., certain groups are restricted from specific bathrooms).

### 🌳 Out-of-House Members (Groups 0 & 1)
- **Round-Robin Rotation**: These members participate in a weekly rotating cleanup schedule, ensuring variety and consistency without complex deficit tracking.

---

## 📄 Data Files
- **`actives.xlsx`**: The source of truth for member names and their residency status (`inhouse` column). It is updated weekly with cumulative counts.
- **`cleanup_config.json`**: Contains system-calculated parameters, including per-week requirements and per-group base targets.
- **`checkpoint.json`**: The internal state tracking system (last assignments, cumulative history, etc.).
- **`weekly_assignments.xlsx`**: A human-readable record of assignments made week-by-week.

---

## 🏁 Quick Start
To simulate an entire semester:
```bash
python3 main.py
```

To run assignments week-by-week:
1. `python3 init.py` (once at start of semester)
2. `python3 schedule.py` (run once every week)
3. `python3 summary.py` (to view reports)
