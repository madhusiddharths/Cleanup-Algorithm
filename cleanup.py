import random

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
    7. Last-resort fallback to ensure full assignment
    """

    names = list(df["name"])
    random.shuffle(names)

    week_assignment = {}
    used_people = set()

    # Coverage milestone: everyone does each allowed cleanup at least once by week 10
    coverage_target = 1 if week <= 10 else None

    # ---------------------------
    # Compute per-person deficit and remaining flexibility
    # ---------------------------
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
                candidates.append(
                    (float("inf"), -person_remaining[person], random.random(), person)
                )
                continue

            # Deficit-aware priority
            deficit = person_deficit[person][cleanup]
            candidates.append(
                (deficit, -person_remaining[person], random.random(), person)
            )

        # Sort candidates: highest priority first
        candidates.sort(reverse=True)

        # ---------------------------
        # Last-resort relaxation if not enough candidates
        # ---------------------------
        if len(candidates) < slots:
            existing = {p for *_, p in candidates}
            for person in names:
                if person in used_people or person in existing:
                    continue

                person_base = base_by_person[person]

                if cleanup not in person_base:
                    continue

                # Respect base+1
                if assigned_so_far[person][cleanup] < person_base[cleanup] + 1:
                    deficit = person_base[cleanup] - assigned_so_far[person][cleanup]
                    candidates.append(
                        (deficit, -person_remaining[person], random.random(), person)
                    )

            candidates.sort(reverse=True)

        # ---------------------------
        # Assign top candidates
        # ---------------------------
        selected = [p for *_, p in candidates[:slots]]

        # Assign to week
        for person in selected:
            week_assignment[person] = cleanup
            used_people.add(person)

    # ---------------------------
    # LAST-RESORT: Assign remaining people if any (guaranteed)
    # ---------------------------
    remaining_people = [p for p in names if p not in used_people]

    for person in remaining_people:
        person_base = base_by_person[person]
        # Candidate cleanups: allowed and below base+1
        candidate_cleanups = [
            c for c in person_base if assigned_so_far[person][c] < person_base[c] + 1
        ]

        # If none available, allow any allowed cleanup
        if not candidate_cleanups:
            candidate_cleanups = list(person_base.keys())

        # Pick cleanup with fewest assignments this week
        assigned_counts = {c: list(week_assignment.values()).count(c) for c in candidate_cleanups}
        best_cleanup = min(assigned_counts, key=lambda x: assigned_counts[x])

        week_assignment[person] = best_cleanup
        used_people.add(person)

        print(f"⚠ Week {week}: last-resort assignment for {person} → {best_cleanup}")

    # ---------------------------
    # Update global state
    # ---------------------------
    for person, cleanup in week_assignment.items():
        assigned_so_far[person][cleanup] += 1
        last_cleanup[person] = cleanup
        df.loc[df["name"] == person, cleanup] += 1

    return week_assignment
