"""Web lookups for people the free sources left unresolved: choose a batch, verify the links agents return, merge.

The lookups themselves are done by agents outside this module. They read
lookup_NN.jsonl and write results_NN.jsonl (first pass) or retry_NN.jsonl
(second pass, for the people in failures_NN.jsonl) in the same directory, one JSON object per person:
    {"id", "department", "department_url", "website", "scholar", "job_title", "role", "note"}
"""

import concurrent.futures
import json
import random
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

import names
import people_store
import roles

WEB_DIR = people_store.CACHE_DIR / "web"
CHECKED_PATH = WEB_DIR / "checked.jsonl"
# The second pass runs on a costlier model, so its size is capped: failures are
# dealt evenly into this many files, one per agent.
RETRY_FILE_COUNT = 3

# Small enough that a cheap model doing its own searches finishes its file
# without losing track of the output format.
DEFAULT_PEOPLE_PER_LOOKUP_FILE = 10
# Fixed so that re-running web-batch before any merge selects the same people.
BATCH_RANDOM_SEED = 20261010

LINK_FIELDS = ("department_url", "website", "scholar")
LINK_TIMEOUT_SECONDS = 25
# The links are spread over hundreds of university sites, so no single site sees many requests at once.
LINK_WORKER_COUNT = 24
# The person's name sits near the top of a profile page; this is enough to reach it on heavy pages.
LINK_READ_BYTES = 1_500_000
# Some university sites refuse clients that do not look like a browser.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
# The site answered but will not show the page to a script, so the link is neither confirmed nor refuted.
BLOCKED_STATUS_CODES = {401, 403, 406, 429, 503, 999}

# Google Scholar and sites behind Cloudflare answer 200 with a robot check instead of the page.
ROBOT_WALL_PATTERN = re.compile(r"not a robot|captcha|just a moment\.\.\.|access denied|enable javascript", re.IGNORECASE)

# The page is gone for good; no second opinion can bring it back.
GONE_STATUS_CODES = {404, 410}

# Directory pages that fill the name in with JavaScript, and sites that reject a script with an
# ordinary-looking page, show the name only in a real browser.
BROWSER_PATH = "/usr/bin/helium-browser"
BROWSER_TIMEOUT_SECONDS = 45
# How long the page's own scripts may run, in the browser's virtual time.
BROWSER_SCRIPT_BUDGET_MILLISECONDS = 8000
# Each rendering starts a whole browser, so only a few run at once.
BROWSER_SLOTS = threading.Semaphore(4)

LINK_OK = "ok"
LINK_BLOCKED = "blocked"
# Neither a fetch nor a browser saw the name, but Google's result for this page, on the person's own
# institution's site, names the person.
LINK_NAMED_BY_SEARCH = "named_by_search"
LINK_DEAD = "dead"
LINK_WITHOUT_NAME = "no_name"
LINK_FAILURES = {LINK_DEAD, LINK_WITHOUT_NAME}
# A field is kept at these statuses; only LINK_OK earns high confidence.
LINK_ACCEPTED = {LINK_OK, LINK_BLOCKED, LINK_NAMED_BY_SEARCH}


def department_applies(record):
    """False for companies, museums and other employers without academic departments.

    Their staff write from addresses outside .edu. Research institutes with
    departments of their own, such as Woods Hole, use .edu addresses.
    """
    return record["email"].lower().endswith(".edu")


def is_unresolved(record):
    if not record["website"]:
        return True
    return department_applies(record) and not record["department"]


def host_of(url):
    return (urllib.parse.urlparse(url).hostname or "").lower()


def missing_field_rank(record):
    """Order people by what a lookup can add: both fields missing first, then the department, then the website."""
    department_missing = department_applies(record) and not record["department"]
    if department_missing and not record["website"]:
        return 0
    return 1 if department_missing else 2


def registered_email_domain(lookup_entry):
    """Return the institution's domain from the person's email: cs.cmu.edu gives cmu.edu."""
    return ".".join(lookup_entry["email"].split("@")[-1].lower().split(".")[-2:])


def read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, entries):
    with open(path, "w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_batch(investigators, batch_size, looked_up_before, people_per_file=DEFAULT_PEOPLE_PER_LOOKUP_FILE):
    """Write lookup files for batch_size unresolved people, whole universities at a time.

    Universities are drawn at random, so the batch's hit rate estimates the
    hit rate for everyone still unresolved. looked_up_before chooses between
    people no web lookup has tried yet (False) and people an earlier lookup
    left unresolved (True).
    """
    people = people_store.load_people()
    unresolved_by_institution = {}
    for nsf_id, record in people.items():
        was_looked_up = bool(record.get("web_checked"))
        if is_unresolved(record) and was_looked_up == looked_up_before and nsf_id in investigators:
            unresolved_by_institution.setdefault(record["institution"], []).append(nsf_id)
    institutions = sorted(unresolved_by_institution)
    random.Random(BATCH_RANDOM_SEED).shuffle(institutions)

    batch = []
    for institution in institutions:
        for nsf_id in sorted(unresolved_by_institution[institution]):
            if len(batch) == batch_size:
                break
            record = people[nsf_id]
            batch.append({
                "id": nsf_id,
                "name": record["name"],
                "first_name": investigators[nsf_id]["first_name"],
                "last_name": investigators[nsf_id]["last_name"],
                "email": record["email"],
                "institution": institution,
                "grant_title": investigators[nsf_id]["grant_titles"][-1],
                "known_department": record["department"],
                "known_website": record["website"],
                "known_scholar": record["scholar"],
            })
    # People missing the most come first, so the first files matter most if a run is cut short. Within
    # that, one university's people stay next to each other, so an agent reads each department site once.
    batch.sort(key=lambda entry: (missing_field_rank(people[entry["id"]]), entry["institution"], entry["name"]))

    WEB_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in list(WEB_DIR.glob("*.jsonl")) + list(WEB_DIR.glob("read_*.txt")):
        old_file.unlink()
    file_count = 0
    for start in range(0, len(batch), people_per_file):
        file_count += 1
        write_jsonl(WEB_DIR / f"lookup_{file_count:02d}.jsonl", batch[start:start + people_per_file])
    institution_count = len({entry["institution"] for entry in batch})
    print(f"{len(batch)} people at {institution_count} universities -> {file_count} files in {WEB_DIR}")


def page_names_person(page_text, lookup_entry):
    """True when the page shows the person's email address, or the family name with the given name.

    The given name is matched on its first three letters, so that 'Steve'
    confirms 'Steven', or as a lone initial, so that 'T. Brent Gunnoe' confirms
    'Thomas Gunnoe'. The email address covers nicknames such as Mike for Michael.
    """
    folded_text = names.fold_accents(page_text)
    if lookup_entry["email"] and lookup_entry["email"].lower() in folded_text:
        return True
    family_pattern = r"\b" + re.escape(names.fold_accents(lookup_entry["last_name"])) + r"\b"
    if not re.search(family_pattern, folded_text):
        return False
    given_words = names.fold_accents(lookup_entry["first_name"]).split()
    if not given_words:
        return False
    given_word = given_words[0]
    given_pattern = r"\b" + re.escape(given_word[:3]) + r"|\b" + re.escape(given_word[0]) + r"\b"
    return bool(re.search(given_pattern, folded_text))


def rendered_page_text(url):
    """Return the page as a real browser shows it after its scripts ran, or '' when the browser fails."""
    # A profile of its own for each run: browsers sharing one profile hand the page to whichever started
    # first and print nothing, and the user's own open browser must not be handed it either.
    # The browser's helper processes can still be writing when it is stopped at the timeout.
    profile = tempfile.TemporaryDirectory(prefix="faculty_browser_", ignore_cleanup_errors=True)
    with BROWSER_SLOTS, profile as profile_dir:
        command = [
            BROWSER_PATH, "--headless", "--disable-gpu", f"--user-data-dir={profile_dir}",
            f"--virtual-time-budget={BROWSER_SCRIPT_BUDGET_MILLISECONDS}", "--dump-dom", url,
        ]
        try:
            completed = subprocess.run(command, capture_output=True, timeout=BROWSER_TIMEOUT_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            return ""
    return completed.stdout.decode("utf-8", errors="ignore")


def search_names_person(url, lookup_entry):
    """True when the saved Google result for this page names the person and the page is on their institution's site."""
    if not host_of(url).endswith(registered_email_domain(lookup_entry)):
        return False
    for search_result in lookup_entry.get("search_results") or []:
        if search_result["link"] == url:
            result_text = search_result["title"] + " " + search_result["snippet"]
            return page_names_person(result_text, {**lookup_entry, "email": ""})
    return False


def second_opinion(url, lookup_entry, fetch_status):
    """Recheck a link that a plain fetch failed on: first in a browser, then against Google's result."""
    if page_names_person(rendered_page_text(url), lookup_entry):
        return LINK_OK
    if search_names_person(url, lookup_entry):
        return LINK_NAMED_BY_SEARCH
    return fetch_status


def check_link(url, lookup_entry):
    """Fetch the page and return LINK_OK, LINK_BLOCKED, LINK_NAMED_BY_SEARCH, LINK_DEAD or LINK_WITHOUT_NAME."""
    if not re.match(r"https?://", url):
        return LINK_DEAD
    request = urllib.request.Request(url, headers=BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=LINK_TIMEOUT_SECONDS) as response:
            page_text = response.read(LINK_READ_BYTES).decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as error:
        if error.code in BLOCKED_STATUS_CODES:
            return LINK_BLOCKED
        if error.code in GONE_STATUS_CODES:
            return LINK_DEAD
        return second_opinion(url, lookup_entry, LINK_DEAD)
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError, OSError):
        return second_opinion(url, lookup_entry, LINK_DEAD)
    if page_names_person(page_text, lookup_entry):
        return LINK_OK
    if ROBOT_WALL_PATTERN.search(page_text):
        return LINK_BLOCKED
    return second_opinion(url, lookup_entry, LINK_WITHOUT_NAME)


def load_lookup_entries():
    entries = {}
    for path in sorted(WEB_DIR.glob("lookup_*.jsonl")):
        for entry in read_jsonl(path):
            entries[entry["id"]] = entry
    return entries


def load_agent_results(prefix):
    results = {}
    for path in sorted(WEB_DIR.glob(f"{prefix}_*.jsonl")):
        for result in read_jsonl(path):
            results[str(result["id"])] = result
    return results


def link_of_numbered_result(lookup_entry, result_number):
    search_results = lookup_entry.get("search_results") or []
    if isinstance(result_number, int) and 1 <= result_number <= len(search_results):
        return search_results[result_number - 1]["link"]
    return None


def resolve_result_numbers(result, lookup_entry):
    """Turn an agent's picks by result number into links.

    Agents that read saved search results answer with the number of a result,
    which keeps them from retyping, and so altering, a URL.
    """
    for number_field, link_field in (("department_result", "department_url"), ("website_result", "website")):
        if number_field in result:
            result[link_field] = link_of_numbered_result(lookup_entry, result.pop(number_field))


def check_result(result, lookup_entry):
    # A Scholar profile the search step matched by name and verified email domain needs no agent to report it.
    if not result.get("scholar") and lookup_entry.get("scholar_from_search"):
        result["scholar"] = lookup_entry["scholar_from_search"]
    link_status = {}
    for field in LINK_FIELDS:
        if result.get(field):
            link_status[field] = check_link(result[field], lookup_entry)
    return link_status


def failure_reasons(result, link_status):
    if result is None:
        return ["no result returned"]
    reasons = [f"{field} {status}: {result[field]}" for field, status in link_status.items() if status in LINK_FAILURES]
    if not result.get("department") and not result.get("website"):
        reasons.append("neither department nor website found")
    return reasons


def verify_results():
    """Fetch every link in the agents' results; write checked.jsonl and, for the first pass, failures_NN.jsonl."""
    lookup_entries = load_lookup_entries()
    first_results = load_agent_results("results")
    retry_results = load_agent_results("retry")
    results = {**first_results, **retry_results}

    known_ids = [nsf_id for nsf_id in results if nsf_id in lookup_entries]
    for nsf_id in known_ids:
        resolve_result_numbers(results[nsf_id], lookup_entries[nsf_id])
    with concurrent.futures.ThreadPoolExecutor(max_workers=LINK_WORKER_COUNT) as executor:
        statuses = list(executor.map(lambda nsf_id: check_result(results[nsf_id], lookup_entries[nsf_id]), known_ids))
    link_status_by_id = dict(zip(known_ids, statuses))

    checked, failures = [], []
    for nsf_id, entry in lookup_entries.items():
        result = results.get(nsf_id)
        link_status = link_status_by_id.get(nsf_id, {})
        reasons = failure_reasons(result, link_status)
        if result is not None:
            checked.append({**result, "id": nsf_id, "link_status": link_status, "retried": nsf_id in retry_results})
        if reasons:
            failures.append({**entry, "previous_result": result, "failure_reasons": reasons})
    write_jsonl(CHECKED_PATH, checked)
    # The second pass is the last one, so its failures are final and are not queued again.
    if not retry_results:
        for file_number in range(1, RETRY_FILE_COUNT + 1):
            # Dealing in turn keeps the files within one person of each other in size.
            write_jsonl(WEB_DIR / f"failures_{file_number:02d}.jsonl", failures[file_number - 1::RETRY_FILE_COUNT])

    status_counts = {}
    for link_status in link_status_by_id.values():
        for field, status in link_status.items():
            status_counts[(field, status)] = status_counts.get((field, status), 0) + 1
    print(f"people in batch {len(lookup_entries)}, with a result {len(checked)}, retried {len(retry_results)}")
    for (field, status), count in sorted(status_counts.items()):
        print(f"  {field} {status}: {count}")
    print(f"people with a failure: {len(failures)}")


def merge_results():
    """Copy fields whose link was verified into people.json.

    A page that loads and names the person confirms the field. A page the site
    blocked, or one only Google's result vouches for, is kept at medium
    confidence. A dead page, or one without the person's name, drops the field.
    """
    people = people_store.load_people()
    accepted_counts = {"department": 0, "website": 0, "scholar": 0, "role": 0}
    checked = read_jsonl(CHECKED_PATH)
    for result in checked:
        record = people[result["id"]]
        link_status = result["link_status"]
        record["web_checked"] = True
        department_status = link_status.get("department_url")

        if result.get("department") and department_status in LINK_ACCEPTED:
            record["department"], record["source"]["department"] = result["department"], "web"
            accepted_counts["department"] += 1
            if department_status == LINK_OK:
                record["confidence"] = "high"
        # The role was read from the department page, so it needs that page confirmed, but not a new
        # department: an agent leaves the department blank when it is already on record. Where the title
        # itself settles the role, the title rule decides, so that every agent treats "Dean" or "Chair" alike.
        role = roles.role_from_job_title(result.get("job_title") or "")
        if role == roles.UNKNOWN:
            role = result.get("role")
        role_is_usable = role in (roles.FACULTY, roles.NOT_FACULTY)
        if role_is_usable and department_status == LINK_OK and record["source"].get("role") != "csrankings":
            record["role"], record["source"]["role"] = role, "web"
            record["job_title"] = result.get("job_title") or record["job_title"]
            accepted_counts["role"] += 1
        for field in ("website", "scholar"):
            if result.get(field) and not record[field] and link_status.get(field) in LINK_ACCEPTED:
                record[field], record["source"][field] = result[field], "web"
                accepted_counts[field] += 1
        if record["confidence"] is None and any(record[field] for field in ("department", "website", "scholar")):
            record["confidence"] = "medium"
    # People the lookup returned nothing for were still tried, so a later batch must not count them as new.
    for nsf_id in load_lookup_entries():
        people[nsf_id]["web_checked"] = True
    people_store.save_people(people)
    still_unresolved = sum(1 for result in checked if is_unresolved(people[result["id"]]))
    print(f"merged {len(checked)} people; fields accepted: {accepted_counts}")
    print(f"resolved by this batch: {len(checked) - still_unresolved}, still unresolved: {still_unresolved}")
