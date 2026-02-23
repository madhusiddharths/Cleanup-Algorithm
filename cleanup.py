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

    if "availability" not in df.columns:
        df["availability"] = 1
    names = df[df["availability"] == 1]["name"].tolist()
    random.shuffle(names)

    out_house_people = list(out_house_people)
    in_house_people = set(names) - set(out_house_people)

    MAX_RETRIES = 5
    for attempt in range(MAX_RETRIES):
        week_assignment = {}
        used_people = set()
        person_deficit = {}
        person_remaining = {}
        
        # We need a temporary round robin index in case we need to retry
        temp_round_robin_index = round_robin_index
    
        # -------------------------------------------------
        # Assign IN-HOUSE people first (2 & 3)
        # -------------------------------------------------
        for person in in_house_people:
            person_base = base_by_person.get(person, {})
            person_deficit[person] = {}
            remaining = 0
    
            for c in person_base:
                max_allowed = person_base[c]
                deficit = max_allowed - assigned_so_far[person].get(c, 0)
                person_deficit[person][c] = deficit
                if assigned_so_far[person].get(c, 0) < max_allowed + 1:
                    remaining += 1
    
            person_remaining[person] = remaining
    
        eligible_counts = {c: sum(1 for p in in_house_people if c in base_by_person[p]) for c in cleanup_types}
        sorted_cleanup_types = sorted(cleanup_types, key=lambda c: eligible_counts[c])
    
        cleanup_slots_assigned = {c: [] for c in cleanup_types}
    
        for cleanup in sorted_cleanup_types:
            slots = per_week_actual[cleanup]
            candidates = []
    
            for person in in_house_people:
                if person in used_people:
                    continue
                if cleanup not in base_by_person[person]:
                    continue
                if assigned_so_far[person].get(cleanup, 0) >= base_by_person[person][cleanup] + 1:
                    continue
    
                total_person_deficit = sum(person_deficit[person].values())
                
                # Penalize back-to-back assignments heavily in the initial candidate sort
                is_b2b = 1 if last_cleanup.get(person) == cleanup else 0
    
                candidates.append(
                    (
                        -is_b2b,                            # primary: strongly avoid back-to-back
                        person_deficit[person][cleanup],    # secondary: deficit for THIS cleanup
                        total_person_deficit,               # tertiary: total remaining deficit
                        -person_remaining[person],          # quaternary: fewer types left to do
                        random.random(),                    # tie-breaker
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
    
            allowed_cleanups = [c for c in cleanup_types if c in base_by_person.get(person, {})]
            if not allowed_cleanups:
                allowed_cleanups = cleanup_types.copy()
                
            if "deck_brush" in allowed_cleanups:
                allowed_cleanups.remove("deck_brush")
    
            # pick next cleanup in rotation using week index + person index
            # Look ahead slightly if the next scheduled assignment is a back-to-back
            idx_offset = 0
            while True:
                cleanup_idx = (temp_round_robin_index + i + idx_offset) % len(allowed_cleanups)
                cleanup = allowed_cleanups[cleanup_idx]
                # Break if we found a non-back-to-back cleanup, OR if we've cycled through all options
                if last_cleanup.get(person) != cleanup or idx_offset >= len(allowed_cleanups):
                    break
                idx_offset += 1
    
            week_assignment[person] = cleanup
            used_people.add(person)
            cleanup_slots_assigned[cleanup].append(person)
    
        temp_round_robin_index += 1
    
        # -------------------------------------------------
        # LAST-RESORT (should rarely trigger)
        # -------------------------------------------------
        remaining_people = [p for p in names if p not in used_people]
        for person in remaining_people:
            allowed = base_by_person.get(person, {})
            candidate_cleanups = list(allowed.keys()) if allowed else cleanup_types.copy()
            if person in out_house_people and "deck_brush" in candidate_cleanups:
                candidate_cleanups.remove("deck_brush")
                
            # Avoid back to back if possible
            best_cleanups = sorted(candidate_cleanups, key=lambda c: (1 if last_cleanup.get(person) == c else 0, len(cleanup_slots_assigned[c])))
            best_cleanup = best_cleanups[0]
            
            week_assignment[person] = best_cleanup
            used_people.add(person)
            cleanup_slots_assigned[best_cleanup].append(person)
            print(f"⚠ Week {week}: last-resort assignment for {person} → {best_cleanup}")
            
        # -------------------------------------------------
        # Validation for back-to-back
        # -------------------------------------------------
        has_b2b = False
        for person, cleanup in week_assignment.items():
            if last_cleanup.get(person) == cleanup:
                has_b2b = True
                break
                
        if not has_b2b:
            # Success!
            round_robin_index = temp_round_robin_index
            break
            
        print(f"🔄 Retry {attempt + 1}/{MAX_RETRIES}: Generated schedule had back-to-back assignments (Week {week}). Retrying...")
        # Shuffle names to potentially get a different result in the next attempt
        random.shuffle(names)

    else:
        # Find exactly who has the back-to-back assignment for reporting
        b2b_people = [p for p, c in week_assignment.items() if last_cleanup.get(p) == c]
        b2b_str = ", ".join(b2b_people) if b2b_people else "unknown"
        
        print(f"❌ ERROR: Could not generate a schedule without back-to-back assignments after {MAX_RETRIES} retries for Week {week}.")
        print(f"⚠ Forced back-to-back assignment for: {b2b_str}. Accepting schedule to prevent script failure.")
        
        # We must still update the round robin index even if it failed, so the math continues cleanly next week
        round_robin_index = temp_round_robin_index

    # -------------------------------------------------
    # Update global state
    # -------------------------------------------------
    for person, cleanup in week_assignment.items():
        if person in in_house_people:
            assigned_so_far[person][cleanup] += 1
        last_cleanup[person] = cleanup
        df.loc[df["name"] == person, cleanup] += 1

    return week_assignment, round_robin_index
