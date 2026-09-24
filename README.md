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
uv run nsf_awards.py download 2025 2026   # fetch NSF yearly zips into data/raw/
uv run nsf_awards.py build                # write data/output/* and site/data.js
```

The site data currently covers awards NSF made in 2025 and 2026. Grants made
earlier that still run past 2027 appear only after their years are downloaded.

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
