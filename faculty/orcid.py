"""Find an investigator's ORCID record and read the department, job title and website links on it."""

import datetime
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import names
import roles

ORCID_API = "https://pub.orcid.org/v3.0"
NETWORK_TIMEOUT_SECONDS = 60
RETRY_COUNT = 6

# Each candidate costs one or two more requests, and a namesake list this long
# means the name is too common to settle from ORCID alone.
MAX_CANDIDATES_PER_PERSON = 5

# A degree at the investigator's own institution that is still running, or that
# ended this recently, marks a record with no job title as a student or postdoc.
RECENT_DEGREE_YEARS = 3
# ORCID entries without an end date are either running or simply undated; a
# start this recent means running.
RUNNING_DEGREE_MAX_YEARS = 8


def fetch_json(url):
    """GET a JSON document, retrying when ORCID asks for a pause."""
    for attempt in range(RETRY_COUNT):
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2 ** attempt)
    raise RuntimeError(f"gave up on {url}")


def search_people(query, rows):
    url = f"{ORCID_API}/expanded-search/?" + urllib.parse.urlencode({"q": query, "rows": rows})
    try:
        return fetch_json(url).get("expanded-result") or []
    except urllib.error.HTTPError as error:
        # ORCID answers 400 to names its query parser cannot read; that is "no result", not an outage.
        if error.code == 400:
            return []
        raise


def quote_for_search(text):
    return '"' + text.replace("\\", " ").replace('"', " ") + '"'


def search_queries(investigator):
    """Return (query, rows) pairs, narrowest first."""
    given_name = investigator["first_name"].split()[0] if investigator["first_name"].split() else ""
    family_name = quote_for_search(investigator["last_name"])
    exact_name = f"given-names:{quote_for_search(given_name)} AND family-name:{family_name}"
    queries = [(exact_name, 50)]
    # Only a narrowing hint for common names; is_same_institution makes the real decision.
    longest_token = max(names.institution_tokens(investigator["institution"]) or {""}, key=len)
    if longest_token:
        queries.insert(0, (f"{exact_name} AND affiliation-org-name:{longest_token}", 20))
        if given_name[:1].isalpha():
            # Catches short forms such as Steve for Steven.
            queries.append(
                (f"family-name:{family_name} AND given-names:{given_name[0]}* AND affiliation-org-name:{longest_token}", 30)
            )
    return queries


def affiliation_summaries(orcid_id, kind):
    """Return the record's entries of one kind: 'employment' or 'education'."""
    document = fetch_json(f"{ORCID_API}/{orcid_id}/{kind}s")
    summaries = []
    for group in document.get("affiliation-group") or []:
        for summary in group.get("summaries") or []:
            summaries.append(summary[f"{kind}-summary"])
    return summaries


def is_at_institution(summary, institution):
    organization_name = (summary.get("organization") or {}).get("name") or ""
    return names.is_same_institution(organization_name, institution)


def year_of(orcid_date):
    year = ((orcid_date or {}).get("year") or {}).get("value")
    return int(year) if year and year.isdigit() else None


def is_recent_student_here(orcid_id, institution):
    this_year = datetime.date.today().year
    for education in affiliation_summaries(orcid_id, "education"):
        if not is_at_institution(education, institution):
            continue
        end_year = year_of(education.get("end-date"))
        start_year = year_of(education.get("start-date"))
        if end_year is not None and end_year >= this_year - RECENT_DEGREE_YEARS:
            return True
        if end_year is None and start_year is not None and start_year >= this_year - RUNNING_DEGREE_MAX_YEARS:
            return True
    return False


def staff_employment_at(orcid_id, institution):
    """Return the record's job at this institution, or None when the record belongs to a student or postdoc.

    ORCID's search matches on any affiliation, including a degree in progress,
    so a namesake student at the same university passes the name and
    institution checks. Only a job here that is not a student or postdoc post counts.
    """
    employments_here = [
        employment for employment in affiliation_summaries(orcid_id, "employment")
        if is_at_institution(employment, institution)
    ]
    current_employments = [employment for employment in employments_here if not employment.get("end-date")]
    for employment in current_employments or employments_here:
        job_title = (employment.get("role-title") or "").strip()
        if roles.is_student_or_postdoc_title(job_title):
            continue
        # With no job title the degree dates are the only sign of a student record.
        if not job_title and is_recent_student_here(orcid_id, institution):
            continue
        return employment
    return None


def website_links(orcid_id):
    """Return the (label, url) pairs the person listed under 'Websites & social links'."""
    document = fetch_json(f"{ORCID_API}/{orcid_id}/researcher-urls")
    links = []
    for entry in document.get("researcher-url") or []:
        url = ((entry.get("url") or {}).get("value") or "").strip()
        if url:
            links.append(((entry.get("url-name") or "").strip(), url))
    return links


def staff_record_of(orcid_id, investigator):
    employment = staff_employment_at(orcid_id, investigator["institution"])
    if employment is None:
        return None
    return {
        "orcid": orcid_id,
        "department": (employment.get("department-name") or "").strip() or None,
        "job_title": (employment.get("role-title") or "").strip() or None,
        "is_current_job": not employment.get("end-date"),
    }


def find_staff_record(investigator):
    """Return what ORCID says about this investigator, or None when no staff record matches.

    The result holds orcid, department, job_title, is_current_job, has_namesake
    and links. has_namesake is True when a second staff record at the same
    institution carries the same name, so the first one may be the wrong person.
    """
    candidate_ids = []
    for query, rows in search_queries(investigator):
        staff_records = []
        for result in search_people(query, rows):
            orcid_id = result["orcid-id"]
            if orcid_id in candidate_ids or len(candidate_ids) >= MAX_CANDIDATES_PER_PERSON:
                continue
            if not names.is_same_given_name(result.get("given-names") or "", investigator["first_name"]):
                continue
            listed_institutions = result.get("institution-name") or []
            if not any(names.is_same_institution(name, investigator["institution"]) for name in listed_institutions):
                continue
            candidate_ids.append(orcid_id)
            staff_record = staff_record_of(orcid_id, investigator)
            if staff_record is not None:
                staff_records.append(staff_record)
        if staff_records:
            chosen_record = staff_records[0]
            chosen_record["has_namesake"] = len(staff_records) > 1
            chosen_record["links"] = website_links(chosen_record["orcid"])
            return chosen_record
    return None
