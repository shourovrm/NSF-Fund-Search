# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run one Google search per person through Serper and attach the results to the lookup files.

Usage:
    uv run faculty/serper_search.py                 # one search per person; agents see the best 3 results
    uv run faculty/serper_search.py --results 8     # agents see 8 results of each search; no new credits
    uv run faculty/serper_search.py --site-search   # a second search, of the name on the institution's own site
    uv run faculty/serper_search.py --email-search --profile-search   # two more, for people still unresolved

Reads SERPER_API_KEY from the environment or from .env in the project root.
Every answer is kept in data/faculty/cache/serper_results.jsonl, so a second
run spends credits only on people not searched yet. Each lookup_NN.jsonl entry
gains "search_results" (the pages an agent chooses from) and
"scholar_from_search" (a Google Scholar profile, when the search shows one whose
verified email domain is the person's own). The same people and results are
also written as read_NN_pKK.txt, the compact form the reading agents use with
faculty/web_read_prompt.md.

A person whose website is on record but whose department is not also gets that
website's own text as a last result, since a homepage usually names the department.

One search holds one person: with two names in a query, Google gave the second
person at most 2 of the 10 results.
"""

import argparse
import concurrent.futures
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import names
import people_store
import web_lookup
import weak_websites

SERPER_URL = "https://google.serper.dev/search"
RESULTS_CACHE_PATH = people_store.CACHE_DIR / "serper_results.jsonl"
# Serper charges a second credit above 10 results.
RESULTS_PER_SEARCH = 10
WORKER_COUNT = 8
NETWORK_TIMEOUT_SECONDS = 30
SEARCH_ATTEMPTS = 3

# The best three results settle most people. A batch of people that reading left unresolved is
# run with --results to show the agents more of the same saved search.
DEFAULT_RESULTS_PER_PERSON = 3
SNIPPET_CHARACTERS = 170
# An agent reads one reading file at a time and writes its answers before opening the next, so a long
# file of people never has to be held in mind at once. A file holds about this many results.
RESULTS_PER_READING_FILE = 120
GRANT_TITLE_CHARACTERS = 70

NAME_SEARCH = "name"
SITE_SEARCH = "site"
# The email address is printed on the person's directory page whatever first name they go by, and
# wherever NSF's institution differs from the one they write from.
EMAIL_SEARCH = "email"
# Without quotes Google matches "Mary Beth Monroe" for NSF's "Mary Monroe", which the quoted searches miss.
PROFILE_SEARCH = "profile"
# The narrower a search, the earlier its results are shown to the agents.
SEARCH_KINDS = (EMAIL_SEARCH, SITE_SEARCH, PROFILE_SEARCH, NAME_SEARCH)
# Addresses at these providers say nothing about where the person works, so there is no site to search.
PERSONAL_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com"}

WEBSITE_TEXT_CACHE_PATH = people_store.CACHE_DIR / "website_text.jsonl"
WEBSITE_ON_RECORD_LABEL = "WEBSITE ON RECORD"
WEBSITE_READ_BYTES = 1_500_000
DEPARTMENT_MENTION = re.compile(
    r"\b(Department|Dept\.?|School|College|Division|Institute|Center|Centre|Laboratory|Program) (of|for|in) ")
# How much of the page is kept before and after each mention of a department.
CHARACTERS_BEFORE_MENTION = 60
CHARACTERS_AFTER_MENTION = 110
MENTIONS_KEPT = 3
# What is kept of a page that mentions no department; its opening lines usually say who the person is.
PAGE_OPENING_CHARACTERS = 250


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


def query_for(entry, search_kind):
    """Return the Google query for this person, or None when this kind of search does not apply to them."""
    # The middle initial NSF records is rarely written on a profile page, and a quoted name must match exactly.
    short_name = f'{entry["first_name"].split()[0]} {entry["last_name"]}'
    quoted_name = f'"{short_name}"'
    if search_kind == NAME_SEARCH:
        return f'{quoted_name} {entry["institution"]}'
    if search_kind == PROFILE_SEARCH:
        return f'{short_name} {entry["institution"]} faculty profile'
    if search_kind == EMAIL_SEARCH:
        return f'"{entry["email"].lower()}"' if entry["email"] else None
    domain = web_lookup.registered_email_domain(entry)
    if not domain or domain in PERSONAL_EMAIL_DOMAINS:
        return None
    # Limited to the institution's own site, Google returns directory and profile pages, not news about the grant.
    return f"{quoted_name} site:{domain}"


def scholar_profile_among(results, entry):
    """Return the Google Scholar profile in the results that is this person's, or None.

    Google prints 'Verified email at <domain>' under a profile; requiring the
    person's own email domain there rules out namesakes at other universities.
    """
    email_domain = entry["email"].split("@")[-1].lower()
    # cs.cmu.edu and cmu.edu are the same university; Google shows the shorter one.
    registered_domain = web_lookup.registered_email_domain(entry)
    for result in results:
        link = result.get("link", "")
        if not web_lookup.host_of(link).startswith("scholar.google.") or "user=" not in link:
            continue
        title_names_person = web_lookup.page_names_person(result.get("title", ""), {**entry, "email": ""})
        if title_names_person and f"verified email at {registered_domain}" in result.get("snippet", "").lower().replace(
                email_domain, registered_domain):
            user_id = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)["user"][0]
            return f"https://scholar.google.com/citations?user={user_id}"
    return None


def results_for_agent(results, entry, results_per_person):
    """Return the few results worth an agent's attention: pages that name the person, university pages first."""
    registered_domain = web_lookup.registered_email_domain(entry)
    useful = []
    for result in results:
        link = result.get("link", "")
        if weak_websites.SHARED_SERVICE_HOSTS.search(web_lookup.host_of(link)):
            continue
        text = names.fold_accents(result.get("title", "") + " " + result.get("snippet", ""))
        shows_email = bool(entry["email"]) and entry["email"].lower() in text
        if names.fold_accents(entry["last_name"]) not in text and not shows_email:
            continue
        useful.append({"title": result.get("title", ""), "link": link,
                       "snippet": result.get("snippet", "")[:SNIPPET_CHARACTERS]})
    # A stable sort keeps Google's order within each group.
    useful.sort(key=lambda result: not web_lookup.host_of(result["link"]).endswith(registered_domain))
    return useful[:results_per_person]


def text_of_page(page_html):
    without_code = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", page_html)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", without_code))).strip()


def fetch_website_text(url):
    """Return the page's title and the parts of its text that mention a department; blanks when it cannot be read."""
    request = urllib.request.Request(url, headers=web_lookup.BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            page_html = response.read(WEBSITE_READ_BYTES).decode("utf-8", errors="ignore")
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError, OSError):
        page_html = ""
    if not DEPARTMENT_MENTION.search(text_of_page(page_html)):
        # A page built by scripts, or one that turns scripts away, shows its text only in a browser.
        page_html = web_lookup.rendered_page_text(url) or page_html
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", page_html)
    title = text_of_page(title_match.group(1)) if title_match else ""
    text = text_of_page(page_html)
    parts = []
    end_of_last_part = 0
    for mention in DEPARTMENT_MENTION.finditer(text):
        if len(parts) == MENTIONS_KEPT:
            break
        if mention.start() < end_of_last_part:
            continue
        end_of_last_part = mention.start() + CHARACTERS_AFTER_MENTION
        parts.append(text[max(0, mention.start() - CHARACTERS_BEFORE_MENTION):end_of_last_part])
    return {"title": title, "text": " ... ".join(parts) or text[:PAGE_OPENING_CHARACTERS]}


def needs_website_text(entry):
    return bool(entry["known_website"]) and not entry["known_department"]


def load_website_texts(entries):
    """Return {id: {"title", "text"}} for everyone whose website may name their department, fetching what is new."""
    website_texts = {}
    if WEBSITE_TEXT_CACHE_PATH.exists():
        website_texts = {saved["id"]: saved for saved in web_lookup.read_jsonl(WEBSITE_TEXT_CACHE_PATH)}
    pending = [entry for entry in entries if needs_website_text(entry) and entry["id"] not in website_texts]
    with open(WEBSITE_TEXT_CACHE_PATH, "a", encoding="utf-8") as cache_file:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
            fetched = executor.map(lambda entry: fetch_website_text(entry["known_website"]), pending)
            for entry, website_text in zip(pending, fetched):
                website_texts[entry["id"]] = {"id": entry["id"], **website_text}
                cache_file.write(json.dumps(website_texts[entry["id"]], ensure_ascii=False) + "\n")
    return website_texts


def website_on_record_result(entry, website_text):
    """Return the person's known website in the shape of a search result, for the agent to read a department from."""
    return {"title": f"{WEBSITE_ON_RECORD_LABEL}: {website_text['title']}", "link": entry["known_website"],
            "snippet": website_text["text"]}


def reading_text(entries):
    """Return the people and their numbered results as compact text for an agent to read."""
    blocks = []
    for entry in entries:
        lines = [f"## {entry['id']} | {entry['name']} | {entry['institution']} | {entry['email']} | grant: "
                 f"{entry['grant_title'][:GRANT_TITLE_CHARACTERS]}"]
        if entry["known_department"]:
            lines[0] += f" | department on record: {entry['known_department']}"
        for number, result in enumerate(entry["search_results"], start=1):
            lines.append(f"{number}. {result['link']} | {result['title']} | {result['snippet']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def write_reading_files(lookup_path, entries, results_per_person):
    """Split one lookup file's people into reading files; people with no usable result are left out."""
    for old_file in lookup_path.parent.glob(lookup_path.stem.replace("lookup_", "read_") + "_p*.txt"):
        old_file.unlink()
    readable_entries = [entry for entry in entries if entry["search_results"]]
    people_per_file = RESULTS_PER_READING_FILE // results_per_person
    for part_number, start in enumerate(range(0, len(readable_entries), people_per_file), start=1):
        reading_path = lookup_path.with_name(lookup_path.stem.replace("lookup_", "read_") + f"_p{part_number:02d}.txt")
        reading_path.write_text(reading_text(readable_entries[start:start + people_per_file]))


def load_cached_results(search_kind):
    """Return {id: results} for one kind of search. Lines written before the site search existed name no kind."""
    if not RESULTS_CACHE_PATH.exists():
        return {}
    return {
        saved["id"]: saved["results"] for saved in web_lookup.read_jsonl(RESULTS_CACHE_PATH)
        if saved.get("kind", NAME_SEARCH) == search_kind
    }


def run_searches(entries, search_kind, api_key):
    """Search everyone this kind of search has not covered yet and return {id: results} for all of them."""
    cached_results = load_cached_results(search_kind)
    pending = [entry for entry in entries if entry["id"] not in cached_results and query_for(entry, search_kind)]
    print(f"{search_kind} search: {len(entries)} people, {len(pending)} to search", flush=True)
    with open(RESULTS_CACHE_PATH, "a", encoding="utf-8") as cache_file:
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
            future_to_entry = {
                executor.submit(search, query_for(entry, search_kind), api_key): entry for entry in pending
            }
            for finished_count, future in enumerate(concurrent.futures.as_completed(future_to_entry), start=1):
                entry = future_to_entry[future]
                try:
                    results = future.result()
                except Exception as error:  # noqa: BLE001 - one failed search must not end the run
                    # Not cached, so the next run searches this person again.
                    print(f"failed {entry['id']} {entry['name']}: {error}", flush=True)
                    continue
                cached_results[entry["id"]] = results
                saved = {"id": entry["id"], "kind": search_kind, "results": results}
                cache_file.write(json.dumps(saved, ensure_ascii=False) + "\n")
                cache_file.flush()
                if finished_count % 500 == 0:
                    print(f"{finished_count}/{len(pending)} searched", flush=True)
    return cached_results


def without_repeated_links(results):
    seen_links = set()
    unique_results = []
    for result in results:
        if result.get("link") not in seen_links:
            seen_links.add(result.get("link"))
            unique_results.append(result)
    return unique_results


def main():
    parser = argparse.ArgumentParser(description="Attach Google search results to the lookup files.")
    parser.add_argument("--results", type=int, default=DEFAULT_RESULTS_PER_PERSON,
                        help="how many results of each person's search the agents see")
    parser.add_argument("--site-search", action="store_true",
                        help="also search each person's name on their institution's own site")
    parser.add_argument("--email-search", action="store_true", help="also search each person's email address")
    parser.add_argument("--profile-search", action="store_true",
                        help="also search the name without quotes, for people who go by another first name")
    arguments = parser.parse_args()
    requested_kinds = {NAME_SEARCH}
    for search_kind, is_requested in ((SITE_SEARCH, arguments.site_search), (EMAIL_SEARCH, arguments.email_search),
                                      (PROFILE_SEARCH, arguments.profile_search)):
        if is_requested:
            requested_kinds.add(search_kind)

    api_key = read_api_key()
    lookup_paths = sorted(web_lookup.WEB_DIR.glob("lookup_*.jsonl"))
    entries = [entry for path in lookup_paths for entry in web_lookup.read_jsonl(path)]
    # A search that was not requested is still read from the cache, so an earlier run's results are not lost.
    results_by_kind = {
        search_kind: run_searches(entries, search_kind, api_key) if search_kind in requested_kinds
        else load_cached_results(search_kind)
        for search_kind in SEARCH_KINDS
    }
    website_texts = load_website_texts(entries)

    with_results_count = 0
    with_scholar_count = 0
    for path in lookup_paths:
        file_entries = web_lookup.read_jsonl(path)
        for entry in file_entries:
            results = without_repeated_links(
                [result for search_kind in SEARCH_KINDS for result in results_by_kind[search_kind].get(entry["id"], [])])
            entry["search_results"] = results_for_agent(results, entry, arguments.results)
            if needs_website_text(entry):
                entry["search_results"].append(website_on_record_result(entry, website_texts[entry["id"]]))
            entry["scholar_from_search"] = scholar_profile_among(results, entry)
            with_results_count += bool(entry["search_results"])
            with_scholar_count += bool(entry["scholar_from_search"])
        web_lookup.write_jsonl(path, file_entries)
        write_reading_files(path, file_entries, arguments.results)
    print(f"{with_results_count} of {len(entries)} people have usable results; "
          f"{with_scholar_count} have a Scholar profile with a matching verified email")


if __name__ == "__main__":
    main()
