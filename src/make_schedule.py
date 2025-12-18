import pandas as pd
import re

# ---- user preferences (edit these as you like) ----
MIN_CREDITS = 12
MAX_CREDITS = 15
MUST_INCLUDE = ["ACCT1011"]       # put course codes you must take, or [] if none
PREFERRED_DAYS = {"Mo","We"}      # days you prefer; use {"Mo","We"} etc.
AVOID_DAYS = {"Fr"}               # days you want to avoid entirely
EARLIEST_START = "10:00"          # no classes before this time (24h)
# ---------------------------------------------------

def time_to_minutes(t):
    # "HH:MM" -> minutes
    h, m = t.split(":")
    return int(h)*60 + int(m)

DAY_PATTERN = re.compile(r"(Mo|Tu|We|Th|Fr|Sa|Su)")

def parse_days(day_string):
    # Extract two-letter day tokens from strings like "TuFr", "MoWe", etc.
    return set(DAY_PATTERN.findall(str(day_string)))

def overlaps(a, b):
    # same day & time intervals intersect
    days_a = parse_days(a["days"])
    days_b = parse_days(b["days"])
    if days_a.isdisjoint(days_b):
        return False
    a_start = time_to_minutes(a["start_time"])
    a_end   = time_to_minutes(a["end_time"])
    b_start = time_to_minutes(b["start_time"])
    b_end   = time_to_minutes(b["end_time"])
    return not (a_end <= b_start or b_end <= a_start)

def section_ok(sec, courses, selected_sections):
    # hard filters: avoid days, earliest start, no overlap with chosen sections
    days = parse_days(sec["days"])
    if not days.isdisjoint(AVOID_DAYS):
        return False
    if sec["start_time"] and time_to_minutes(sec["start_time"]) < time_to_minutes(EARLIEST_START):
        return False
    for s in selected_sections:
        if overlaps(sec, s):
            return False
    return True

def score_section(sec):
    # soft score: prefer selected days and later starts
    score = 0
    days = parse_days(sec["days"])
    if not PREFERRED_DAYS or not days.isdisjoint(PREFERRED_DAYS):
        score += 2
    if sec["start_time"] and time_to_minutes(sec["start_time"]) >= time_to_minutes(EARLIEST_START):
        score += 1
    return score

def main():
    courses_df = pd.read_csv("courses_from_csv.csv")
    sections_df = pd.read_csv("sections_from_csv.csv")

    # quick lookups
    course_units = {row["course_id"]: int(row.get("units", 0)) for _, row in courses_df.iterrows()}
    course_title = {row["course_id"]: row.get("title","") for _, row in courses_df.iterrows()}

    # normalize types (just in case)
    for col in ["start_time","end_time","days","course_id","section_id"]:
        if col in sections_df.columns:
            sections_df[col] = sections_df[col].astype(str)

    # ensure we don't pick two sections of the same course
    selected_sections = []
    selected_courses = set()
    total_credits = 0
    explanations = []

    # 1) pick MUST_INCLUDE courses first
    for must in MUST_INCLUDE:
        options = sections_df[sections_df["course_id"] == must].copy()
        if options.empty:
            explanations.append(f"Could not find any sections for required course {must}.")
            continue
        # filter by hard rules
        options = [row for _, row in options.iterrows() if section_ok(row, course_units, selected_sections)]
        if not options:
            explanations.append(f"All sections for {must} conflict with your constraints.")
            continue
        # pick best by score
        options.sort(key=score_section, reverse=True)
        chosen = options[0]
        units = course_units.get(chosen["course_id"], 0)
        if total_credits + units <= MAX_CREDITS:
            selected_sections.append(chosen)
            selected_courses.add(chosen["course_id"])
            total_credits += units
            explanations.append(f"Selected {must} (required). Fits constraints and scored best among its sections.")
        else:
            explanations.append(f"Skipping {must} because adding it would exceed max credits.")

    # 2) fill with other courses up to MAX_CREDITS
    # candidates: sections that pass hard rules and are not already selected course
    candidate_rows = []
    for _, row in sections_df.iterrows():
        cid = row["course_id"]
        if cid in selected_courses:
            continue
        units = course_units.get(cid, 0)
        if units <= 0:
            continue
        if not section_ok(row, course_units, selected_sections):
            continue
        candidate_rows.append(row)

    # sort candidates by score (desc)
    candidate_rows.sort(key=score_section, reverse=True)

    # greedily add until credits satisfied or no more candidates
    for row in candidate_rows:
        cid = row["course_id"]
        if cid in selected_courses:
            continue
        units = course_units.get(cid, 0)
        if total_credits + units > MAX_CREDITS:
            continue
        # check overlap again with the current selection
        if not section_ok(row, course_units, selected_sections):
            continue
        selected_sections.append(row)
        selected_courses.add(cid)
        total_credits += units
        explanations.append(f"Added {cid} as a good fit (days/time preferences).")

        if total_credits >= MIN_CREDITS:
            break

    # ---- output ----
    if not selected_sections:
        print("No feasible schedule found with current constraints.")
        for e in explanations:
            print("-", e)
        return

    print("\nProposed schedule:")
    for sec in selected_sections:
        cid = sec["course_id"]
        title = course_title.get(cid, "")
        print(f"  {cid} - {title} | {sec['section_id']} | {sec['days']} {sec['start_time']}-{sec['end_time']}")
    print(f"Total credits: {total_credits}\n")

    print("Why these were chosen:")
    for e in explanations:
        print(" -", e)

if __name__ == "__main__":
    main()
