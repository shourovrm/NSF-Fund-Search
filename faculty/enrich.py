# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Find each lead investigator's department, website, Google Scholar link and role.

Usage:
    uv run faculty/enrich.py free                 # ORCID, CSRankings and email for everyone; resumable
    uv run faculty/enrich.py free-without-orcid   # records from CSRankings and email for people ORCID has not reached
    uv run faculty/enrich.py coverage             # how many records have each field
    uv run faculty/enrich.py web-batch 200        # write lookup files for 200 unresolved people, grouped by university
    uv run faculty/enrich.py web-batch 200 again  # the same, for people an earlier web lookup left unresolved
    uv run faculty/enrich.py web-batch 7000 new 350   # a third number sets how many people go in each lookup file
    uv run faculty/enrich.py web-batch 900 all 180    # everyone unresolved, looked up before or not
    uv run faculty/enrich.py web-verify           # fetch every link the web lookups returned
    uv run faculty/enrich.py web-merge            # copy the verified web results into people.json
    uv run faculty/enrich.py web-clean            # replace or remove websites that are files, news or lists of people

Results go to data/faculty/people.json, keyed by NSF investigator ID.
"""

import collections
import sys

import free_sources
import investigators
import people_store
import web_lookup
import website_cleanup


def run_free_sources():
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    free_sources.run(investigators.load_lead_investigators(), limit)
    print_coverage()


def print_coverage():
    people = people_store.load_people()
    total = len(people)
    if total == 0:
        print("people.json is empty")
        return

    def share(count):
        return f"{count} ({100 * count / total:.1f}%)"

    print(f"records: {total}")
    for field in ("department", "website", "scholar"):
        records_with_field = [record for record in people.values() if record[field]]
        by_source = collections.Counter(record["source"][field] for record in records_with_field)
        print(f"{field}: {share(len(records_with_field))}  by source: {dict(by_source.most_common())}")
    for label, counter in (
        ("role", collections.Counter(record["role"] for record in people.values())),
        ("confidence", collections.Counter(record["confidence"] or "none" for record in people.values())),
    ):
        print(f"{label}: " + ", ".join(f"{value} {share(count)}" for value, count in counter.most_common()))
    without_departments_count = sum(1 for record in people.values() if not web_lookup.department_applies(record))
    print(f"at employers without departments (email outside .edu): {share(without_departments_count)}")
    resolved_count = sum(1 for record in people.values() if not web_lookup.is_unresolved(record))
    print(f"resolved (website known, and department where one applies): {share(resolved_count)}")
    unresolved = [record for record in people.values() if web_lookup.is_unresolved(record)]
    missing_labels = ("department and website", "department only", "website only")
    by_missing_field = collections.Counter(missing_labels[web_lookup.missing_field_rank(record)] for record in unresolved)
    print(f"unresolved: {share(len(unresolved))}  missing: {dict(by_missing_field.most_common())}")


def write_web_batch():
    group = sys.argv[3] if len(sys.argv) > 3 else "new"
    looked_up_before = {"new": False, "again": True, "all": None}[group]
    people_per_file = int(sys.argv[4]) if len(sys.argv) > 4 else web_lookup.DEFAULT_PEOPLE_PER_LOOKUP_FILE
    web_lookup.write_batch(investigators.load_lead_investigators(), int(sys.argv[2]), looked_up_before, people_per_file)


def main():
    commands = {
        "free": run_free_sources,
        "free-without-orcid": lambda: free_sources.add_records_without_orcid(investigators.load_lead_investigators()),
        "coverage": print_coverage,
        "web-batch": write_web_batch,
        "web-verify": web_lookup.verify_results,
        "web-merge": web_lookup.merge_results,
        "web-clean": lambda: website_cleanup.clean_websites(investigators.load_lead_investigators()),
    }
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(1)
    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
