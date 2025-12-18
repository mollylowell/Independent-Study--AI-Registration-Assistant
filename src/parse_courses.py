import argparse
import pandas as pd
import re
from datetime import datetime

def parse_section(section: str) -> tuple[str, str]:
    code, sec_id = section.split("-", 1)
    return code, section

def parse_units(tags: str) -> int:
    match = re.search(r"(\d+)\s*Credit", str(tags))
    return int(match.group(1)) if match else 0

DAY_MAP = {"M": "Mo", "T": "Tu", "W": "We", "R": "Th", "F": "Fr", "S": "Sa", "U": "Su"}

def parse_meeting(pattern: str) -> tuple[str, str, str]:
    if pd.isna(pattern):
        return "", "", ""
    try:
        days_part, time_part = [s.strip() for s in pattern.split("|")]
        days = "".join(DAY_MAP.get(ch, ch) for ch in days_part)
        start_str, end_str = [t.strip() for t in time_part.split("-")]
        to24 = lambda t: datetime.strptime(t, "%I:%M %p").strftime("%H:%M")
        return days, to24(start_str), to24(end_str)
    except Exception:
        return "", "", ""

def parse_courses_csv(input_path: str, courses_output: str, sections_output: str) -> None:
    raw = pd.read_csv(input_path, encoding="latin1")
    courses = {}
    sections = []
    for _, row in raw.iterrows():
        course_code, section_id = parse_section(row["Section"])
        units = parse_units(row.get("Course Tags", ""))
        days, start_time, end_time = parse_meeting(row.get("Meeting Patterns", ""))
        if course_code not in courses:
            courses[course_code] = {
                "course_id": course_code,
                "code": course_code,
                "title": row.get("Course Title", ""),
                "units": units,
                "bucket": "Elective",
                "prereqs": [],
                "coreqs": [],
                "repeatable": False,
            }
        sections.append({
            "section_id": section_id,
            "course_id": course_code,
            "instructor": row.get("Instructor", ""),
            "modality": "in-person",
            "campus": row.get("Location", ""),
            "days": days,
            "start_time": start_time,
            "end_time": end_time,
            "capacity": 100,
            "seats_taken": int(row.get("Enrolled", 0)),
        })
    courses_df = pd.DataFrame(courses.values())
    sections_df = pd.DataFrame(sections)
    courses_df.to_csv(courses_output, index=False)
    sections_df.to_csv(sections_output, index=False)

def main():
    parser = argparse.ArgumentParser(description="Parse Fairfield course CSV into structured tables.")
    parser.add_argument("--input", required=True, help="Path to raw CSV (e.g. Updated Analytics Request Fall 2025.csv)")
    parser.add_argument("--courses", default="courses_from_csv.csv", help="Output path for courses CSV")
    parser.add_argument("--sections", default="sections_from_csv.csv", help="Output path for sections CSV")
    args = parser.parse_args()
    parse_courses_csv(args.input, args.courses, args.sections)
    print(f"Wrote {args.courses} and {args.sections}.")

if __name__ == "__main__":
    main()
