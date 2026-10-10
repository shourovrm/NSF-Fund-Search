# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run one Google search per person through Serper and attach the results to the lookup files.

Usage:
    uv run faculty/serper_search.py

Reads SERPER_API_KEY from the environment or from .env in the project root.
Every answer is kept in data/faculty/cache/serper_results.jsonl, so a second
run spends credits only on people not searched yet. Each lookup_NN.jsonl entry
gains "search_results" (the pages an agent chooses from) and
"scholar_from_search" (a Google Scholar profile, when the search shows one whose
verified email domain is the person's own). The same people and results are
also written as read_NN_pKK.txt, the compact form the reading agents use with
faculty/web_read_prompt.md.

One search holds one person: with two names in a query, Google gave the second
person at most 2 of the 10 results.
"""

import concurrent.futures
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import names
import people_store
import web_lookup

SERPER_URL = "https://google.serper.dev/search"
RESULTS_CACHE_PATH = people_store.CACHE_DIR / "serper_results.jsonl"
# Serper charges a second credit above 10 results.
RESULTS_PER_SEARCH = 10
WORKER_COUNT = 8
NETWORK_TIMEOUT_SECONDS = 30
SEARCH_ATTEMPTS = 3

RESULTS_PER_PERSON = 3
SNIPPET_CHARACTERS = 170
# An agent reads one of these at a time and writes its answers before opening the next,
# so a long file of people never has to be held in mind at once.
PEOPLE_PER_READING_FILE = 40
GRANT_TITLE_CHARACTERS = 70
# Pages about the person on shared services; an agent needs the person's own or the university's pages.
UNHELPFUL_HOSTS = re.compile(
    r"(^|\.)(linkedin|facebook|twitter|x|instagram|youtube|researchgate|ratemyprofessors|rocketreach|zoominfo"
    r"|academia|semanticscholar|openreview|ieeexplore\.ieee|dl\.acm|scilit|alphaxiv|arxiv|orcid|scholar\.google"
    r"|wikipedia|amazon|signalhire|contactout|expertisefinder|academictree|mathgenealogy)\.[a-z.]+$"
)


def read_api_key():
    if os.environ.get("SERPER_API_KEY"):
        return os.environ["SERPER_API_KEY"]
    env_path = people_store.PROJECT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("SERPER_API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("SERPER_API_KEY is not set in the environment or in .env")


def search(query, api_key):
    body = json.dumps({"q": query, "num": RESULTS_PER_SEARCH}).encode()
    request = urllib.request.Request(SERPER_URL, data=body, headers={"X-API-KEY": api_key, "Content-Type": "application/json"})
    for attempt in range(SEARCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
                return json.load(response).get("organic") or []
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == SEARCH_ATTEMPTS - 1:
                raise
    return []


def query_for(entry):
    # The middle initial NSF records is rarely written on a profile page, and a quoted name must match exactly.
    return f'"{entry["first_name"].split()[0]} {entry["last_name"]}" {entry["institution"]}'


def host_of(url):
    return (urllib.parse.urlparse(url).hostname or "").lower()


def scholar_profile_among(results, entry):
    """Return the Google Scholar profile in the results that is this person's, or None.

    Google prints 'Verified email at <domain>' under a profile; requiring the
    person's own email domain there rules out namesakes at other universities.
    """
    email_domain = entry["email"].split("@")[-1].lower()
    # cs.cmu.edu and cmu.edu are the same university; Google shows the shorter one.
    registered_domain = ".".join(email_domain.split(".")[-2:])
    for result in results:
        link = result.get("link", "")
        if not host_of(link).startswith("scholar.google.") or "user=" not in link:
            continue
        title_names_person = web_lookup.page_names_person(result.get("title", ""), {**entry, "email": ""})
        if title_names_person and f"verified email at {registered_domain}" in result.get("snippet", "").lower().replace(
                email_domain, registered_domain):
            user_id = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)["user"][0]
            return f"https://scholar.google.com/citations?user={user_id}"
    return None


def results_for_agent(results, entry):
    """Return the few results worth an agent's attention: pages that name the person, university pages first."""
    registered_domain = ".".join(entry["email"].split("@")[-1].lower().split(".")[-2:])
    useful = []
    for result in results:
        link = result.get("link", "")
        if UNHELPFUL_HOSTS.search(host_of(link)):
            continue
        text = result.get("title", "") + " " + result.get("snippet", "")
        if names.fold_accents(entry["last_name"]) not in names.fold_accents(text):
            continue
        useful.append({"title": result.get("title", ""), "link": link,
                       "snippet": result.get("snippet", "")[:SNIPPET_CHARACTERS]})
    # A stable sort keeps Google's order within each group.
    useful.sort(key=lambda result: not host_of(result["link"]).endswith(registered_domain))
    return useful[:RESULTS_PER_PERSON]


def reading_text(entries):
    """Return the people and their numbered results as compact text for an agent to read."""
    blocks = []
    for entry in entries:
        lines = [f"## {entry['id']} | {entry['name']} | {entry['institution']} | grant: "
                 f"{entry['grant_title'][:GRANT_TITLE_CHARACTERS]}"]
        for number, result in enumerate(entry["search_results"], start=1):
            lines.append(f"{number}. {result['link']} | {result['title']} | {result['snippet']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def write_reading_files(lookup_path, entries):
    """Split one lookup file's people into reading files; people with no usable result are left out."""
    for old_file in lookup_path.parent.glob(lookup_path.stem.replace("lookup_", "read_") + "_p*.txt"):
        old_file.unlink()
    readable_entries = [entry for entry in entries if entry["search_results"]]
    for part_number, start in enumerate(range(0, len(readable_entries), PEOPLE_PER_READING_FILE), start=1):
        reading_path = lookup_path.with_name(lookup_path.stem.replace("lookup_", "read_") + f"_p{part_number:02d}.txt")
        reading_path.write_text(reading_text(readable_entries[start:start + PEOPLE_PER_READING_FILE]))


def load_cached_results():
    if not RESULTS_CACHE_PATH.exists():
        return {}
    return {entry["id"]: entry["results"] for entry in web_lookup.read_jsonl(RESULTS_CACHE_PATH)}


def main():
    api_key = read_api_key()
    lookup_paths = sorted(web_lookup.WEB_DIR.glob("lookup_*.jsonl"))
    entries = [entry for path in lookup_paths for entry in web_lookup.read_jsonl(path)]
    cached_results = load_cached_results()
    pending = [entry for entry in entries if entry["id"] not in cached_results]
    print(f"{len(entries)} people, {len(cached_results)} searched before, {len(pending)} to search", flush=True)

    with open(RESULTS_CACHE_PATH, "a", encoding="utf-8") as cache_file:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
            future_to_entry = {executor.submit(search, query_for(entry), api_key): entry for entry in pending}
            for finished_count, future in enumerate(concurrent.futures.as_completed(future_to_entry), start=1):
                entry = future_to_entry[future]
                try:
                    results = future.result()
                except Exception as error:  # noqa: BLE001 - one failed search must not end the run
                    # Not cached, so the next run searches this person again.
                    print(f"failed {entry['id']} {entry['name']}: {error}", flush=True)
                    continue
                cached_results[entry["id"]] = results
                cache_file.write(json.dumps({"id": entry["id"], "results": results}, ensure_ascii=False) + "\n")
                cache_file.flush()
                if finished_count % 500 == 0:
                    print(f"{finished_count}/{len(pending)} searched", flush=True)

    with_results_count = 0
    with_scholar_count = 0
    for path in lookup_paths:
        file_entries = web_lookup.read_jsonl(path)
        for entry in file_entries:
            results = cached_results.get(entry["id"], [])
            entry["search_results"] = results_for_agent(results, entry)
            entry["scholar_from_search"] = scholar_profile_among(results, entry)
            with_results_count += bool(entry["search_results"])
            with_scholar_count += bool(entry["scholar_from_search"])
        web_lookup.write_jsonl(path, file_entries)
        write_reading_files(path, file_entries)
    print(f"{with_results_count} of {len(entries)} people have usable results; "
          f"{with_scholar_count} have a Scholar profile with a matching verified email")


if __name__ == "__main__":
    main()
