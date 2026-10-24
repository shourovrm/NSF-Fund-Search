System: polaris

Values come from `~/.claude/skills/design-system/references/polaris.md` (Polaris tokens 9.4.2).
This file wins over `DESIGN.md`, which records the earlier Libre Franklin look.
Direction: the Polaris mockup the user approved on 2026-10-25 (`.design-mockups/polaris.html`).

## Type

The site uses one face, Inter, self-hosted in `site/fonts/` (variable woff2, OFL). The fallback stack is
`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif`. The root size is 16px,
and every size is a rem token in `:root`.

| Token | Desktop | Phone (<768px, one step up) | Use |
|---|---|---|---|
| `--text-caption` | 11/12 | 12/16 | count badge |
| `--text-small` | 12/16 | 14/20 | meta, hints, pills, chips, table headers |
| `--text-body` | 13/20 | 16/24 | body, inputs, buttons, list rows |
| `--text-strong` | 14/20 | 16/24 | professor name, panel title, app title |
| `--text-heading` | 20/24 | 22/28 | dialog title |

Weights: `--weight-regular` 450, `--weight-medium` 550 (labels, buttons), `--weight-semibold` 650 (names,
headings) and `--weight-bold` 700 (months-left figure). Numbers use `font-variant-numeric: tabular-nums`.

## Space

The base unit is 4px. Tokens: `--space-025` 1, `--space-050` 2, `--space-100` 4, `--space-150` 6, `--space-200` 8,
`--space-300` 12, `--space-400` 16, `--space-500` 20, `--space-600` 24 and `--space-800` 32.
Card padding is 16 and the gap between filter fields is 12. The label-to-control gap is 4.
Table cells are padded 12 by 16. Page gutter: 24 at the sides and 20 above the content.
The sidebar and the results card are 16 apart.

## Controls

- Every input, select, multi-select field and button is 32px high (`--control-height`).
- Chips are 24px. Pills are 20px. The star toggle is 32px.
- Radius: `--radius-control` 8 (inputs, buttons, chips, pills, dropdown panels) and `--radius-card` 12.
- Borders are 1px `--color-input-border`.
- Focus: `outline: 2px solid var(--color-focus); outline-offset: 1px`, applied on `:focus-visible` only.
- Native selects (PhD funding, Total funding, Sort) keep the native element, styled to the same box with a custom chevron.
- Starts from is two native selects side by side: Month (Any month, Jan to Dec) and Year (Any year, then each start year in the data). A grant matches when it starts in or after that month.
- Funding left is a segmented control with Any, 12+, 24+ and 36+ months; the selected segment is filled with `--color-fill`.
- Multi-select fields are comboboxes: the field is a text input. Typing filters the list (autosuggest), ticked options sit in a "Selected" group at the top, and the rest keep their order and groups.
- Phone tap targets: 44px minimum. Polaris states no minimum; this follows WCAG 2.5.5.

## Colour

| Token | Light | Dark | Use |
|---|---|---|---|
| `--color-bg` | #f1f1f1 | #1a1a1a | page |
| `--color-surface` | #ffffff | #303030 | cards, inputs, panels |
| `--color-surface-secondary` | #f7f7f7 | #2a2a2a | table header, chip, hover row |
| `--color-text` | #303030 | #e3e3e3 | body |
| `--color-text-secondary` | #616161 | #b5b5b5 | meta, hints |
| `--color-border` | #e3e3e3 | #4a4a4a | card edges, row dividers |
| `--color-input-border` | #8a8a8a | #8a8a8a | controls |
| `--color-link` | #005bd3 | #91c5ff | links, grant titles |
| `--color-focus` | #005bd3 | #91c5ff | focus ring |
| `--color-fill` | #303030 | #e3e3e3 | the one primary button, selected segment |
| `--color-on-fill` | #ffffff | #1a1a1a | text on fill |
| `--color-topbar` | #1a1a1a | #0f0f0f | header bar |
| `--color-topbar-input` | #474747 | #303030 | header search and header buttons |
| `--color-info-bg` / `--color-info-text` | #eaf4ff / #003a5a | #00385c / #cde5ff | CAREER pill |
| `--color-caution-bg` / `--color-caution-text` | #fff5ea / #5e4200 | #4a3a00 / #ffe9a8 | "PhD funding: possible" |
| `--color-warning-bg` / `--color-warning-text` | #fff1e3 / #5e2b00 | #5a2a0a / #ffd9b8 | "not faculty" tag |
| `--color-neutral-bg` | #ebebeb | #474747 | grant type and collaborative pills |
| `--color-star` | #b98900 | #ffd24d | saved star |

- Topic pills are outlined: a `--color-border` edge on the surface.
- "PhD funding: unlikely" is an outlined pill with `--color-text`.
- Status colours appear only on pills, never on body text.
- Dark mode is selected by `html[data-theme="dark"]`.

## Layout of the finder page

- **Header:** a 56px dark bar. The title and subtitle sit at the left, the search field (max 520px) in the centre, and My list and Dark mode at the right.
- **Body:** a grid of a 280px sidebar and a fluid results column. It fills the window with no max width; Polaris's 998px column is not used, because the table needs the width.
- **Sidebar:** one card with the title "Filters". It holds Topic, Research field, Grant type, PhD funding, State, University, Department, Starts from, Funding left, Total funding and More options, then "Clear filters" as a full-width secondary button.
- **Results card:** a top row with the count and Sort, then active-filter chips with "Clear all", then the table.
- **Table columns:** star, Professor, Lead grant, Ends, Months left, Funding.
- **Professor cell:**
  - name, plus the "not faculty" tag when it applies;
  - title · department;
  - university, state;
  - email · Website on one line.
- **Lead grant cell:**
  - title link;
  - "Started Mon YYYY";
  - pills, at most 2 topic pills and never "Other topics";
  - "N more grants".
- **Phone (<768px):**
  - The header wraps, with the search on its own row.
  - Filters sit behind a "Filters" button.
  - Rows become cards, with Ends, Months left and Funding on one line.
- **My list:** a dialog 560px wide at most, with `--radius-card`. "Show only my list" is the one primary action.

## Gates

`tests/design-gate.test.mjs` (run with `npm test`) fails on any of these:

- a `px` or `rem` value outside a `:root` block or an `@media` prelude in `site/*.css`;
- a hex or rgb colour outside a `:root` block;
- a banned word from `docs/copy.md` in `site/index.html` or in the visible strings of `site/*.js`.

Allowed outside tokens: `0`, `1px` borders, `2px` focus outlines, and `100%`/`fr`/`ch`/`vh` units.
