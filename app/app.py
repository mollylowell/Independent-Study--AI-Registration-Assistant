"""
app/app.py — AI Course Registration Assistant (Professional)
Run from repo root:
  streamlit run app/app.py

Optional secrets:
  .streamlit/secrets.toml
    APP_PASSWORD = "StagBotAdvisor"
"""

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.paths import DATA_DIR, COURSES_CSV, SECTIONS_CSV
from src.planner import build_schedule
from src.parse_courses import parse_courses_csv
from src import requirements as req


# ---------------------------
# Streamlit config
# ---------------------------
st.set_page_config(
    page_title="AI Course Registration Assistant",
    page_icon="🗓️",
    layout="wide",
)


# ---------------------------
# Helpers
# ---------------------------
def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def json_default(o: Any):
    # Planner prefs may include sets — make JSON-safe
    if isinstance(o, set):
        return sorted(list(o))
    return str(o)


def unique_codes(codes: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for c in codes:
        c = (c or "").strip().replace(" ", "")
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def parse_completed_from_csv(file_bytes: bytes) -> list[str]:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        col = "code" if "code" in df.columns else df.columns[0]
        return [str(c).strip().replace(" ", "") for c in df[col].dropna().astype(str)]
    except Exception:
        return []


def parse_completed_from_json(file_bytes: bytes) -> list[str]:
    try:
        data = json.loads(file_bytes.decode("utf-8"))
        if isinstance(data, list):
            return [str(x).strip().replace(" ", "") for x in data]
        if isinstance(data, dict) and "completed" in data:
            return [str(x).strip().replace(" ", "") for x in data["completed"]]
        return []
    except Exception:
        return []


def profile_path(name: str) -> Path:
    safe = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_")).strip() or "profile"
    return DATA_DIR / f"profile_{safe}.json"


def save_profile(name: str, data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    profile_path(name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_profile(name: str) -> dict | None:
    p = profile_path(name)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def try_load_tables():
    if COURSES_CSV.exists() and SECTIONS_CSV.exists():
        try:
            return pd.read_csv(COURSES_CSV), pd.read_csv(SECTIONS_CSV), None
        except Exception as e:
            return None, None, f"Failed reading tables: {e}"
    return None, None, "Structured tables not found yet."


# ---------------------------
# Passcode gate (optional)
# ---------------------------
def login_gate():
    st.session_state.setdefault("authed", False)
    expected = st.secrets.get("APP_PASSWORD", None)

    if not expected:
        st.sidebar.info("🔓 No APP_PASSWORD set. App is currently open.")
        return

    if st.session_state["authed"]:
        st.sidebar.success("🔒 Access granted")
        if st.sidebar.button("Log out", use_container_width=True):
            st.session_state["authed"] = False
            rerun()
        return

    st.title("🔒 Private App")
    st.write("Enter the passcode to continue.")
    pw = st.text_input("Passcode", type="password")
    if st.button("Let me in"):
        if pw == expected:
            st.session_state["authed"] = True
            rerun()
        else:
            st.error("Incorrect passcode.")


login_gate()
if st.secrets.get("APP_PASSWORD") and not st.session_state.get("authed", False):
    st.stop()


# ---------------------------
# Header
# ---------------------------
st.title("🗓️ AI Course Registration Assistant (Prototype)")
st.caption("Fairfield Dolan • Natural-language scheduling • Degree progress snapshot • Upload-ready")

with st.expander("ℹ️ How this works"):
    st.markdown(
        """
**Goal:** Convert plain-English preferences (e.g., “Tu/Th only, 15 credits, avoid Friday, no classes before 10am”)
plus degree rules into a conflict-free schedule with explanations.

**Data options:**
- If you already have structured tables in `data/`, you're ready.
- Or upload the raw registrar CSV and this app will generate:
  - `data/courses_from_csv.csv`
  - `data/sections_from_csv.csv`
"""
    )


# ---------------------------
# Sidebar — 1) Course Data
# ---------------------------
st.sidebar.header("1) Course Data")
st.sidebar.caption(f"Tables path: {COURSES_CSV.name} and {SECTIONS_CSV.name} (stored in data/)")

raw_csv_upload = st.sidebar.file_uploader("Upload raw registrar CSV (optional)", type=["csv"])

if st.sidebar.button("Build tables from uploaded raw CSV", use_container_width=True):
    if raw_csv_upload is None:
        st.sidebar.error("Upload a raw registrar CSV first.")
    else:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            tmp_raw = DATA_DIR / "_uploaded_raw.csv"
            tmp_raw.write_bytes(raw_csv_upload.getbuffer())

            parse_courses_csv(str(tmp_raw), str(COURSES_CSV), str(SECTIONS_CSV))
            st.sidebar.success("✅ Built courses_from_csv.csv and sections_from_csv.csv in data/")
        except Exception as e:
            st.sidebar.error(f"Failed to build tables: {e}")

courses_upload = st.sidebar.file_uploader("Upload courses_from_csv.csv", type=["csv"])
sections_upload = st.sidebar.file_uploader("Upload sections_from_csv.csv", type=["csv"])

if st.sidebar.button("Save uploaded structured tables", use_container_width=True):
    if not courses_upload or not sections_upload:
        st.sidebar.error("Upload BOTH structured files first.")
    else:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            COURSES_CSV.write_bytes(courses_upload.getbuffer())
            SECTIONS_CSV.write_bytes(sections_upload.getbuffer())
            st.sidebar.success("✅ Saved structured tables into data/")
        except Exception as e:
            st.sidebar.error(f"Saving tables failed: {e}")


courses_df, sections_df, tables_msg = try_load_tables()
if courses_df is not None and sections_df is not None:
    st.sidebar.success("✅ Structured tables loaded.")
else:
    st.sidebar.info(f"ℹ️ {tables_msg}")


# ---------------------------
# Sidebar — 2) Student Data (completed courses)
# ---------------------------
st.sidebar.header("2) Student Data (completed courses)")
completed_from_upload: list[str] = []

student_file = st.sidebar.file_uploader(
    "Upload completed courses (CSV w/ 'code' column, or JSON list)",
    type=["csv", "json"],
)

if student_file is not None:
    file_bytes = student_file.getbuffer().tobytes()
    if student_file.name.lower().endswith(".csv"):
        completed_from_upload = parse_completed_from_csv(file_bytes)
    else:
        completed_from_upload = parse_completed_from_json(file_bytes)

    if completed_from_upload:
        st.sidebar.success(f"Loaded {len(completed_from_upload)} completed courses.")
    else:
        st.sidebar.error("Could not read any course codes from that file.")

with st.sidebar.expander("Download templates"):
    st.download_button(
        "CSV template",
        data="code\nACCT1011\nECON1011\nSTAT1011\n",
        file_name="completed_courses_template.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "JSON template",
        data='["ACCT1011","ECON1011","STAT1011"]',
        file_name="completed_courses_template.json",
        mime="application/json",
        use_container_width=True,
    )


# ---------------------------
# Sidebar — 3) Preferences & constraints
# ---------------------------
st.sidebar.header("3) Preferences")

default_text = "15 credits, prefer Tu/Th, avoid Friday, no classes before 10am"
user_text = st.sidebar.text_area(
    "Describe your request in plain English:",
    value=default_text,
    height=120,
)

code_list: list[str] = []
if courses_df is not None and "code" in courses_df.columns:
    code_list = sorted(set(courses_df["code"].dropna().astype(str)))

manual_completed = st.sidebar.multiselect("Or manually pick completed courses:", code_list, default=[])
completed_codes = unique_codes((completed_from_upload or []) + manual_completed)
st.sidebar.caption(f"Total completed courses counted: {len(completed_codes)}")

st.sidebar.header("4) Constraints")
colA, colB = st.sidebar.columns(2)
min_credits = colA.number_input("Min credits", 0, 21, 12, 1)
max_credits = colB.number_input("Max credits", 0, 21, 15, 1)
include_capstone = st.sidebar.checkbox("Include Capstone (MGMT4300) if possible")
must_include = st.sidebar.multiselect("Must include these course codes:", code_list)

st.sidebar.subheader("Day/Time Preferences")
avoid_days = st.sidebar.multiselect("Avoid these days", ["Mo", "Tu", "We", "Th", "Fr"])
earliest = st.sidebar.text_input("Earliest start (e.g., 10:00)", "10:00")
latest = st.sidebar.text_input("Latest end (e.g., 18:00)", "18:00")


# ---------------------------
# Degree progress & recommendations
# ---------------------------
recommended_pool: list[str] = []
progress: dict | None = None

if courses_df is not None:
    try:
        annotated = req.annotate_courses(courses_df)
        progress = req.progress_report(completed_codes, annotated)
        missing_business_core = progress.get("business_core_missing", []) or []
        offered = set(code_list)
        recommended_pool = [c for c in missing_business_core if c in offered]
    except Exception as e:
        st.sidebar.warning(f"Could not compute degree progress: {e}")

prioritize_codes = st.sidebar.multiselect(
    "Recommended (from degree gaps): prefer these",
    sorted(recommended_pool),
    default=recommended_pool[:4] if recommended_pool else [],
)


# ---------------------------
# Profiles
# ---------------------------
st.sidebar.subheader("Profile")
profile_name = st.sidebar.text_input("Profile name", "my_profile")
colS, colL = st.sidebar.columns(2)
save_profile_btn = colS.button("💾 Save", use_container_width=True)
load_profile_btn = colL.button("📂 Load", use_container_width=True)

if save_profile_btn:
    save_profile(
        profile_name,
        {
            "user_text": user_text,
            "completed_codes": completed_codes,
            "min_credits": min_credits,
            "max_credits": max_credits,
            "include_capstone": include_capstone,
            "must_include": must_include,
            "avoid_days": avoid_days,
            "earliest": earliest,
            "latest": latest,
            "prioritize_codes": prioritize_codes,
        },
    )
    st.sidebar.success(f"Saved profile '{profile_name}' in data/")

if load_profile_btn:
    loaded = load_profile(profile_name)
    if loaded:
        st.sidebar.info("Loaded profile JSON (for now shown below).")
        st.sidebar.json(loaded)
    else:
        st.sidebar.error(f"No profile named '{profile_name}' found in data/.")


# ---------------------------
# Run
# ---------------------------
st.sidebar.markdown("---")
run = st.sidebar.button("⚙️ Build Schedule", use_container_width=True)


if run:
    if courses_df is None or sections_df is None:
        st.error("I need structured tables in data/ (`courses_from_csv.csv` and `sections_from_csv.csv`).")
        st.stop()

    # Compose rich NL text from controls so planner can parse it
    nl_extras = f", {min_credits}-{max_credits} credits"
    if include_capstone:
        nl_extras += ", include Capstone"
    if avoid_days:
        nl_extras += ", avoid " + " ".join(avoid_days)
    if earliest:
        nl_extras += f", no classes before {earliest}"
    if latest:
        nl_extras += f", finish by {latest}"
    if must_include:
        nl_extras += ", must include " + ", ".join(must_include)
    if prioritize_codes:
        nl_extras += ", prioritize " + ", ".join(prioritize_codes)

    full_text = (user_text or default_text) + nl_extras

    with st.spinner("Building your schedule..."):
        result = build_schedule(full_text, completed_codes=completed_codes)

    # ----- Output -----
    st.subheader("✅ Proposed Schedule")

    rows: list[dict[str, str]] = []
    for line in result.get("schedule", []):
        try:
            left, right = line.split("|", 1)
            code_title = left.strip()

            section, tail = [s.strip() for s in right.split("|")]
            parts = [p for p in tail.split(" ") if p.strip()]
            days = parts[0] if len(parts) > 0 else ""
            times = parts[1] if len(parts) > 1 else ""
            start, end = (times.split("-") + ["", ""])[:2]

            code = code_title.split(" - ")[0].strip()
            title = code_title.split(" - ")[1].strip() if " - " in code_title else ""

            rows.append({"Code": code, "Title": title, "Section": section, "Days": days, "Start": start, "End": end})
        except Exception:
            rows.append({"Code": "", "Title": "", "Section": "", "Days": "", "Start": "", "End": ""})
            st.write("•", line)

    if rows:
        df_sched = pd.DataFrame(rows)
        st.dataframe(df_sched, use_container_width=True)

        csv_buf = io.StringIO()
        df_sched.to_csv(csv_buf, index=False)
        st.download_button(
            "Download schedule as CSV",
            data=csv_buf.getvalue(),
            file_name="schedule.csv",
            mime="text/csv",
        )

    st.markdown(f"**Total credits:** {result.get('credits', 0)}")

    with st.expander("🧠 Why these were chosen"):
        for r in result.get("reasons", []):
            st.markdown(f"- {r}")

    pr = result.get("progress", {})
    if pr:
        st.subheader("📊 Degree Progress Snapshot")
        col1, col2, col3 = st.columns(3)

        bc_missing = pr.get("business_core_missing", [])
        col1.metric("Business Core missing", len(bc_missing))
        col2.metric("Magis Orientation unmet", len(pr.get("magis_unmet", {}).get("orientation", [])))
        col3.metric("Magis Exploration unmet", len(pr.get("magis_unmet", {}).get("exploration", [])))

        with st.expander("Details: Business Core missing"):
            st.write(sorted(bc_missing))
        with st.expander("Details: Magis Orientation unmet"):
            st.write(pr.get("magis_unmet", {}).get("orientation", []))
        with st.expander("Details: Magis Exploration unmet"):
            st.write(pr.get("magis_unmet", {}).get("exploration", []))

    st.download_button(
        "Download result as JSON",
        data=json.dumps(result, indent=2, default=json_default),
        file_name="schedule_result.json",
        mime="application/json",
    )

st.markdown("---")
st.caption("Prototype • Passcode-enabled • Upload student history • Recommend gaps • Export schedule")
