# app.py — AI Course Registration Assistant (passcode + uploads + recommendations)
# Run:
#   streamlit run app.py
# .streamlit/secrets.toml example:
#   APP_PASSWORD = "StagBotAdvisor"

import os, sys, json, io
import pandas as pd
import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---------------------------
# Resilient imports (handles 'bot (2).py' vs 'bot.py')
# ---------------------------
def _import_or_error(modname, alt_path=None):
    try:
        return __import__(modname)
    except Exception:
        if alt_path and os.path.exists(os.path.join(HERE, alt_path)):
            import importlib.util
            spec = importlib.util.spec_from_file_location(modname, os.path.join(HERE, alt_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.modules[modname] = mod
            return mod
        return None

planner = _import_or_error("planner")
parse_courses = _import_or_error("parse_courses")
req = _import_or_error("requirements")
bot = _import_or_error("bot", alt_path="bot (2).py")

def patch_planner_time_parser():
    if bot and hasattr(bot, "patch_planner_time_parser"):
        try:
            bot.patch_planner_time_parser()
        except Exception as e:
            st.warning(f"Time parser patch failed, continuing without it: {e}")

COURSES_CSV = os.path.join(HERE, "courses_from_csv.csv")
SECTIONS_CSV = os.path.join(HERE, "sections_from_csv.csv")

# ---------------------------
# Page config FIRST
# ---------------------------
st.set_page_config(page_title="AI Course Registration Assistant", page_icon="🗓️", layout="wide")

# ---------------------------
# Rerun helper
# ---------------------------
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

# ---------------------------
# Passcode gate
# ---------------------------
def login_gate():
    st.session_state.setdefault("authed", False)
    expected = st.secrets.get("APP_PASSWORD", None)

    if not expected:
        st.warning("Security note: APP_PASSWORD not found in .streamlit/secrets.toml — set it to require a passcode.")
        return

    if st.session_state["authed"]:
        left, right = st.columns([1,1])
        with left:
            st.caption("🔒 Access granted")
        with right:
            if st.button("Log out"):
                st.session_state["authed"] = False
                _rerun()
        return

    st.title("🔒 Private App")
    st.write("Enter the passcode to continue.")
    pw = st.text_input("Passcode", type="password")
    if st.button("Let me in"):
        if pw == expected:
            st.session_state["authed"] = True
            _rerun()
        else:
            st.error("Incorrect passcode.")

login_gate()
if st.secrets.get("APP_PASSWORD") and not st.session_state.get("authed", False):
    st.stop()

# ---------------------------
# Helpers for uploads / profiles
# ---------------------------
def parse_completed_from_csv(file_bytes) -> list[str]:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        col = "code" if "code" in df.columns else df.columns[0]
        return [str(c).strip() for c in df[col].dropna().astype(str)]
    except Exception:
        return []

def parse_completed_from_json(file_bytes) -> list[str]:
    try:
        data = json.loads(file_bytes.decode("utf-8"))
        if isinstance(data, list):
            return [str(x).strip() for x in data]
        if isinstance(data, dict) and "completed" in data:
            return [str(x).strip() for x in data["completed"]]
        return []
    except Exception:
        return []

def unique_codes(codes: list[str]) -> list[str]:
    seen, out = set(), []
    for c in codes:
        if c and c not in seen:
            seen.add(c); out.append(c)
    return out

def _profile_path(name: str) -> str:
    return os.path.join(HERE, f"profile_{name}.json")

def save_user_profile(name: str, data: dict):
    with open(_profile_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_user_profile(name: str):
    p = _profile_path(name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# ---------------------------
# Header & explainer
# ---------------------------
st.title("🗓️ AI Course Registration Assistant (Prototype)")
st.caption("Fairfield Dolan • Natural-language scheduling • Degree progress snapshot • Mock data ready")

with st.expander("ℹ️ How this works (click to open)"):
    st.markdown("""
**Goal:** Convert plain English preferences (e.g., *"Tu/Th only, 15 credits, avoid Friday, no classes before 10am"*) +
degree rules into a concrete, conflict-free schedule with explanations.

**Data you need:**
- Structured tables next to this file: `courses_from_csv.csv` and `sections_from_csv.csv`, **or**
- Upload the raw registrar CSV (e.g., *Updated Analytics Request Fall 2025.csv*) and I will build those tables for you.

**Included logic:**
- Dolan Business Core requirements + co-reqs
- Magis Core (Orientation & Exploration areas)
- Credit bounds, day/time conflicts, greedy fit scoring
""")

# ---------------------------
# Sidebar — 1) Course Data
# ---------------------------
st.sidebar.header("1) Course Data")
data_status = []

raw_csv_upload = st.sidebar.file_uploader("Upload *raw* registrar CSV (optional)", type=["csv"])
if st.sidebar.button("Build tables from uploaded raw CSV") and raw_csv_upload is not None:
    tmp_path = os.path.join(HERE, "Uploaded_Raw.csv")
    with open(tmp_path, "wb") as f:
        f.write(raw_csv_upload.getbuffer())
    try:
        if parse_courses and hasattr(parse_courses, "parse_courses_csv"):
            parse_courses.parse_courses_csv(tmp_path, COURSES_CSV, SECTIONS_CSV)
            st.sidebar.success("Built courses_from_csv.csv and sections_from_csv.csv from your upload.")
        else:
            st.sidebar.error("parse_courses.parse_courses_csv(...) not found in parse_courses.py")
    except Exception as e:
        st.sidebar.error(f"Failed to build structured tables: {e}")

courses_upload = st.sidebar.file_uploader("Upload courses_from_csv.csv (optional)", type=["csv"])
sections_upload = st.sidebar.file_uploader("Upload sections_from_csv.csv (optional)", type=["csv"])
if st.sidebar.button("Save uploaded tables"):
    try:
        if courses_upload:
            with open(COURSES_CSV, "wb") as f:
                f.write(courses_upload.getbuffer())
        if sections_upload:
            with open(SECTIONS_CSV, "wb") as f:
                f.write(sections_upload.getbuffer())
        st.sidebar.success("Saved table files next to app.py.")
    except Exception as e:
        st.sidebar.error(f"Saving tables failed: {e}")

courses_df, sections_df = None, None
if os.path.exists(COURSES_CSV) and os.path.exists(SECTIONS_CSV):
    try:
        courses_df = pd.read_csv(COURSES_CSV)
        sections_df = pd.read_csv(SECTIONS_CSV)
        data_status.append("✅ Structured tables loaded.")
    except Exception as e:
        data_status.append(f"❌ Failed to load structured tables: {e}")
else:
    data_status.append("ℹ️ Structured tables not found yet. Upload raw CSV or the two structured tables.")

st.sidebar.write("\n".join(data_status))

# ---------------------------
# Sidebar — 2) Student Data (completed courses)
# ---------------------------
st.sidebar.header("2) Student Data (completed courses)")
completed_from_upload = []
student_file = st.sidebar.file_uploader("Upload completed courses (CSV with 'code' column, or JSON list)", type=["csv","json"])
if student_file is not None:
    file_bytes = student_file.getbuffer().tobytes()
    if student_file.name.lower().endswith(".csv"):
        completed_from_upload = parse_completed_from_csv(file_bytes)
    else:
        completed_from_upload = parse_completed_from_json(file_bytes)
    if completed_from_upload:
        st.sidebar.success(f"Loaded {len(completed_from_upload)} completed courses from upload.")
    else:
        st.sidebar.error("Could not read any course codes from the uploaded file.")

with st.sidebar.expander("Download templates"):
    csv_example = "code\nACCT1011\nECON1011\nSTAT1011\n"
    st.download_button("CSV template (completed courses)", data=csv_example, file_name="completed_courses_template.csv", mime="text/csv")
    json_example = '["ACCT1011","ECON1011","STAT1011"]'
    st.download_button("JSON template (completed courses)", data=json_example, file_name="completed_courses_template.json", mime="application/json")

# ---------------------------
# Sidebar — 3) Preferences & Constraints
# ---------------------------
st.sidebar.header("3) Preferences")
default_text = "15 credits, prefer Tu/Th, avoid Friday, no classes before 10am"
user_text = st.sidebar.text_area("Describe your request in plain English:", value=default_text, height=120)

code_list = sorted(set(courses_df["code"].dropna().astype(str))) if (courses_df is not None and "code" in courses_df.columns) else []
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
avoid_days = st.sidebar.multiselect("Avoid these days", ["Mo","Tu","We","Th","Fr"])
earliest = st.sidebar.text_input("Earliest start (e.g., 10:00)", "10:00")
latest   = st.sidebar.text_input("Latest end (e.g., 18:00)", "18:00")

# ---------------------------
# Degree progress & recommendations (FIXED)
# ---------------------------
recommended_pool = []
missing_business_core = []
try:
    if req and hasattr(req, "progress_report") and courses_df is not None:
        annotated = req.annotate_courses(courses_df)          # <-- annotate first
        progress = req.progress_report(completed_codes, annotated)  # <-- then compute
        missing_business_core = progress.get("business_core_missing", []) or []
        offered = set(code_list)
        recommended_pool = [c for c in missing_business_core if c in offered]
except Exception as e:
    st.sidebar.warning(f"Could not compute degree progress: {e}")

prioritize_codes = st.sidebar.multiselect(
    "Recommended (from degree gaps): prefer these",
    sorted(recommended_pool),
    default=recommended_pool[:4] if recommended_pool else []
)

# ---------------------------
# Profiles
# ---------------------------
st.sidebar.subheader("Profile")
profile_name = st.sidebar.text_input("Profile name", "my_profile")
save_profile = st.sidebar.button("💾 Save profile")
load_profile = st.sidebar.button("📂 Load profile")

if save_profile:
    profile_data = {
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
    }
    save_user_profile(profile_name, profile_data)
    st.sidebar.success(f"Saved profile '{profile_name}'")

if load_profile:
    loaded = load_user_profile(profile_name)
    if loaded:
        st.sidebar.info(f"Loaded profile '{profile_name}'. Reapply values above, then click Build.")
    else:
        st.sidebar.error(f"No profile named '{profile_name}' found.")

# ---------------------------
# Run button
# ---------------------------
run = st.sidebar.button("⚙️ Build Schedule")

# ---------------------------
# RUN PLANNER
# ---------------------------
def _json_default(o):
    # JSON-safe fallback (FIXED: handles sets from planner prefs)
    if isinstance(o, set):
        return sorted(list(o))
    return str(o)

if run:
    if courses_df is None or sections_df is None:
        st.error("I need structured tables (`courses_from_csv.csv` and `sections_from_csv.csv`) to build a schedule.")
    elif planner is None or not hasattr(planner, "build_schedule"):
        st.error("planner.build_schedule(...) not found. Make sure planner.py is in this folder.")
    else:
        patch_planner_time_parser()

        # Compose rich NL text from controls so your planner can parse it
        nl_extras = f", {min_credits}-{max_credits} credits"
        if include_capstone:
            nl_extras += ", include Capstone"
        if avoid_days:
            nl_extras += ", avoid days " + "/".join(avoid_days)
        if earliest:
            nl_extras += f", no classes before {earliest}"
        if latest:
            nl_extras += f", finish by {latest}"
        if must_include:
            nl_extras += ", must include " + ", ".join(must_include)
        if prioritize_codes:
            nl_extras += ", prioritize " + ", ".join(prioritize_codes)

        full_text = (user_text or default_text) + nl_extras

        try:
            result = planner.build_schedule(full_text, completed_codes=completed_codes)
        except Exception as e:
            st.error(f"Planner crashed: {e}")
            result = None

        if result:
            st.subheader("Proposed Schedule")
            rows = []
            for line in result.get("schedule", []):
                try:
                    left, right = line.split("|", 1)
                    code_title = left.strip()
                    section, tail = [s.strip() for s in right.split("|")]
                    parts = [p for p in tail.split(" ") if p.strip()]
                    days = parts[0] if len(parts) > 0 else ""
                    times = parts[1] if len(parts) > 1 else ""
                    start, end = (times.split("-") + ["",""])[:2]
                    code = code_title.split(" - ")[0].strip()
                    title = code_title.split(" - ")[1].strip() if " - " in code_title else ""
                    rows.append({"Code": code, "Title": title, "Section": section, "Days": days, "Start": start, "End": end})
                except Exception:
                    rows.append({"Raw": line})

            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                # CSV download
                try:
                    df_sched = pd.DataFrame(rows)
                    csv_buf = io.StringIO()
                    df_sched.to_csv(csv_buf, index=False)
                    st.download_button("Download schedule as CSV", data=csv_buf.getvalue(), file_name="schedule.csv", mime="text/csv")
                except Exception:
                    pass
            else:
                st.warning("No feasible schedule found with current constraints.")

            st.markdown(f"**Total credits:** {result.get('credits', 0)}")

            with st.expander("Why these were chosen"):
                for r in result.get("reasons", []):
                    st.markdown(f"- {r}")

            pr = result.get("progress", {})
            if pr:
                st.subheader("Degree Progress Snapshot")
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

            # JSON download (FIXED default= for sets)
            st.download_button(
                "Download result as JSON",
                data=json.dumps(result, indent=2, default=_json_default),
                file_name="schedule_result.json",
                mime="application/json",
            )

st.markdown("---")
st.caption("Prototype • Passcode-enabled • Upload student history • Recommend gaps • Export schedule")
