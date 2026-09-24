# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS, no framework. The page must still open directly from disk (`file://`), so the data ships as a script file. Hosted on classic Cloudflare Pages at https://nsf-fund-search.pages.dev (the user preferred the pages.dev address), with one Pages Function (`functions/api/list.js`) and a Workers KV namespace for list sync. Everything must stay on free plans (user requirement, 2026-09-25). Code lives at github.com/shourovrm/NSF-Fund-Search (public).

## Users

One person: an international (non-US citizen) student applying to US PhD programs for Fall 2027. They are hunting for professors who hold NSF grants that will still be running when they start, so the professor can pay them as a research assistant. They use it on a laptop and on a phone.

## Product Purpose

Turn NSF's raw award data into a searchable, filterable list of professors (one entry per lead PI, grants grouped under them) across all research fields, limited to grants still active on Aug 15, 2027. Success is a shortlist of professors worth emailing, each with the evidence (grant, start and end dates, amount, type, topic match) needed to write that email.

## Positioning

Built from NSF's own award files and filtered for what matters to a funding-seeking international applicant: grant active on 2027-08-15; conferences, SBIR/STTR, I-Corps, fellowships, planning grants, REU sites and undergraduate education grants excluded; each grant labelled with how likely it is to pay a PhD research assistant (grant type plus yearly budget; traineeships marked unlikely because their stipends are mostly limited to US citizens and permanent residents).

## Operating Context

- Data source: NSF yearly award zips (currently awards made in 2025 and 2026) processed by `nsf_awards.py` with category rules in `taxonomy.py`; `uv run nsf_awards.py build` writes `data/output/*` and `site/data.js`.
- About 9,000 lead PIs and 10,000 grants; roughly 8,700 PIs are visible with default filters.
- Next steps after the site: reading lab pages and emailing professors.

## Capabilities and Constraints

- Search (name, university, grant title, NSF program).
- Filters: Topic (17 keyword topics in two groups plus "Other topics"), Research field (10, from NSF division), Grant type (8, grouped by PhD-funding likelihood), PhD funding level, collaborative-only, State (full names), University (type-ahead, scoped to state), months left, funding amount, strong topic match, My list only, include centers, include undergraduate (RUI) colleges. Centers and RUI colleges are hidden by default.
- Sort by months left (capped at 60 for ranking), newest grant, funding, name, university; column headers sort too.
- My list: star professors; saved in browser localStorage; CSV export; JSON backup and merge-import; on the hosted site, optional sync across devices keyed by a passphrase fingerprint (passphrase never sent; at least 12 characters).
- Light theme by default, dark theme on request.
- Category and PhD-likelihood matching is rule-based and imperfect. The page shows the reason only for "PhD: unlikely" grants (and in the PhD pill tooltip); topic-match evidence is in the spreadsheet column `match_detail`. The user asked (2026-09-25) not to show "Why listed" lines on the page.
- Coverage limit: grants awarded before 2025 that run past 2027 are not included until those years are downloaded.

## Brand Commitments

User-pinned: light mode; mobile friendly; news-site typography "like CNN" (sans-serif, high readability).

User chose the conventional layout (2026-09-24, over a government-notice and a news-results-desk direction): sidebar filters plus a sortable table that becomes cards on phones.

## Evidence on Hand

Real NSF data only. No invented professors, grants, or claims.

## Product Principles

1. Contactability first: every entry leads to a name, institution, email, and the grant that justifies the email.
2. Show funding runway plainly: months left at Fall 2027 matters more than total dollars.
3. Fast narrowing: filters and search respond instantly on thousands of rows.
4. Honest matching: show why a PI is in a category.

## Accessibility & Inclusion

Readable body text on phone screens, sufficient contrast in light mode, and filters usable by keyboard and touch.
