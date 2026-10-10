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
