# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl"]
# ///
"""Download NSF award data and find PIs whose grants are still active when a
PhD student would start (Fall 2027), with field, topic and grant-type labels.

Usage:
    uv run nsf_awards.py download 2025 2026      # fetch yearly award zips
    uv run nsf_awards.py analyze                 # build data/output/*.xlsx and *.csv
    uv run nsf_awards.py site                    # build site/data.js for the web page
    uv run nsf_awards.py build                   # both of the above in one pass

Each yearly zip holds the awards NSF *made* in that calendar year (one JSON file
per award). Grants made in 2022-2024 can still be running in 2027, so download
those years too if you want wider coverage. Category rules live in taxonomy.py.
"""

import csv
import datetime
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import taxonomy

PROJECT_DIR = Path(__file__).parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = PROJECT_DIR / "data" / "output"
SITE_DIR = PROJECT_DIR / "site"

# NSF's "Download Awards by Year" page gets its signed S3 links from this endpoint.
FILE_LIST_URL = "https://api.nsf.gov/services/v2/s3/list-files"

# A grant must still be running on this date to fund a student starting Fall 2027.
FALL_2027_START = datetime.date(2027, 8, 15)

# Awards that do not pay for PhD students: company grants, startup training,
# postdoc/graduate fellowships, and event or site grants.
EXCLUDED_PROGRAM_CODES = {
    "537100", "537300", "150500", "159100", "287Y00", "286Y00", "809100",  # SBIR / STTR
    "802300", "170Y00",  # I-Corps
    "113900", "135900",  # REU / RET sites
}
EXCLUDED_INSTRUMENTS = {"Fellowship Award", "Interagency Agreement"}
# Undergraduate teaching (DUE) and K-12/informal learning (DRL) grants rarely hire
# PhD research assistants. DGE stays because it holds NRT traineeships.
EXCLUDED_DIVISIONS = {"DUE", "DRL"}
EXCLUDED_TITLE_PATTERN = re.compile(
    r"\b(conference|workshop|symposium|summer school|travel|meeting|REU site|"
    r"student support|doctoral consortium|hackathon|planning grant|I-Corps|MRI|"
    r"postdoctoral fellowship|research fellows|[A-Z]+-PF)\b",
    re.IGNORECASE,
)

# NSF solicitation prefixes removed from titles for display, e.g.
# "Collaborative Research: SaTC: CORE: Medium: Securing ..." -> "Securing ...".
DISPLAY_STRIPPED_PREFIXES = {
    "CAREER", "CRII", "ERI", "EAGER", "RAPID", "Collaborative Research", "RUI",
    "CORE", "Small", "Medium", "Large", "SaTC", "SaTC 2.0", "EDU", "TTP", "CIF", "SHF",
    "RI", "III", "HCC", "CNS Core", "CSR", "NeTS", "AF", "FET", "CPS", "FMitF", "DASS",
    "QII-TAQS", "NQVL", "EPCN", "AMPS", "ECCS", "SWIFT", "SII", "FRR", "CICI", "SCH",
    "Track 1", "Track 2", "Track 3", "Elements", "Frameworks", "Implementation", "CDS&E",
    "NSF-BSF", "NSF-SNSF", "NSF-NSERC", "GOALI", "LEAPS-MPS", "BRC-BIO", "Research Initiation",
    "Excellence in Research", "CyberTraining", "DMREF", "VINES", "CAIG", "MFAI", "RES",
}

CSV_FIELDNAMES = [
    "topics", "field", "grant_type", "phd_funding_likelihood", "phd_funding_reason",
    "collaborative", "undergraduate_institution",
    "match_detail", "title", "pi_name", "pi_email", "co_pis", "institution", "state",
    "award_date", "start_date", "end_date", "months_left_at_fall_2027", "amount_usd",
    "instrument", "directorate", "division", "nsf_programs", "program_officer",
    "program_officer_email", "award_id", "award_url",
]


def download_years(years):
    """Fetch the yearly award zips named in `years` into data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(FILE_LIST_URL) as response:
        file_listing = json.load(response)
    download_urls = {entry["fileName"]: entry["downloadUrl"] for entry in file_listing["files"]}
    for year in years:
        file_name = f"{year}.zip"
        if file_name not in download_urls:
            print(f"NSF has no file named {file_name}; skipping")
            continue
        destination = RAW_DIR / file_name
        print(f"Downloading {file_name} ...")
        urllib.request.urlretrieve(download_urls[file_name], destination)
        print(f"  saved {destination} ({destination.stat().st_size / 1e6:.1f} MB)")


def load_awards():
    """Return every award dict from every zip in data/raw/; a later file wins on duplicates."""
    awards_by_id = {}
    for zip_path in sorted(RAW_DIR.glob("*.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.namelist():
                if not member.endswith(".json"):
                    continue
                award = json.loads(archive.read(member))
                awards_by_id[award["awd_id"]] = award
    return awards_by_id.values()


def parse_date(text):
    if not text:
        return None
    return datetime.date.fromisoformat(text)


def is_research_award_funding_students(award):
    if award.get("awd_istr_txt") in EXCLUDED_INSTRUMENTS:
        return False
    if award.get("div_abbr") in EXCLUDED_DIVISIONS:
        return False
    if taxonomy.program_codes_of(award) & EXCLUDED_PROGRAM_CODES:
        return False
    title = award.get("awd_titl_txt") or ""
    if EXCLUDED_TITLE_PATTERN.search(title):
        return False
    # "Planning:" grants fund proposal preparation, not research assistants.
    if "Planning" in taxonomy.title_prefixes(title):
        return False
    return True


def is_active_at_fall_2027(award):
    end_date = parse_date(award.get("awd_exp_date"))
    return end_date is not None and end_date >= FALL_2027_START


def current_investigators(award):
    """Split the award's investigators into the lead PI and still-active co-PIs."""
    lead_pi = None
    co_pis = []
    for person in award.get("pi") or []:
        if person.get("pi_end_date"):
            continue
        if person["pi_role"] == "Principal Investigator":
            lead_pi = person
        else:
            co_pis.append(person["pi_full_name"])
    return lead_pi, co_pis


def months_between(start, end):
    return (end.year - start.year) * 12 + (end.month - start.month)


def display_title(title):
    """Drop known NSF solicitation prefixes; keep colons that belong to the project name."""
    segments = title.split(":")
    while len(segments) > 1 and segments[0].strip() in DISPLAY_STRIPPED_PREFIXES:
        segments.pop(0)
    return ":".join(segments).strip()


def build_row(award):
    """One flat record per award, shared by the spreadsheet and the website."""
    lead_pi, co_pis = current_investigators(award)
    institution = award.get("inst") or {}
    end_date = parse_date(award["awd_exp_date"])
    topic_matches = taxonomy.match_topics(award)
    phd_likelihood, phd_reason = taxonomy.phd_likelihood_of(award)
    return {
        "topics": "; ".join(taxonomy.TOPIC_LABELS[key] for key in topic_matches),
        "field": taxonomy.FIELDS[taxonomy.field_of(award)],
        "grant_type": taxonomy.GRANT_TYPES[taxonomy.grant_type_of(award)],
        "phd_funding_likelihood": taxonomy.PHD_LIKELIHOOD[phd_likelihood],
        "phd_funding_reason": phd_reason,
        "collaborative": taxonomy.is_collaborative(award),
        "undergraduate_institution": taxonomy.is_undergraduate_institution(award),
        "match_detail": " | ".join(
            f"{taxonomy.TOPIC_LABELS[key]}={match['score']} ({', '.join(match['reasons'])})"
            for key, match in topic_matches.items() if match["reasons"]
        ),
        "title": award.get("awd_titl_txt"),
        "pi_name": lead_pi["pi_full_name"] if lead_pi else "",
        "pi_email": lead_pi["pi_email_addr"] if lead_pi else "",
        "co_pis": "; ".join(co_pis),
        "institution": institution.get("inst_name"),
        "state": institution.get("inst_state_code"),
        # First award letter: when NSF made the award, which can precede the start date.
        "award_date": award.get("awd_min_amd_letter_date"),
        "start_date": award.get("awd_eff_date"),
        "end_date": award.get("awd_exp_date"),
        "months_left_at_fall_2027": months_between(FALL_2027_START, end_date),
        "amount_usd": award.get("tot_intn_awd_amt"),
        "instrument": award.get("awd_istr_txt"),
        "directorate": award.get("dir_abbr"),
        "division": award.get("div_abbr"),
        "nsf_programs": "; ".join(program["pgm_ele_name"] for program in award.get("pgm_ele") or []),
        "program_officer": award.get("po_sign_block_name"),
        "program_officer_email": award.get("po_email"),
        "award_id": award["awd_id"],
        "award_url": f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award['awd_id']}",
        # Structured copies of the labels above; kept out of the CSV columns.
        "topic_matches": topic_matches,
        "field_key": taxonomy.field_of(award),
        "grant_type_key": taxonomy.grant_type_of(award),
        "phd_key": phd_likelihood,
    }


def eligible_rows():
    """Rows for every award active on FALL_2027_START that can fund a PhD student."""
    rows = [
        build_row(award)
        for award in load_awards()
        if is_active_at_fall_2027(award) and is_research_award_funding_students(award)
    ]
    rows.sort(key=lambda row: (row["institution"] or "", row["pi_name"]))
    return rows


def summarize_pis(rows):
    """One row per lead PI: how many active grants, total dollars, latest end date."""
    pis = {}
    for row in rows:
        key = row["pi_email"].lower() or row["pi_name"]
        if key not in pis:
            pis[key] = {
                "pi_name": row["pi_name"], "pi_email": row["pi_email"],
                "institution": row["institution"], "state": row["state"],
                "award_ids": [], "topics": set(), "fields": set(), "grant_types": set(),
                "total_amount_usd": 0.0, "latest_end_date": row["end_date"],
            }
        pi = pis[key]
        pi["award_ids"].append(row["award_id"])
        pi["total_amount_usd"] += row["amount_usd"] or 0
        pi["topics"].update(row["topics"].split("; "))
        pi["fields"].add(row["field"])
        pi["grant_types"].add(row["grant_type"])
        pi["latest_end_date"] = max(pi["latest_end_date"], row["end_date"])

    summary = []
    for pi in pis.values():
        summary.append({
            "pi_name": pi["pi_name"], "pi_email": pi["pi_email"],
            "institution": pi["institution"], "state": pi["state"],
            "active_award_count": len(pi["award_ids"]),
            "has_career_award": taxonomy.GRANT_TYPES["career"] in pi["grant_types"],
            "total_amount_usd": pi["total_amount_usd"],
            "latest_end_date": pi["latest_end_date"],
            "fields": "; ".join(sorted(pi["fields"])),
            "topics": "; ".join(sorted(pi["topics"])),
            "grant_types": "; ".join(sorted(pi["grant_types"])),
            "award_ids": "; ".join(sorted(pi["award_ids"])),
        })
    summary.sort(key=lambda pi: (-pi["active_award_count"], -pi["total_amount_usd"]))
    return summary


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_sheet(workbook, sheet_name, rows, fieldnames):
    sheet = workbook.create_sheet(sheet_name[:31])
    sheet.append(fieldnames)
    for row in rows:
        sheet.append([row[field] for field in fieldnames])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def analyze(rows=None):
    from openpyxl import Workbook

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else eligible_rows()
    pi_summary = summarize_pis(rows)
    pi_fieldnames = list(pi_summary[0].keys()) if pi_summary else []

    workbook = Workbook()
    workbook.remove(workbook.active)
    write_sheet(workbook, "PI_summary", pi_summary, pi_fieldnames)
    write_csv(OUTPUT_DIR / "PI_summary.csv", pi_summary, pi_fieldnames)
    write_sheet(workbook, "All_awards", rows, CSV_FIELDNAMES)
    write_csv(OUTPUT_DIR / "All_awards.csv", rows, CSV_FIELDNAMES)
    for topic_key, topic_label in taxonomy.TOPIC_LABELS.items():
        topic_rows = [row for row in rows if topic_key in row["topic_matches"]]
        sheet_name = re.sub(r"[^A-Za-z0-9]+", "_", topic_label).strip("_")
        write_sheet(workbook, sheet_name, topic_rows, CSV_FIELDNAMES)
        write_csv(OUTPUT_DIR / f"topic_{topic_key}.csv", topic_rows, CSV_FIELDNAMES)
        print(f"{topic_label}: {len(topic_rows)} awards")
    workbook_path = OUTPUT_DIR / "nsf_active_fall2027.xlsx"
    workbook.save(workbook_path)
    print(f"{len(rows)} awards, {len(pi_summary)} distinct lead PIs -> {workbook_path}")


# The site keeps at most this many match reasons per topic; the rest is noise.
SITE_REASONS_PER_TOPIC = 3


def build_site_records(rows):
    """Group award rows under their lead PI in the compact shape the website reads."""
    records_by_pi = {}
    for row in rows:
        key = row["pi_email"].lower() or row["pi_name"]
        if key not in records_by_pi:
            records_by_pi[key] = {
                "name": row["pi_name"], "email": row["pi_email"],
                "institution": row["institution"], "state": row["state"],
                "grants": [],
            }
        full_title = row["title"] or ""
        grant = {
            "id": row["award_id"],
            "title": display_title(full_title),
            "fullTitle": full_title,
            "type": row["grant_type_key"],
            "phd": row["phd_key"],
            "collab": row["collaborative"],
            "rui": row["undergraduate_institution"],
            "field": row["field_key"],
            "topics": {key: match["reasons"][:SITE_REASONS_PER_TOPIC] for key, match in row["topic_matches"].items()},
            "start": row["start_date"],
            "end": row["end_date"],
            "monthsLeft": row["months_left_at_fall_2027"],
            "amount": row["amount_usd"],
            "division": row["division"],
            "programs": row["nsf_programs"],
            "coPis": [name for name in row["co_pis"].split("; ") if name],
        }
        # The page knows each grant type's default reason; only exceptions ship per grant.
        default_reason = taxonomy.PHD_LIKELIHOOD_BY_GRANT_TYPE[row["grant_type_key"]][1]
        if row["phd_funding_reason"] != default_reason:
            grant["phdReason"] = row["phd_funding_reason"]
        records_by_pi[key]["grants"].append(grant)
    records = list(records_by_pi.values())
    for record in records:
        record["grants"].sort(key=lambda grant: grant["end"], reverse=True)
    records.sort(key=lambda record: record["name"])
    return records


def export_site(rows=None):
    """Write site/data.js so the static page can open straight from disk."""
    SITE_DIR.mkdir(exist_ok=True)
    records = build_site_records(rows if rows is not None else eligible_rows())
    payload = {
        "generated": datetime.date.today().isoformat(),
        "sourceYears": sorted(path.stem for path in RAW_DIR.glob("*.zip")),
        "fallStart": FALL_2027_START.isoformat(),
        "fields": taxonomy.FIELDS,
        "topics": taxonomy.TOPIC_LABELS,
        "topicGroups": taxonomy.TOPIC_GROUPS,
        "grantTypes": taxonomy.GRANT_TYPES,
        "phdLikelihood": taxonomy.PHD_LIKELIHOOD,
        "grantTypePhdLikelihood": {key: value[0] for key, value in taxonomy.PHD_LIKELIHOOD_BY_GRANT_TYPE.items()},
        "grantTypePhdReasons": {key: value[1] for key, value in taxonomy.PHD_LIKELIHOOD_BY_GRANT_TYPE.items()},
        "pis": records,
    }
    # A <script> file rather than JSON: browsers block fetch() on file:// pages.
    data_path = SITE_DIR / "data.js"
    data_path.write_text("window.NSF_DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n")
    grant_count = sum(len(record["grants"]) for record in records)
    print(f"{len(records)} PIs, {grant_count} grants -> {data_path} ({data_path.stat().st_size / 1e6:.1f} MB)")


def build():
    """Spreadsheets and site data from one pass; topic matching is the slow part."""
    rows = eligible_rows()
    analyze(rows)
    export_site(rows)


def main():
    commands = {
        "download": lambda: download_years(sys.argv[2:]),
        "analyze": analyze,
        "site": export_site,
        "build": build,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(1)
    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
