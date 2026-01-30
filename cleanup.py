import random
from collections import defaultdict
import pandas as pd

def schedule_one_week_final(
    week,
    df,
    cleanup_types,
    per_week_actual,
    base_by_person,      # person -> allowed cleanup base dict
    assigned_so_far,
    last_cleanup,
    num_weeks,
    out_house_people,
    round_robin_index
):
    """
    Assign one week's cleanups to all people.

    - In-house people (2 & 3) respect base +1 caps and coverage milestone.
    - Out-of-house people (0 & 1) are assigned using TRUE round-robin over their allowed cleanups.
    - Returns (week_assignment, updated_round_robin_index)
    """

    names = list(df["name"])
    random.shuffle(names)

    out_house_people = list(out_house_people)
    in_house_people = set(names) - set(out_house_people)

    week_assignment = {}
    used_people = set()

    # -------------------------------------------------
    # Assign IN-HOUSE people first (2 & 3)
    # -------------------------------------------------
    person_deficit = {}
    person_remaining = {}

    for person in in_house_people:
        person_base = base_by_person.get(person, {})
        person_deficit[person] = {}
        remaining = 0

        for c in person_base:  # only their allowed cleanups
            max_allowed = person_base[c]
            deficit = max_allowed - assigned_so_far[person].get(c, 0)
            person_deficit[person][c] = deficit
            if assigned_so_far[person].get(c, 0) < max_allowed + 1:
                remaining += 1

        person_remaining[person] = remaining

    cleanup_slots_assigned = {c: [] for c in cleanup_types}

    # Assign in-house people based on deficit and available slots
    for cleanup in cleanup_types:
        slots = per_week_actual[cleanup]
        candidates = []

        for person in in_house_people:
            if person in used_people:
                continue
            if cleanup not in base_by_person[person]:
                continue
            if assigned_so_far[person].get(cleanup, 0) >= base_by_person[person][cleanup] + 1:
                continue

            candidates.append(
                (
                    person_deficit[person][cleanup],
                    -person_remaining[person],
                    random.random(),
                    person
                )
            )

        candidates.sort(reverse=True)
        selected = [p for *_, p in candidates[:slots]]

        for person in selected:
            week_assignment[person] = cleanup
            used_people.add(person)
            cleanup_slots_assigned[cleanup].append(person)

    # -------------------------------------------------
    # TRUE ROUND-ROBIN for OUT-OF-HOUSE (0 & 1)
    # -------------------------------------------------
    for i, person in enumerate(out_house_people):
        if person in used_people:
            continue

        # allowed cleanups (empty dict means all cleanups)
        allowed_cleanups = [c for c in cleanup_types if c in base_by_person.get(person, {})]
        if not allowed_cleanups:
            allowed_cleanups = cleanup_types.copy()

        # pick next cleanup in rotation using week index + person index
        cleanup_idx = (round_robin_index + i) % len(allowed_cleanups)
        cleanup = allowed_cleanups[cleanup_idx]

        week_assignment[person] = cleanup
        used_people.add(person)
        cleanup_slots_assigned[cleanup].append(person)

    # Increment for next week
    round_robin_index += 1

    # -------------------------------------------------
    # LAST-RESORT (should rarely trigger)
    # -------------------------------------------------
    remaining_people = [p for p in names if p not in used_people]
    for person in remaining_people:
        allowed = base_by_person.get(person, {})
        candidate_cleanups = list(allowed.keys()) if allowed else cleanup_types
        best_cleanup = min(candidate_cleanups, key=lambda c: len(cleanup_slots_assigned[c]))
        week_assignment[person] = best_cleanup
        used_people.add(person)
        cleanup_slots_assigned[best_cleanup].append(person)
        print(f"⚠ Week {week}: last-resort assignment for {person} → {best_cleanup}")

    # -------------------------------------------------
    # Update global state
    # -------------------------------------------------
    for person, cleanup in week_assignment.items():
        if person in in_house_people:
            assigned_so_far[person][cleanup] += 1
        last_cleanup[person] = cleanup
        df.loc[df["name"] == person, cleanup] += 1

    return week_assignment, round_robin_index
