"""Replace or remove stored websites that are not the person's own page.

A weak link (see weak_websites.py) often sits below the page that was wanted:
a CV at example.edu/~smith/cv.pdf sits below the homepage example.edu/~smith/.
Such a link is replaced by the page above it; one with no such page is removed,
so that the next web lookup searches for the person's website again.
"""

import concurrent.futures
import json
import re
import socket
import urllib.error
import urllib.request

import names
import people_store
import web_lookup
import weak_websites

LOG_PATH = people_store.CACHE_DIR / "website_cleanup.jsonl"
DEAD_LINK = "dead link"
# ORCID and CSRankings links were entered by the person or a colleague, some of them years ago, and no
# lookup has fetched them. Links found by the web lookup were fetched when they were accepted.
UNFETCHED_SOURCES = {"orcid", "csrankings"}
# A lab's front page is titled "Smith Lab" or "Smith Research Group", without the given name.
GROUP_TITLE = re.compile(r"\b(lab|laboratory|group|research)\b", re.IGNORECASE)


def page_title_and_text(url):
    request = urllib.request.Request(url, headers=web_lookup.BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=web_lookup.LINK_TIMEOUT_SECONDS) as response:
            page_html = response.read(web_lookup.LINK_READ_BYTES).decode("utf-8", errors="ignore")
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError, OSError):
        return "", ""
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", page_html)
    return (title_match.group(1) if title_match else ""), page_html


def title_names_person(title, lookup_entry):
    if web_lookup.page_names_person(title, {**lookup_entry, "email": ""}):
        return True
    family_name = r"\b" + re.escape(names.fold_accents(lookup_entry["last_name"])) + r"\b"
    return bool(re.search(family_name, names.fold_accents(title)) and GROUP_TITLE.search(title))


def page_above(url, lookup_entry):
    """Return the shortest page above this link that is the person's own, or None."""
    for shorter_url in weak_websites.shorter_urls(url):
        if weak_websites.weakness(shorter_url, lookup_entry):
            continue
        title, page_text = page_title_and_text(shorter_url)
        if not web_lookup.page_names_person(page_text, lookup_entry):
            continue
        if weak_websites.url_names_person(shorter_url, lookup_entry) or title_names_person(title, lookup_entry):
            return shorter_url
    return None


def is_gone(url):
    """True when the page answers 404 or 410, or its host no longer exists.

    A refused connection, a timeout or a bad certificate says nothing: many
    working university servers answer a script that way.
    """
    request = urllib.request.Request(url, headers=web_lookup.BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=web_lookup.LINK_TIMEOUT_SECONDS):
            return False
    except urllib.error.HTTPError as error:
        return error.code in web_lookup.GONE_STATUS_CODES
    except urllib.error.URLError as error:
        return isinstance(error.reason, socket.gaierror)
    except (TimeoutError, ConnectionError, ValueError, OSError):
        return False


def judge_website(record, lookup_entry):
    """Return (reason, replacement) for a website that must change, or (None, None) to keep it."""
    reason = weak_websites.weakness(record["website"], lookup_entry)
    if reason:
        return reason, page_above(record["website"], lookup_entry)
    if record["source"].get("website") in UNFETCHED_SOURCES and is_gone(record["website"]):
        return DEAD_LINK, None
    return None, None


def clean_websites(investigators):
    people = people_store.load_people()
    lookup_entries = {
        nsf_id: {**investigators[nsf_id], "email": record["email"]}
        for nsf_id, record in people.items() if record["website"] and nsf_id in investigators
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=web_lookup.LINK_WORKER_COUNT) as executor:
        judgements = list(executor.map(
            lambda nsf_id: judge_website(people[nsf_id], lookup_entries[nsf_id]), lookup_entries))

    reason_counts = {}
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        for nsf_id, (reason, replacement) in zip(lookup_entries, judgements):
            if reason is None:
                continue
            record = people[nsf_id]
            change = "replaced" if replacement else "removed"
            reason_counts[(reason, change)] = reason_counts.get((reason, change), 0) + 1
            log_file.write(json.dumps({"id": nsf_id, "name": record["name"], "reason": reason,
                                       "old_website": record["website"], "new_website": replacement}) + "\n")
            record["website"] = replacement
            if replacement is None:
                del record["source"]["website"]
    people_store.save_people(people)
    for (reason, change), count in sorted(reason_counts.items()):
        print(f"{reason}, {change}: {count}")
    print(f"log: {LOG_PATH}")
