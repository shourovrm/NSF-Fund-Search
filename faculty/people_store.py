"""Read and write data/faculty/people.json: one record per NSF investigator ID."""

import json
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
FACULTY_DATA_DIR = PROJECT_DIR / "data" / "faculty"
PEOPLE_PATH = FACULTY_DATA_DIR / "people.json"
# Downloads and intermediate lookup files; rebuilt on demand and kept out of git.
CACHE_DIR = FACULTY_DATA_DIR / "cache"


def load_people():
    if not PEOPLE_PATH.exists():
        return {}
    return json.loads(PEOPLE_PATH.read_text())


def save_people(people):
    """Write through a temporary file so an interrupted run never leaves half a file."""
    FACULTY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary_path = PEOPLE_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(json.dumps(people, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(temporary_path, PEOPLE_PATH)
