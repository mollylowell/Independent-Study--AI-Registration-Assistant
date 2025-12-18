# requirements.py
import re
import pandas as pd
from src.magis_core_rules import MAGIS_RULES
from src.dolan_core_rules import DOLAN_RULES

PREFIX_RX = re.compile(r"^[A-Z]{3,4}")

def course_prefix(code: str) -> str:
    code = str(code).replace(" ", "")
    m = PREFIX_RX.match(code)
    return m.group(0) if m else ""

def course_level(code: str) -> int:
    digits = re.findall(r"\d+", str(code))
    if not digits:
        return 0
    n = int(digits[0])
    return (n // 1000) * 1000  # 1000, 2000, ...

def matches_area(code: str, area_def: dict) -> bool:
    code = code.replace(" ", "")
    # exact course match
    if code in set(area_def.get("by_course", [])):
        return True
    # prefix + optional level rule
    px = course_prefix(code)
    if px and px in set(area_def.get("by_prefix", [])):
        lv_req = area_def.get("level")
        if not lv_req:
            return True
        lvl = course_level(code)
        if lv_req == "1000" and lvl == 1000:
            return True
        if lv_req == "2000+" and lvl >= 2000:
            return True
    return False

def annotate_courses(courses_df: pd.DataFrame) -> pd.DataFrame:
    magis_hits, dolan_hits = [], []
    for _, row in courses_df.iterrows():
        code = str(row["code"]).replace(" ", "")
        m_hits, d_hits = [], []

        # Magis Orientation / Exploration
        for area, spec in MAGIS_RULES["orientation"].items():
            if matches_area(code, spec): m_hits.append(("orientation", area))
        for area, spec in MAGIS_RULES["exploration"].items():
            if matches_area(code, spec): m_hits.append(("exploration", area))

        # Dolan Business Core — exact courses
        if code in set(DOLAN_RULES["business_core"]["required_courses"]):
            d_hits.append(("business_core", code))

        magis_hits.append(m_hits); dolan_hits.append(d_hits)

    out = courses_df.copy()
    out["magis_matches"] = magis_hits
    out["dolan_matches"] = dolan_hits
    return out

def progress_report(completed_codes: list[str], annotated_courses_df: pd.DataFrame) -> dict:
    completed_codes = set(c.replace(" ", "") for c in completed_codes)
    comp = annotated_courses_df[annotated_courses_df["code"].str.replace(" ","").isin(completed_codes)]

    # Business Core
    req = set(DOLAN_RULES["business_core"]["required_courses"])
    missing_business = sorted(list(req - completed_codes))

    # Magis Orientation / Exploration
    def unmet_for(tier: str):
        needs = {k: v["need"] for k, v in MAGIS_RULES[tier].items()}
        have = {k: 0 for k in needs}
        for _, r in comp.iterrows():
            for t, area in r.get("magis_matches", []):
                if t == tier and area in have:
                    have[area] += 1
        return [a for a, need in needs.items() if have.get(a, 0) < need]

    unmet_orientation = unmet_for("orientation")
    unmet_exploration = unmet_for("exploration")

    return {
        "business_core_missing": missing_business,
        "magis_unmet": {"orientation": unmet_orientation, "exploration": unmet_exploration}
    }
