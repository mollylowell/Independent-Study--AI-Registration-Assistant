# planner.py
import re
import pandas as pd

from src.paths import COURSES_CSV, SECTIONS_CSV
from src.dolan_core_rules import DOLAN_RULES
from src.magis_core_rules import MAGIS_RULES
from src.requirements import annotate_courses, progress_report

# ---------- Natural language → preferences ----------
def parse_request(text: str):
    t = text.lower()
    day_map = {
        "monday": "Mo", "tuesday": "Tu", "wednesday": "We",
        "thursday": "Th", "friday": "Fr", "saturday": "Sa", "sunday": "Su",
        "mo": "Mo", "tu": "Tu", "we": "We", "th": "Th", "fr": "Fr", "sa": "Sa", "su": "Su"
    }
    prefs = {
        "min_credits": 12, "max_credits": 15,
        "avoid_days": set(), "preferred_days": set(),
        "earliest_start": None, "must_include": set(), "include_capstone": False
    }

    # credits like "18 credits" or "12-15 credits"
    m = re.search(r"(\d{1,2})\s*-\s*(\d{1,2})\s*credits?", t)
    if m:
        prefs["min_credits"], prefs["max_credits"] = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"(\d{1,2})\s*credits?", t)
        if m:
            prefs["min_credits"] = prefs["max_credits"] = int(m.group(1))

    # avoid/prefer/only days
    for word, code in day_map.items():
        if re.search(rf"\bavoid\s+{word}\b", t):
            prefs["avoid_days"].add(code)
        if re.search(rf"\bonly\s+{word}s?\b", t):
            prefs["preferred_days"] = {code}
        if re.search(rf"\b{word}s?\b", t) and "avoid" not in t[max(0, t.find(word)-8):t.find(word)+8]:
            prefs["preferred_days"].add(code)

    # earliest start: "no classes before 10am"
    m = re.search(r"(?:before|earlier than|no.*before)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)", t)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2) or 0)
        ap = m.group(3)
        if ap == "pm" and h != 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        prefs["earliest_start"] = f"{h:02d}:{mm:02d}"

    # explicit course codes and Capstone
    for code in re.findall(r"\b[A-Z]{3,4}\s*\d{4}\b", text.upper()):
        prefs["must_include"].add(code.replace(" ", ""))
    if "capstone" in t:
        prefs["include_capstone"] = True

    return prefs


# ---------- helpers ----------
def t2m(t):
    if not t or t == "nan":
        return None
    h, m = str(t).split(":")
    return int(h) * 60 + int(m)

def parse_days(s):
    if not isinstance(s, str):
        s = str(s)
    return {s[i:i+2] for i in range(0, len(s), 2) if len(s[i:i+2]) == 2}

def overlap(a, b):
    da, db = parse_days(a["days"]), parse_days(b["days"])
    if da.isdisjoint(db):
        return False
    a1, a2 = t2m(a["start_time"]), t2m(a["end_time"])
    b1, b2 = t2m(b["start_time"]), t2m(b["end_time"])
    if None in (a1, a2, b1, b2):
        return False
    return not (a2 <= b1 or b2 <= a1)

def hard_ok(sec, prefs):
    if not parse_days(sec["days"]).isdisjoint(prefs["avoid_days"]):
        return False
    if prefs["earliest_start"]:
        st = t2m(sec["start_time"])
        if st is not None and st < t2m(prefs["earliest_start"]):
            return False
    return True

def score(sec, prefs):
    s = 0
    d = parse_days(sec["days"])
    if (not prefs["preferred_days"]) or (not d.isdisjoint(prefs["preferred_days"])):
        s += 2
    if prefs["earliest_start"]:
        st = t2m(sec["start_time"])
        if st is not None and st >= t2m(prefs["earliest_start"]):
            s += 1
    return s


# ---------- main planner ----------
def build_schedule(user_text, completed_codes=None):
    prefs = parse_request(user_text)
    completed_codes = [c.replace(" ", "") for c in (completed_codes or [])]

    # load data (portable paths!)
    courses = pd.read_csv(COURSES_CSV)
    sections = pd.read_csv(SECTIONS_CSV)

    # annotate + degree progress
    annotated = annotate_courses(courses)
    pr = progress_report(completed_codes, annotated)
    missing_bc = pr["business_core_missing"]
    unmet = pr["magis_unmet"]

    units = {r["course_id"]: int(r.get("units", 0)) for _, r in courses.iterrows()}
    titles = {r["course_id"]: r.get("title", "") for _, r in courses.iterrows()}
    codes = {r["course_id"]: str(r.get("code", "")) for _, r in courses.iterrows()}

    selected, used_courses, credits, reasons = [], set(), 0, []

    # 1) must-include (NL) + optional Capstone
    musts = set(prefs["must_include"])
    if prefs["include_capstone"]:
        musts.add("MGMT4300")

    for want in musts:
        opts = courses[courses["code"] == want][["course_id", "code", "title", "units"]].merge(
            sections, on="course_id", how="inner"
        )
        opts = [
            s for _, s in opts.iterrows()
            if s["course_id"] not in used_courses
            and hard_ok(s, prefs)
            and not any(overlap(s, x) for x in selected)
        ]
        if not opts:
            reasons.append(f"No section fits for requested {want}.")
            continue

        opts.sort(key=lambda s: score(s, prefs), reverse=True)
        best = opts[0]
        u = units.get(best["course_id"], 0)

        if credits + u <= prefs["max_credits"]:
            selected.append(best)
            used_courses.add(best["course_id"])
            credits += u
            reasons.append(f"Included requested {want}.")

    # 2) Business Core gaps
    for code in missing_bc:
        if credits >= prefs["max_credits"]:
            break

        opts = courses[courses["code"] == code][["course_id", "code", "title", "units"]].merge(
            sections, on="course_id", how="inner"
        )
        opts = [
            s for _, s in opts.iterrows()
            if s["course_id"] not in used_courses
            and hard_ok(s, prefs)
            and not any(overlap(s, x) for x in selected)
        ]
        if not opts:
            reasons.append(f"No available section for Business Core {code}.")
            continue

        opts.sort(key=lambda s: score(s, prefs), reverse=True)
        best = opts[0]
        u = units.get(best["course_id"], 0)

        if credits + u <= prefs["max_credits"]:
            selected.append(best)
            used_courses.add(best["course_id"])
            credits += u
            reasons.append(f"Added Business Core: {code}.")

            for co in DOLAN_RULES["business_core"].get("co_reqs", {}).get(code, []):
                co_opts = courses[courses["code"] == co][["course_id", "code", "title", "units"]].merge(
                    sections, on="course_id", how="inner"
                )
                co_opts = [
                    s for _, s in co_opts.iterrows()
                    if s["course_id"] not in used_courses
                    and hard_ok(s, prefs)
                    and not any(overlap(s, x) for x in selected)
                ]
                if co_opts:
                    co_opts.sort(key=lambda s: score(s, prefs), reverse=True)
                    cbest = co_opts[0]
                    uu = units.get(cbest["course_id"], 0)

                    if credits + uu <= prefs["max_credits"]:
                        selected.append(cbest)
                        used_courses.add(cbest["course_id"])
                        credits += uu
                        reasons.append(f"Added co-requisite: {co}.")

    # 3) Magis unmet (Orientation then Exploration) — one course per unmet area
    def pick_magis(tier):
        nonlocal selected, used_courses, credits
        for area in unmet[tier]:
            if credits >= prefs["max_credits"]:
                break

            cand_ids = [
                r["course_id"] for _, r in annotated.iterrows()
                if any(t == tier and a == area for (t, a) in r.get("magis_matches", []))
            ]
            if not cand_ids:
                reasons.append(f"No course found for Magis {tier}: {area}.")
                continue

            merged = courses[courses["course_id"].isin(cand_ids)][["course_id", "code", "title", "units"]].merge(
                sections, on="course_id", how="inner"
            )
            opts = [
                s for _, s in merged.iterrows()
                if s["course_id"] not in used_courses
                and hard_ok(s, prefs)
                and not any(overlap(s, x) for x in selected)
            ]
            if not opts:
                reasons.append(f"All sections conflict for Magis {tier}: {area}.")
                continue

            opts.sort(key=lambda s: score(s, prefs), reverse=True)
            best = opts[0]
            u = units.get(best["course_id"], 0)

            if credits + u <= prefs["max_credits"]:
                selected.append(best)
                used_courses.add(best["course_id"])
                credits += u
                reasons.append(f"Added Magis {tier} – {area}: {best['code']}.")

    if credits < prefs["min_credits"]:
        pick_magis("orientation")
    if credits < prefs["min_credits"]:
        pick_magis("exploration")

    # 4) Fill up to credit floor with best non-conflicting fits
    if credits < prefs["min_credits"]:
        merged = courses[["course_id", "code", "title", "units"]].merge(sections, on="course_id", how="inner")
        cand = [
            s for _, s in merged.iterrows()
            if s["course_id"] not in used_courses
            and units.get(s["course_id"], 0) > 0
            and hard_ok(s, prefs)
            and not any(overlap(s, x) for x in selected)
        ]
        cand.sort(key=lambda s: score(s, prefs), reverse=True)
        for s in cand:
            u = units.get(s["course_id"], 0)
            if credits + u > prefs["max_credits"]:
                continue
            selected.append(s)
            used_courses.add(s["course_id"])
            credits += u
            reasons.append(f"Added good-fit filler: {s['code']}.")
            if credits >= prefs["min_credits"]:
                break

    # Output
    pretty = [
        f"{codes[s['course_id']]} - {titles[s['course_id']]} | {s['section_id']} | {s['days']} {s['start_time']}-{s['end_time']}"
        for s in selected
    ]
    return {
        "schedule": pretty,
        "credits": credits,
        "reasons": reasons,
        "prefs": prefs,
        "progress": pr,
    }


if __name__ == "__main__":
    import sys
    user_text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "15 credits, prefer Tu/Th, avoid Friday, no classes before 10am"
    result = build_schedule(user_text, completed_codes=[])

    print("\nRequest:", user_text)
    print("\nProposed schedule:")
    for line in result["schedule"]:
        print("  ", line)
    print("Total credits:", result["credits"])

    print("\nWhy chosen:")
    for r in result["reasons"]:
        print(" -", r)

    print("\nProgress snapshot:")
    print("  Business Core missing:", result["progress"]["business_core_missing"])
    print("  Magis Orientation unmet:", result["progress"]["magis_unmet"]["orientation"])
    print("  Magis Exploration unmet:", result["progress"]["magis_unmet"]["exploration"])
