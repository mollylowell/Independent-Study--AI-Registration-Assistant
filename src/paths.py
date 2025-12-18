from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

COURSES_CSV = DATA_DIR / "courses_from_csv.csv"
SECTIONS_CSV = DATA_DIR / "sections_from_csv.csv"
RAW_CSV = DATA_DIR / "Updated Analytics Request Fall 2025.csv"
