"""Build one record per investigator from sources that cost nothing: ORCID, CSRankings and the email address."""

import concurrent.futures
import re
import urllib.parse

import csrankings
import orcid
import people_store
import roles

WORKER_COUNT = 6
# A crash loses at most this many finished lookups.
SAVE_EVERY = 200

# Email subdomains that name a department. School-wide ones (seas, engr, andrew) say nothing.
DEPARTMENT_BY_EMAIL_SUBDOMAIN = {
    "cs": "Computer Science",
    "cis": "Computer and Information Science",
    "csail": "Electrical Engineering and Computer Science (CSAIL)",
    "stat": "Statistics",
    "math": "Mathematics",
    "ece": "Electrical and Computer Engineering",
    "eecs": "Electrical Engineering and Computer Science",
    "cse": "Computer Science and Engineering",
}

# Profile pages on these sites are not the person's own website.
NOT_A_WEBSITE_HOSTS = re.compile(
    r"(^|\.)(linkedin|twitter|x|facebook|instagram|youtube|researchgate|academia|orcid|scopus|webofscience"
    r"|publons|clarivate|semanticscholar|dblp|mendeley|loop\.frontiersin|ncbi\.nlm\.nih|github|gitlab|bsky"
    r"|mastodon|threads|scholar\.google|arxiv|ssrn|researcherid|sciprofiles|wikipedia)\.[a-z.]+$"
)


def department_from_email(email):
    domain_parts = email.lower().split("@")[-1].split(".")
    for subdomain in domain_parts[:-2]:
        if subdomain in DEPARTMENT_BY_EMAIL_SUBDOMAIN:
            return DEPARTMENT_BY_EMAIL_SUBDOMAIN[subdomain]
    return None


def host_of(url):
    return (urllib.parse.urlparse(url if "//" in url else "//" + url).hostname or "").lower()


def with_scheme(url):
    return url if re.match(r"https?://", url, re.IGNORECASE) else "https://" + url


def scholar_link_among(links):
    for _, url in links:
        if host_of(url).startswith("scholar.google.") and "user=" in url:
            return with_scheme(url)
    return None


def website_among(links):
    """Return the first listed link that is a site of the person's own, not a profile on a shared service."""
    for _, url in links:
        host = host_of(url)
        if host and not NOT_A_WEBSITE_HOSTS.search(host):
            return with_scheme(url)
    return None


def confidence_of(orcid_record, csrankings_row, email_department):
    """Return how far the record can be trusted to describe this person: high, medium or None.

    High: CSRankings lists the person at this institution, or ORCID shows a
    current job here with a title and no namesake. Medium: the ORCID job has
    ended, has no title or has a namesake at the same institution, or the only
    evidence is the email subdomain.
    """
    if csrankings_row is not None:
        return "high"
    if orcid_record is not None:
        if orcid_record["is_current_job"] and orcid_record["job_title"] and not orcid_record["has_namesake"]:
            return "high"
        return "medium"
    if email_department:
        return "medium"
    return None


def build_record(investigator, faculty_by_family_name):
    orcid_record = orcid.find_staff_record(investigator)
    csrankings_row = csrankings.find_row(investigator, faculty_by_family_name)
    email_department = department_from_email(investigator["email"])
    orcid_links = orcid_record["links"] if orcid_record else []
    source = {}

    department = None
    if orcid_record and orcid_record["department"]:
        department, source["department"] = orcid_record["department"], "orcid"
    elif email_department:
        department, source["department"] = email_department, "email"

    website = None
    if csrankings_row and csrankings_row.get("homepage"):
        website, source["website"] = csrankings_row["homepage"], "csrankings"
    elif website_among(orcid_links):
        website, source["website"] = website_among(orcid_links), "orcid"

    scholar = None
    if csrankings_row and csrankings.scholar_link(csrankings_row):
        scholar, source["scholar"] = csrankings.scholar_link(csrankings_row), "csrankings"
    elif scholar_link_among(orcid_links):
        scholar, source["scholar"] = scholar_link_among(orcid_links), "orcid"

    job_title = orcid_record["job_title"] if orcid_record else None
    role = roles.role_from_job_title(job_title)
    if role != roles.UNKNOWN:
        source["role"] = "orcid"
    # CSRankings lists only faculty, and is kept current by the departments, so it outranks a self-typed title.
    if csrankings_row is not None:
        role, source["role"] = roles.FACULTY, "csrankings"

    return {
        "name": investigator["name"],
        "email": investigator["email"],
        "institution": investigator["institution"],
        "department": department,
        "website": website,
        "scholar": scholar,
        "role": role,
        "job_title": job_title,
        "orcid": orcid_record["orcid"] if orcid_record else None,
        "source": source,
        "confidence": confidence_of(orcid_record, csrankings_row, email_department),
    }


def save_new_records(new_records):
    """Add this run's records to people.json and return the whole file's content.

    The file is read again on every save because a web lookup may have updated
    other people's records while this run was going.
    """
    people = people_store.load_people()
    for nsf_id, record in new_records.items():
        people.setdefault(nsf_id, record)
    people_store.save_people(people)
    return people


def run(investigators, limit=None):
    """Look up every investigator not yet in people.json. Safe to stop and start again."""
    people = people_store.load_people()
    pending = [investigator for nsf_id, investigator in investigators.items() if nsf_id not in people]
    if limit is not None:
        pending = pending[:limit]
    print(f"{len(investigators)} investigators, {len(people)} already saved, {len(pending)} to look up", flush=True)
    if not pending:
        return people
    faculty_by_family_name = csrankings.load_faculty_by_family_name()
    failed_count = 0
    new_records = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
        future_to_nsf_id = {
            executor.submit(build_record, investigator, faculty_by_family_name): investigator["nsf_id"]
            for investigator in pending
        }
        for finished_count, future in enumerate(concurrent.futures.as_completed(future_to_nsf_id), start=1):
            nsf_id = future_to_nsf_id[future]
            try:
                new_records[nsf_id] = future.result()
            except orcid.DailyQuotaExceeded:
                # Everyone still waiting would fail the same way, so keep what is done and stop.
                executor.shutdown(wait=False, cancel_futures=True)
                people = save_new_records(new_records)
                print(f"ORCID's daily quota is used up; stopped with {len(people)} records saved. Run again tomorrow.",
                      flush=True)
                return people
            except Exception as error:  # noqa: BLE001 - one bad lookup must not end a two-hour run
                # Left out of people.json, so the next run tries this person again.
                failed_count += 1
                print(f"failed {nsf_id} {investigators[nsf_id]['name']}: {error}", flush=True)
            if finished_count % SAVE_EVERY == 0:
                save_new_records(new_records)
                print(f"{finished_count}/{len(pending)} looked up", flush=True)
    people = save_new_records(new_records)
    print(f"done; {failed_count} lookups failed and will be retried on the next run", flush=True)
    return people
