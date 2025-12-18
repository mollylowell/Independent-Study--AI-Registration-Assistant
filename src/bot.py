
import argparse
import os
import sys
import json

# Local imports (assumes bot.py sits next to planner.py, parse_courses.py, etc.)
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import planner as pl  # your main scheduler
import parse_courses as pc  # to regenerate tables if needed

COURSES_CSV = os.path.join(HERE, "courses_from_csv.csv")
SECTIONS_CSV = os.path.join(HERE, "sections_from_csv.csv")
RAW_CSV_DEFAULT = os.path.join(HERE, "Updated Analytics Request Fall 2025.csv")

def _t2m_safe(t):
    """Safer time parser: tolerates blanks/TBA and returns None."""
    try:
        if t is None:
            return None
        s = str(t).strip().lower()
        if not s or s == "nan" or ":" not in s:
            return None
        h, m = s.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None

def patch_planner_time_parser():
    """Monkey-patch planner.t2m to the safer version so overlap() won't crash."""
    try:
        pl.t2m = _t2m_safe
    except Exception:
        pass

def ensure_tables(raw_csv=None, quiet=False):
    """
    Ensure courses_from_csv.csv and sections_from_csv.csv exist.
    If missing and a raw CSV is present, auto-generate them via parse_courses.
    """
    have_courses = os.path.exists(COURSES_CSV)
    have_sections = os.path.exists(SECTIONS_CSV)

    if have_courses and have_sections:
        return True

    raw_csv = raw_csv or RAW_CSV_DEFAULT
    if not os.path.exists(raw_csv):
        if not quiet:
            print("ERROR: Structured tables are missing and the raw CSV was not found:")
            print(" - Expected:", COURSES_CSV)
            print(" - Expected:", SECTIONS_CSV)
            print(" - Missing raw CSV to regenerate:", raw_csv)
            print("Fix: Place your 'Updated Analytics Request Fall 2025.csv' next to bot.py or pass --raw path.")
        return False

    # attempt to regenerate
    try:
        pc.parse_courses_csv(raw_csv, COURSES_CSV, SECTIONS_CSV)
        if not quiet:
            print(f"Regenerated tables from raw CSV:\n - {COURSES_CSV}\n - {SECTIONS_CSV}")
        return True
    except Exception as e:
        if not quiet:
            print("ERROR: Failed to regenerate structured tables from raw CSV.")
            print("Reason:", e)
        return False

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Natural-language scheduler bot for Fairfield course planning (prototype)."
    )
    parser.add_argument("request", nargs="*", help="Natural-language request, e.g., '15 credits, Tu/Th, avoid Friday, no classes before 10am'")
    parser.add_argument("--completed", "-c", action="append", default=[],
                        help="Previously completed course codes (repeatable). e.g., -c ENGL1001 -c MATH1121")
    parser.add_argument("--raw", help="Path to raw registrar CSV (if tables need regeneration).")
    parser.add_argument("--json", action="store_true", help="Output full JSON instead of pretty text.")
    args = parser.parse_args(argv)

    user_text = " ".join(args.request).strip() or "15 credits, prefer Tu/Th, avoid Friday, no classes before 10am"

    # Make sure CSVs exist (or can be built)
    if not ensure_tables(raw_csv=args.raw, quiet=False):
        sys.exit(2)

    # Patch planner's time parser for robustness
    patch_planner_time_parser()

    # Build schedule
    try:
        result = pl.build_schedule(user_text, completed_codes=args.completed)
    except Exception as e:
        print("ERROR: build_schedule failed.")
        print("Reason:", e)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    # Pretty print
    print("Request:", user_text)
    if args.completed:
        print("Completed:", ", ".join(args.completed))

    print("\nProposed schedule:")
    if not result.get("schedule"):
        print("  (no feasible schedule found given constraints)")
    else:
        for line in result["schedule"]:
            print(" ", line)

    print("Total credits:", result.get("credits", 0))

    print("\nWhy chosen:")
    for r in result.get("reasons", []):
        print(" -", r)

    pr = result.get("progress", {})
    if pr:
        print("\nProgress snapshot:")
        bc = pr.get("business_core_missing", [])
        mag = pr.get("magis_unmet", {})
        print("  Business Core missing:", bc)
        print("  Magis Orientation unmet:", mag.get("orientation", []))
        print("  Magis Exploration unmet:", mag.get("exploration", []))

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
