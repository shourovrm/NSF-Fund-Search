"""Look a person up in the CSRankings faculty list, which gives a homepage and a Google Scholar ID.

CSRankings lists only faculty who can advise a computer science PhD student,
so a match also says the person is faculty.
"""

import csv
import re
import string
import urllib.error
import urllib.request

import names
from people_store import CACHE_DIR

CSRANKINGS_DIR = CACHE_DIR / "csrankings"
CSRANKINGS_URL = "https://raw.githubusercontent.com/emeryberger/CSrankings/gh-pages/csrankings-{letter}.csv"
# CSRankings writes this where a person has no Google Scholar profile.
NO_SCHOLAR_PAGE = "NOSCHOLARPAGE"
# GitHub serves these files from several addresses and one of them can be
# unreachable, so a short timeout and another attempt beats a long wait.
NETWORK_TIMEOUT_SECONDS = 10
DOWNLOAD_ATTEMPTS = 5


def download(url):
    for _ in range(DOWNLOAD_ATTEMPTS - 1):
        try:
            with urllib.request.urlopen(url, timeout=NETWORK_TIMEOUT_SECONDS) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
    with urllib.request.urlopen(url, timeout=NETWORK_TIMEOUT_SECONDS) as response:
        return response.read()


def download_missing_files():
    CSRANKINGS_DIR.mkdir(parents=True, exist_ok=True)
    for letter in string.ascii_lowercase:
        destination = CSRANKINGS_DIR / f"csrankings-{letter}.csv"
        if not destination.exists():
            destination.write_bytes(download(CSRANKINGS_URL.format(letter=letter)))


def load_faculty_by_family_name():
    """Return CSRankings rows grouped by lower-cased family name."""
    download_missing_files()
    faculty_by_family_name = {}
    for csv_path in sorted(CSRANKINGS_DIR.glob("csrankings-*.csv")):
        with open(csv_path, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                # CSRankings appends a DBLP number to tell namesakes apart, e.g. "Wei Zhang 0001".
                clean_name = re.sub(r"\s+\d{4}$", "", row["name"]).strip()
                if not clean_name:
                    continue
                row["clean_name"] = clean_name
                family_name = names.fold_accents(clean_name.split()[-1])
                faculty_by_family_name.setdefault(family_name, []).append(row)
    return faculty_by_family_name


def find_row(investigator, faculty_by_family_name):
    for row in faculty_by_family_name.get(names.fold_accents(investigator["last_name"]), []):
        if not names.is_same_given_name(row["clean_name"].split()[0], investigator["first_name"]):
            continue
        if names.is_same_institution(row["affiliation"], investigator["institution"]):
            return row
    return None


def scholar_link(row):
    scholar_id = (row.get("scholarid") or "").strip()
    if not scholar_id or scholar_id == NO_SCHOLAR_PAGE:
        return None
    return f"https://scholar.google.com/citations?user={scholar_id}"
