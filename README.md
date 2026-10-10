# NSF Fund Search

A searchable list of US professors whose NSF grants are still running on
August 15, 2027, built for choosing PhD advisors who can pay a research
assistant. Each professor shows their grants with topic, research field, grant
type, months of funding left, and how likely the grant is to fund a PhD student.

## Data

`nsf_awards.py` reads NSF's yearly award files and keeps awards that are still
active on 2027-08-15 and can fund students. It excludes conferences, workshops,
SBIR/STTR, I-Corps, fellowships, planning grants, REU sites and undergraduate
education grants. Category rules (fields, topics, grant types, PhD-funding
likelihood) live in `taxonomy.py`.

```sh
uv run nsf_awards.py download 2025 2026   # first time: fetch NSF yearly zips into data/raw/
uv run nsf_awards.py update               # later: fetch only what changed, then rebuild
uv run nsf_awards.py build                # rebuild data/output/* and site/data.js from local files
```

`update` reads only the index at the end of each NSF zip (about 0.5 MB per
year) and compares checksums with the local copy, so it downloads only the
awards that are new or changed. It falls back to a full download when most of a
file changed, and it picks up a new year file when NSF adds one. NSF re-stamps
every file daily, so file dates do not show whether anything changed;
`nsf_remote.py` holds the comparison.

The site data covers awards NSF made from 2025 on. Grants made earlier that
still run past 2027 appear only after their years are downloaded.

## Faculty details

`faculty/enrich.py` finds each lead investigator's department, website, Google
Scholar link and role, and saves one record per NSF investigator ID in
`data/faculty/people.json`. Each record names the source of every field and a
confidence: `high`, `medium` or none.

```sh
uv run faculty/enrich.py free            # ORCID, CSRankings and the email address; stop and restart at will
uv run faculty/enrich.py coverage        # how many records have each field
uv run faculty/enrich.py web-batch 200   # lookup files for 200 unresolved people, grouped by university
uv run faculty/enrich.py web-verify      # fetch every link the web lookups returned
uv run faculty/enrich.py web-merge       # copy verified web results into people.json
```

`free` costs nothing. It matches a person in ORCID by name and institution and
accepts the record only when it shows a job at that institution that is not a
student or postdoc post; ORCID's search also matches degrees in progress, which
otherwise returns namesake students. The role (`faculty`, `not faculty`,
`unknown`) comes from the ORCID job title, or from CSRankings, which lists only
faculty.

A person is unresolved while the department or the website is missing.
`web-batch` writes `data/faculty/cache/web/lookup_NN.jsonl` for agents to
research; they write `results_NN.jsonl` beside it. `web-verify` fetches each
returned link and checks that the page names the person, and lists the people
whose links failed, dealt evenly into three `failures_NN.jsonl` files, for one
second pass (`retry_NN.jsonl`).
The lookups can also run through the pi agent with a cheap model and Tavily
search: `TAVILY_API_KEY=... uv run faculty/pi_lookup.py` runs every lookup file
that has no results yet, using the instructions in `faculty/web_lookup_prompt.md`.
`web-batch 200 again` queues people an earlier lookup left unresolved.

For thousands of people, one Google search per person through Serper is cheaper
than agents that search for themselves. `web-batch 7000 new 350` writes large
lookup files, then `uv run faculty/serper_search.py` (it reads `SERPER_API_KEY`
from the environment or `.env`) attaches each person's search results to the
lookup files and writes them again as `read_NN_pKK.txt`. Agents read those with
the instructions in `faculty/web_read_prompt.md` and answer with the number of
a result, never a retyped link; `web-verify` and `web-merge` then run as
before. Every search is kept in `data/faculty/cache/serper_results.jsonl`, so a
person is paid for once.

`free-without-orcid` builds records from CSRankings and the email address for
people ORCID has not been asked about, for days when ORCID's quota is spent; a
later `free` run asks ORCID about them and fills in what it knows.

`web-merge` keeps a field only when its page loaded and named the person
(`high`) or the site refused scripts (`medium`); Google Scholar always refuses.

## Update reminder

`reminder/install.sh` installs a systemd user timer that runs
`reminder/update_reminder.py` 10 minutes after each login. The script stays
silent when the data was updated within the last 7 days or when NSF has nothing
new. Otherwise it shows one desktop notification, for example "No update since
25 Sep 26. Update found: 520 awards." Then run `update` and `npm run deploy`.
`reminder/install.sh --uninstall` removes it.

## Site

Live at <https://nsf-fund-search.pages.dev> (Cloudflare Pages, free plan).

`site/index.html` is a static page that also opens straight from disk. The
saved list ("My list") lives in the browser, can be exported as CSV or as a
JSON backup, and on the hosted site can sync across devices: the browser stores
the list under a SHA-256 fingerprint of a passphrase the user picks, through
`functions/api/list.js` and a Workers KV namespace. `PRODUCT.md` and
`DESIGN.md` record the product scope and the design system.

```sh
npm install        # installs the pinned wrangler
npm run dev        # site + sync API on http://localhost:8788 (local KV)
npm run deploy     # publish site/ and functions/ to Cloudflare Pages
```

Source data: [NSF Award Search](https://www.nsf.gov/awardsearch/), public
domain US government data.
