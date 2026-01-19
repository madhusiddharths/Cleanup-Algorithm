import random
from collections import defaultdict
import pandas as pd
import math

def schedule_one_week_final(
    week,
    df,
    cleanup_types,
    per_week_actual,
    base_by_person,      # person -> allowed cleanup base dict
    assigned_so_far,
    last_cleanup,
    num_weeks
):
    """
    Assign one week's cleanups to all people, respecting:
    1. Allowed cleanups per person (in-house constraints)
    2. Base targets per person (base + 1 max)
    3. Coverage milestone (week <= 10)
    4. Deficit priority
    5. Back-to-back restriction for kitchen/deck_0
    6. Weekly slots per cleanup
    7. Last-resort fallback
    8. HARD: Every cleanup must have at least one in-house
    9. SOFT: Max 50% out-of-house, relaxed only if necessary
    """

    names = list(df["name"])
    random.shuffle(names)

    # Determine in-house vs out-of-house
    in_house_people = set(df.loc[df["inhouse"] != 1, "name"])
    out_house_people = set(df.loc[df["inhouse"] == 1, "name"])

    week_assignment = {}
    used_people = set()

    # Coverage milestone: everyone does each allowed cleanup at least once by week 10
    coverage_target = 1 if week <= 10 else None

    # Compute per-person deficit and remaining flexibility
    person_deficit = {}
    person_remaining = {}
    for person in names:
        person_deficit[person] = {}
        remaining = 0
        person_base = base_by_person[person]
        for c in person_base:
            deficit = person_base[c] - assigned_so_far[person][c]
            person_deficit[person][c] = deficit
            if assigned_so_far[person][c] < person_base[c] + 1:
                remaining += 1
        person_remaining[person] = remaining

    # Track cleanup slots assigned this week
    cleanup_slots_assigned = {c: [] for c in cleanup_types}  # list of people

    # Shuffle cleanup order weekly
    ordered_cleanups = cleanup_types.copy()
    random.shuffle(ordered_cleanups)

    # ---------------------------
    # Assign cleanups
    # ---------------------------
    for cleanup in ordered_cleanups:
        slots = per_week_actual[cleanup]
        candidates = []

        for person in names:
            if person in used_people:
                continue

            person_base = base_by_person[person]

            # Person cannot do this cleanup at all
            if cleanup not in person_base:
                continue

            # Hard cap: base + 1
            if assigned_so_far[person][cleanup] >= person_base[cleanup] + 1:
                continue

            # No back-to-back kitchen / deck_0
            if cleanup in {"kitchen", "deck_0"} and last_cleanup[person] == cleanup:
                continue

            # Coverage requirement (week <= 10)
            if coverage_target is not None and assigned_so_far[person][cleanup] < coverage_target:
                deficit_val = float("inf")
            else:
                deficit_val = person_deficit[person][cleanup]

            candidates.append(
                (deficit_val, -person_remaining[person], random.random(), person)
            )

        # Sort candidates: highest priority first
        candidates.sort(reverse=True)

        # ---------------------------
        # Hard in-house / 50% out-of-house check
        # ---------------------------
        assigned_this_cleanup = cleanup_slots_assigned[cleanup].copy()
        final_selected = []

        for *_, person in candidates:
            if len(final_selected) >= slots:
                break

            in_house_count = sum(1 for p in final_selected if p in in_house_people)
            out_house_count = sum(1 for p in final_selected if p in out_house_people)

            remaining_slots = slots - len(final_selected)

            # HARD: must have at least one in-house eventually
            # If only one slot remaining, it must be in-house
            if remaining_slots == 1 and person in out_house_people and in_house_count == 0:
                continue

            # Soft: max 50% out-of-house, but relax later
            max_out_house = math.floor(slots / 2)
            if person in out_house_people and out_house_count >= max_out_house:
                continue

            final_selected.append(person)

        # ---------------------------
        # Last-resort relaxation if not enough candidates
        # ---------------------------
        remaining_needed = slots - len(final_selected)
        if remaining_needed > 0:
            # Consider all remaining people not yet assigned
            remaining_people = [p for p in names if p not in used_people and p not in final_selected]
            # Sort remaining by deficit / random
            remaining_people.sort(key=lambda p: (
                -person_deficit[p].get(cleanup, 0),
                random.random()
            ))

            for person in remaining_people:
                if len(final_selected) >= slots:
                    break
                in_house_count = sum(1 for p in final_selected if p in in_house_people)
                out_house_count = sum(1 for p in final_selected if p in out_house_people)
                remaining_slots = slots - len(final_selected)

                # HARD: must have ≥1 in-house
                if remaining_slots == 1 and person in out_house_people and in_house_count == 0:
                    continue

                # Soft: may exceed 50% if necessary
                final_selected.append(person)

        # ---------------------------
        # Assign selected
        # ---------------------------
        for person in final_selected:
            week_assignment[person] = cleanup
            used_people.add(person)
            cleanup_slots_assigned[cleanup].append(person)

    # ---------------------------
    # LAST-RESORT: assign any remaining people
    # ---------------------------
    remaining_people = [p for p in names if p not in used_people]
    for person in remaining_people:
        person_base = base_by_person[person]
        candidate_cleanups = list(person_base.keys())

        # Pick cleanup with fewest assigned this week
        assigned_counts = {c: len(cleanup_slots_assigned[c]) for c in candidate_cleanups}
        best_cleanup = min(assigned_counts, key=lambda x: assigned_counts[x])

        week_assignment[person] = best_cleanup
        used_people.add(person)
        cleanup_slots_assigned[best_cleanup].append(person)
        print(f"⚠ Week {week}: last-resort assignment for {person} → {best_cleanup}")

    # ---------------------------
    # Update global state
    # ---------------------------
    for person, cleanup in week_assignment.items():
        assigned_so_far[person][cleanup] += 1
        last_cleanup[person] = cleanup
        df.loc[df["name"] == person, cleanup] += 1

    return week_assignment
