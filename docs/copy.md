# Copy

These rules cover the words on the finder page and in the My list dialog. They follow
`docs/design-system.md` (Polaris).

## Vocabulary

| Use | Not |
|---|---|
| professor | PI, lead PI, investigator |
| grant | award (except "NSF award page") |
| lead grant | top grant, primary award |
| my list | shortlist, favourites, saved |
| funding left | runway, months remaining |
| total funding | matching amount, matching grants |
| department | dept, unit |
| university | institution, organisation |
| topic | category, keyword |
| research field | division, directorate |
| grant type | award type, instrument |
| PhD funding | RA likelihood, phd level |
| sync | cloud, KV, server |
| passphrase | password, key, fingerprint |
| backup | JSON dump, export file |

## Rules

- A label is a noun phrase of at most three words in sentence case. It is never a question.
- A button is a verb plus its object, such as "Clear filters" or "Download backup".
- A hint is one line of at most twelve words that states an effect. Add one only when the label is not enough.
- A status line says what happened, then what the user can do next.
- An error names what failed and offers one action, with exact numbers or dates.
- Polaris copy rules also apply:
  - Use contractions.
  - Leave no end punctuation on labels or single sentences.
  - Don't say "please", "we" or "invalid".
- No exclamation marks and no jokes.
- Numbers the user can't act on stay out of the main page.

## Banned words

The gate test fails on these in visible strings: `lead PI`, `matching grants`, `runway`,
`localStorage`, `fingerprint`, `invalid`, `please`, `Default view`, `!`.

## Changes

| Before | After | Reason |
|---|---|---|
| "NSF awards 2025–2027, updated at 25 Oct 26" | "Grants active on Aug 15, 2027 · updated Oct 25, 2026" | Restores the main promise; the old date was ambiguous |
| "Covers grants NSF awarded in 2025–2027." | deleted | Repeated the header and the footer |
| Source note "awards made in 2025 and 2026 and 2027" | "NSF fiscal years 2025–2027" | The yearly NSF files are fiscal years |
| "Months left at Aug 15, 2027" | "Funding left" (segmented: Any, 12+, 24+, 36+ months) | Shorter; the date is already in the header |
| "Funding (matching grants)" | "Total funding" | Internal wording |
| "Show" / "Default view" | "More options" / "None" | Said nothing about the contents |
| "Reset all filters" | "Clear filters" | Matches "Clear all" on the chips |
| "Sort: months left" (and siblings) | label "Sort by"; options "Most months left", "Newest grant", "Most funding", "Name", "University" | Plain choices under one label |
| "Department not found" | "Department unknown" | Calmer; not an error |
| "Grant started Aug 2025" in the professor cell | "Started Aug 2025" in the grant cell | It describes the grant |
| Filters toggle "(3 on)" | "Filters (3)" | Shorter |
| Multi-select search "Search department" | field placeholder "Any department" and typing filters the list | Autosuggest replaces the separate search box |
| "Could not import this file. Choose a backup downloaded from this site. (…)" | "Couldn't import this file. Choose a backup downloaded from this site" | Contraction; the raw error detail goes to the console |
| (new) | "Starts from" label; chip "Starts Aug 2026 or later" | Start-date filter |
