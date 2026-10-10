---
name: NSF Professor Finder
description: Sidebar filters and a sortable table of professors whose NSF grants run past Aug 15, 2027; light by default, dark on request.
colors:
  accent: "#1d4ed8"
  accent-wash: "#eaf0fd"
  on-accent: "#ffffff"
  career: "#b42318"
  career-wash: "#fde8e7"
  star: "#b7791f"
  star-border: "#e7c27d"
  star-wash: "#fff8e8"
  star-ink: "#8a5a12"
  likely: "#166534"
  likely-wash: "#e3f4e8"
  possible: "#6b21a8"
  possible-wash: "#f3e8ff"
  success: "#166534"
  bg: "#f6f7f9"
  surface: "#ffffff"
  surface-sunken: "#fafbfc"
  row-hover: "#fbfcfe"
  ink: "#14171c"
  ink-soft: "#454b55"
  ink-faint: "#6b7280"
  line: "#e3e6eb"
  control-border: "#c9ced6"
  pill: "#eef0f3"
typography:
  display:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 800
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    lineHeight: 1.5
  title:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.5
  figure:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 800
    lineHeight: 1.5
    fontFeature: "tnum"
  body:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  body-dense:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 400
    lineHeight: 1.5
  meta:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.92rem"
    fontWeight: 600
  label:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    letterSpacing: "0.05em"
  pill:
    fontFamily: "Libre Franklin, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.74rem"
    fontWeight: 600
rounded:
  control: "8px"
  panel: "10px"
  dialog: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  panel: "18px"
  lg: "24px"
components:
  button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  icon-button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
    height: "42px"
  count-badge:
    backgroundColor: "{colors.star-wash}"
    textColor: "{colors.star-ink}"
    rounded: "{rounded.pill}"
    padding: "0 7px"
  input-search:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "11px 14px"
  input-search-focus:
    backgroundColor: "{colors.surface}"
  select:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 10px"
  pill:
    backgroundColor: "{colors.pill}"
    textColor: "{colors.ink-soft}"
    typography: "{typography.pill}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  pill-topic:
    backgroundColor: "{colors.accent-wash}"
    textColor: "{colors.accent}"
    typography: "{typography.pill}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  pill-career:
    backgroundColor: "{colors.career-wash}"
    textColor: "{colors.career}"
    typography: "{typography.pill}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  pill-phd-maybe:
    backgroundColor: "{colors.possible-wash}"
    textColor: "{colors.possible}"
    typography: "{typography.pill}"
    rounded: "{rounded.pill}"
    padding: "2px 8px"
  pill-phd-unlikely:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.pill}"
    rounded: "{rounded.pill}"
    padding: "1px 7px"
  filter-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "4px 6px 4px 10px"
  star-toggle:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-faint}"
    rounded: "{rounded.control}"
    size: "40px"
  star-toggle-saved:
    backgroundColor: "{colors.star-wash}"
    textColor: "{colors.star}"
    rounded: "{rounded.control}"
    size: "40px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "16px 18px 18px"
  multi-select:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.control}"
    padding: "9px 10px"
  multi-select-has-value:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.accent}"
    rounded: "{rounded.control}"
    padding: "9px 10px"
  multi-select-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.control}"
  table-header:
    backgroundColor: "{colors.surface-sunken}"
    textColor: "{colors.ink-faint}"
    typography: "{typography.label}"
    padding: "10px 14px"
  table-header-sorted:
    textColor: "{colors.accent}"
  dialog:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.dialog}"
    width: "min(480px, calc(100vw - 32px))"
---

# Design System: NSF Professor Finder

## Overview

**Creative North Star: "The Clean Results Desk"**

The page is the category-standard research tool: a filter panel on the left, a sortable results table on the right, both set on white rounded panels over a pale grey ground (`bg`). The user chose this conventional layout over two own-world directions, so the system's job is execution quality, not novelty: hairline rules, one blue accent, colored pills that each carry one fixed meaning, and a single news-sans family (Libre Franklin) whose weights carry the hierarchy.

Density is high and deliberate. The table shows roughly 8,700 professors, so rows are separated by 1px lines rather than cards, numbers use tabular figures and right alignment, and every metadata line drops to a smaller size and a fainter ink instead of adding boxes. The filter panel and the table header both stay pinned while the results scroll, so narrowing and sorting are always one click away.

Light is the default theme and the one the user pinned. Dark is opt-in through `:root[data-theme="dark"]`, which re-tunes every role token (surfaces, inks, accent, pill hues) to hold 4.5:1 text contrast; no component rule branches on theme except the theme toggle swapping its moon and sun icons. The dark values live in the sidecar under `extensions.themes.dark`.

**Key Characteristics:**
- Grey ground, white panels with 10px corners and 1px hairline borders; no shadows except the My list dialog and an open dropdown panel.
- One blue accent for everything interactive or selected.
- Fixed-meaning hues: red is CAREER, amber is saved, green, purple and an outline mark PhD likelihood.
- Libre Franklin only, weights 400 to 800, tabular figures everywhere.
- Sticky, independently scrolling filter panel and sticky sortable table header on desktop; table becomes labelled cards at 900px and below.

## Colors

The palette is cool neutral greys with one saturated blue and four reserved signal hues, each paired with a pale "wash" background of the same hue.

### Primary
- **Newsroom Blue** (`accent`): links, grant titles, topic pills, the active sort header and its caret, the label and border of a filter dropdown that has a selection, the border of an open dropdown, checkbox fill, the dropdown "Clear" and "Done" actions, the primary dialog button, the "Show more" bar text, and the 3px focus ring. **Blue Wash** (`accent-wash`) backs topic pills and the 3px halo around the focused search field and the open dropdown button.

### Secondary
- **CAREER Red** (`career`, on `career-wash`): the CAREER grant-type pill, plus the error line in the My list dialog. No other use.
- **Saved Amber** (`star`, `star-border`, `star-wash`, `star-ink`): the pressed star toggle and the count badge on the My list button. `star-ink` is the darker amber used for badge text so the number stays legible.

### Tertiary
- **PhD Green** (`likely`, on `likely-wash`): no pill uses it since grants that usually fund PhD students carry none; `success` shares this value and colors the dialog's success status line.
- **PhD Purple** (`possible`, on `possible-wash`): the "PhD funding: possible" pill.

### Neutral
- **Ground Grey** (`bg`): page background and the resting fill of the header search field.
- **Panel White** (`surface`): header bar, filter panel, results card, dialog, buttons, chips, star toggles.
- **Sunken White** (`surface-sunken`): table header row, active-filter chip strip, "Show more" bar, the search strip and footer inside a dropdown panel.
- **Row Hover** (`row-hover`): whole-row hover wash on hover-capable devices only.
- **Ink** (`ink`): primary text, professor names, button text, the outlined "PhD funding: unlikely" pill text.
- **Soft Ink** (`ink-soft`): institutions, the grant start line, the coverage note, dialog prose, neutral pill text, and the placeholder value of an empty filter dropdown.
- **Faint Ink** (`ink-faint`): uppercase field and column labels, group labels inside a dropdown, counts beside filter options, field hints, the PhD caveat line, placeholders, the inline number labels on phones, and the hover border of controls.
- **Hairline** (`line`): every divider and panel border.
- **Control Border** (`control-border`): 1px border on buttons, inputs, selects, dropdown buttons and panels, chips and star toggles; the thin scrollbar thumb of the filter panel and the dropdown option list.
- **Tag Grey** (`pill`): fill of neutral pills (grant types other than CAREER, "Collaborative", "Other topics", "+N topics").

### Named Rules
**The One Blue Rule.** Blue means "you can act on this" or "this is selected". No second accent exists; any new interactive element uses `accent`.

**The Reserved Hue Rule.** Red is CAREER (and error text), amber is saved, green is PhD likely, purple is PhD maybe. None of these hues appears for decoration or for any other category.

**The Role Token Rule.** Components reference role tokens (`--ink`, `--surface`, `--accent`), never literal colors, so the dark block re-tunes the whole page by redefining the tokens alone.

## Typography

**Display Font:** Libre Franklin (with Helvetica Neue, Arial, sans-serif)
**Body Font:** Libre Franklin (same stack)

**Character:** One self-hosted Franklin Gothic revival, the news-sans the user asked for ("like CNN"), used at weights 400, 500, 600, 700 and 800. Hierarchy comes from weight and size steps, not from a second family.

### Hierarchy
- **Display** (800, 1.25rem, letter-spacing -0.01em): the app title in the header. The only display-scale text.
- **Headline** (700, 1.1rem): the My list dialog heading.
- **Title** (700, 1rem): professor names in table rows and cards.
- **Figure** (800, 1.05rem, tabular): months left; the unit "mo" follows at body weight.
- **Body** (400, 16px, line-height 1.5, tabular figures): base text; table cells step down to 0.95rem (`body-dense`), grant titles at 500.
- **Meta** (400, 0.82 to 0.9rem): institution (0.9rem), emails and the grant start line (0.85rem), the PhD caveat, sub-grant lines and field hints (0.82rem). Source notes cap at 90ch.
- **Control** (600, 0.92rem): buttons, icon buttons; inputs, selects and dropdown buttons use 500 at 0.92 to 1rem, and a dropdown with a selection steps up to 600.
- **Label** (700, 0.8rem, letter-spacing 0.05em, uppercase): filter field labels; table column headers use 0.78rem at 0.04em. Group labels inside a dropdown panel are 700, 0.76rem, sentence case.
- **Pill** (600, 0.74rem): all pills; filter chips use 600 at 0.82rem.

### Named Rules
**The Tabular Figures Rule.** `font-variant-numeric: tabular-nums` is set on the body, and numeric columns (Ends, Months left, Funding) are right-aligned and never wrap, so digits line up down 8,700 rows.

**The One Family Rule.** Libre Franklin sets every glyph on the page. Weight, size and ink shade do the work a second family would do.

## Layout

The page is a centered 1360px max-width container. The header bar spans full width with a hairline bottom border and holds title, a flexible search field (min 240px) and two icon buttons in one wrapping row, 16px 24px padding. Below it, a two-column grid places a 300px filter panel beside a fluid results column, with 24px padding and 24px gap.

The filter panel is sticky at `top: 16px`, capped at `calc(100vh - 32px)`, and scrolls on its own with contained overscroll and a thin scrollbar, so every filter stays reachable beside a long table. Each filter is a labelled field, 14px apart: multi-choice filters are multi-select dropdowns, threshold filters are native selects. The results card clips its overflow (not `hidden`) so the table header row stays sticky at `top: 0` while the page scrolls.

Spacing uses a small, observed set: 4px and 6px inside pill and chip rows, 8px between controls, 14px table-cell padding, 18px horizontal inset inside the results card, 24px between the major columns.

At 900px and below: the grid collapses to one column with 16px padding; the search field wraps to its own full-width row; icon buttons drop their text labels; the filter panel becomes a static card whose body is hidden behind a full-width "Filters (N on)" toggle; the table header is hidden and each row becomes a block card (12px 16px padding) with the star toggle pinned top right and the three numbers inline, each prefixed by its own faint label ("Ends", "Left", "Funding") from `data-label`.

### Named Rules
**The Always-Reachable Rule.** On desktop the filters and the column headers never scroll out of view; the filter panel scrolls independently when it is taller than the viewport.

**The Self-Labelled Number Rule.** When the header row is hidden on phones, every number carries its own label inline.

## Elevation & Depth

The system is flat. Depth comes from tone (grey ground, white panels, near-white sunken strips) and 1px hairline borders. Two transient surfaces lift, both with the same `--shadow` token: the My list modal dialog, over a 45% dark backdrop, and an open filter dropdown panel.

### Shadow Vocabulary
- **Transient lift** (`box-shadow: 0 8px 24px rgba(20, 23, 28, 0.08)`; dark theme `rgba(0, 0, 0, 0.4)`): the My list dialog and an open dropdown panel.
- **Focus halo** (`box-shadow: 0 0 0 3px` in `accent-wash`): the header search field on focus, replacing the outline, and a dropdown button while its panel is open.

### Named Rules
**The Flat Panels Rule.** Panels, rows, cards and buttons carry no shadow. Separation is a hairline or a tone step; only a transient layer (the modal dialog, an open dropdown panel) lifts.

## Shapes

Corners come in four fixed steps: 8px for controls (buttons, inputs, selects, dropdown buttons and their panels, star toggles), 10px for panels (filter panel, results card), 12px for the dialog, and fully rounded (999px) for pills, chips and the count badge. Borders are 1px throughout; and the additional-grants list uses a 2px left rule. Icons are inline stroke SVGs (2px stroke, round caps) at 14 to 18px. The active sort direction is a small CSS triangle in `currentColor`.

## Components

### Buttons
- **Shape:** gently rounded (8px), 1px `control-border`.
- **Default:** white surface, ink text, 600 at 0.92rem, 10px 12px padding.
- **Primary:** blue fill and border with `on-accent` text; used once, for "Show only my list" in the dialog.
- **Hover / Focus:** border darkens to `ink-faint`; keyboard focus draws the global 3px blue outline at 2px offset.
- **Icon button:** same shape with an 18px SVG and text label, 42px min height; the label hides at 900px and below. The My list button carries an amber count badge.
- **Text actions:** "Clear all" is an underlined blue text button; "Show more" is a full-width sunken bar with blue 600 text.

### Chips
- **Pills (read-only tags):** fully rounded, 0.74rem 600, 2px 8px. Neutral grey for grant types and "Collaborative"; blue wash for matched topics (selected topics sort first); red wash for CAREER; no PhD pill on grants that usually fund PhD students; purple wash for "PhD funding: possible"; transparent with a 1px `ink-faint` outline and full ink for "PhD funding: unlikely".
- **Active-filter chips:** white, 1px `control-border`, 0.82rem 600, a 14px close icon in faint ink; they sit in a sunken strip under the coverage note and remove their filter on click. The strip disappears when empty.

### Cards / Containers
- **Corner Style:** 10px panels, 12px dialog.
- **Background:** `surface` over `bg`.
- **Shadow Strategy:** none (see Flat Panels Rule).
- **Border:** 1px `line`.
- **Internal Padding:** 18px horizontal in the results card and filter panel; 14px table cells; 12px 16px per row-card on phones.

### Inputs / Fields
- **Search:** ground-grey fill, 1px `control-border`, 8px corners, 500 at 1rem, 11px 14px padding. On focus the fill turns white, the border turns blue and a 3px blue-wash halo replaces the outline.
- **Selects:** white fill, same border and radius, 500 at 0.95rem, 9px 10px.
- **Checkboxes:** native, 17px, `accent-color` blue; the option's result count sits right-aligned in faint ink.

### Navigation
- **Multi-select dropdown** (Topic, Research field, Grant type, State, University, Show): a select-styled button in soft ink showing its placeholder ("Any topic", "All states", "Default view"), the one chosen label, or "N selected"; once anything is chosen the label turns blue at 600 with a blue border. While open, the button takes a blue border and the 3px blue-wash halo, and its 16px chevron rotates 180 degrees over 160ms ease-out (disabled under reduced motion). The panel opens in place 6px below the button (never as an overlay, so the scrolling sidebar cannot clip it), with 8px corners, a `control-border` edge and the transient lift shadow: optional search field on a sunken strip, a checkbox list capped at 300px with sentence-case group labels and faint counts, and a footer with "Clear" and "Done". One dropdown is open at a time; outside click and Escape close it.
- **Sortable headers:** column-header buttons inherit the uppercase label style; hover shifts them to full ink; the active sort turns blue with a direction caret and sets `aria-sort`.

### Professor Row (signature)
Star toggle, then professor (name, with an outlined "Title · not faculty" tag beside it for people who are not professors; a "Job title · Department" line; institution; email; an outlined 32px Website link button in accent ink with a globe icon; and "Grant started/starts Mon YYYY" for the lead grant; a department or website that was not found is said in faint ink), then the lead grant (blue linked title, pill row, a PhD caveat line only for "PhD funding: unlikely", and a "N more grants" disclosure with a left-ruled list), then Ends, Months left and Funding as right-aligned figures. The star toggle is a 40px outlined square in faint ink; pressed, it fills with amber wash, amber border and amber star.

### My list Dialog
Native modal `dialog`, 480px max, 12px corners, hairline-separated head with an icon close button, and a stacked column of full-width buttons (one primary) with a status line in green (success) or red (error).

## Do's and Don'ts

### Do:
- **Do** use `accent` for every link, selected state, active sort and focus ring, and for nothing decorative.
- **Do** pair each signal hue with its own wash (`career-wash`, `likely-wash`, `possible-wash`, `star-wash`, `accent-wash`) as the pill or toggle background.
- **Do** style every new component through role tokens so the dark theme works by token redefinition alone.
- **Do** right-align numeric columns with tabular figures and `white-space: nowrap`.
- **Do** separate content with 1px `line` hairlines and tone steps.
- **Do** give every number an inline label wherever its column header is not visible.
- **Do** keep hover washes behind `@media (hover: hover)` so touch devices do not stick in a hover state.

### Don't:
- **Don't** introduce a second accent or reuse red, amber, green or purple for anything beyond their assigned meanings.
- **Don't** add shadows to panels, rows, buttons or cards; the dialog and an open dropdown panel are the only lifted surfaces.
- **Don't** add a second typeface; Libre Franklin is the only face in `fonts/fonts.css`.
- **Don't** give "PhD funding: unlikely" a filled grey pill; it stays outlined so it never reads as one more neutral tag.
- **Don't** hardcode hex colors in component rules; the only literal colors in the stylesheet are the token blocks and the dialog backdrop.
