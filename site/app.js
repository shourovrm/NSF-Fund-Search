// Rendering and event wiring for index.html. All data logic lives in core.js.
(function () {
  "use strict";

  const PAGE_SIZE = 50;
  const SEARCH_DELAY_MS = 120;
  const TOPIC_PILLS_SHOWN = 2;
  const THEME_STORAGE_KEY = "nsf-theme";

  const filters = NSF.createFilterState();
  let visibleCount = PAGE_SIZE;
  const byId = (id) => document.getElementById(id);
  const escapeHtml = NSF.escapeHtml;

  const starIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z"/></svg>';
  const chevronIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M6 9l6 6 6-6"/></svg>';
  const removeIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" d="M7 7l10 10M17 7L7 17"/></svg>';

  // ---------------------------------------------------------------------------
  // Filter dropdowns
  // ---------------------------------------------------------------------------

  // Grant types grouped by how often they pay PhD research assistants.
  const GRANT_TYPE_GROUP_LABELS = {
    likely: "Usually fund PhD students",
    possible: "Sometimes fund PhD students",
    unlikely: "Rarely fund international PhD students",
  };

  // "Show" options are independent on/off switches in the filter state.
  const SHOW_OPTIONS = {
    strongOnly: "Strong topic match only",
    shortlistOnly: "My list only",
    collaborativeOnly: "Collaborative (multi-university) only",
    includeCenters: "Include centers & institutes",
    includeUndergraduateColleges: "Include undergraduate colleges (RUI)",
  };

  function toggleInSet(set, value, isChecked) {
    if (isChecked) set.add(value);
    else set.delete(value);
  }

  // Dropdowns backed by a Set in `filters` share the same wiring.
  function setBackedDropdown(elementId, name, placeholder, filterKey, extra = {}) {
    return createMultiSelect(byId(elementId), {
      name,
      placeholder,
      searchable: extra.searchable,
      getSelected: () => filters[filterKey],
      onChange: (value, isChecked) => { toggleInSet(filters[filterKey], value, isChecked); extra.afterChange?.(); refresh(); },
      onClear: () => { filters[filterKey].clear(); extra.afterChange?.(); refresh(); },
    });
  }

  const dropdowns = {
    topics: setBackedDropdown("ms-topics", "Topic", "Any topic", "topics", { searchable: true }),
    fields: setBackedDropdown("ms-fields", "Research field", "Any field", "fields"),
    grantTypes: setBackedDropdown("ms-grant-types", "Grant type", "Any grant type", "grantTypes"),
    states: setBackedDropdown("ms-states", "State", "All states", "states", { searchable: true, afterChange: onStatesChanged }),
    institutions: setBackedDropdown("ms-institutions", "University", "Any university", "institutions", { searchable: true }),
    show: createMultiSelect(byId("ms-show"), {
      name: "Show",
      placeholder: "Default view",
      getSelected: () => new Set(Object.keys(SHOW_OPTIONS).filter((key) => filters[key])),
      onChange: (key, isChecked) => { filters[key] = isChecked; refresh(); },
      onClear: () => { for (const key of Object.keys(SHOW_OPTIONS)) filters[key] = false; refresh(); },
    }),
  };

  function renderInstitutionOptions() {
    const institutions = NSF.institutionsIn(filters.states);
    dropdowns.institutions.setOptions(institutions.map((institution) => ({ value: institution.name, label: institution.name, count: institution.count })));
    const scope = filters.states.size ? `in the selected state${filters.states.size > 1 ? "s" : ""}` : "in all states";
    byId("institution-hint").textContent = `${institutions.length} universities ${scope}.`;
  }

  // A university outside the selected states would silently return zero rows.
  function onStatesChanged() {
    const allowed = new Set(NSF.institutionsIn(filters.states).map((institution) => institution.name));
    for (const name of filters.institutions) if (!allowed.has(name)) filters.institutions.delete(name);
    renderInstitutionOptions();
  }

  function renderStaticOptions() {
    dropdowns.topics.setOptions(Object.entries(NSF.TOPIC_LABELS).map(([key, label]) => ({
      value: key, label, count: NSF.topicCounts[key] || 0, group: NSF.TOPIC_GROUPS[key],
    })));
    dropdowns.fields.setOptions(Object.entries(NSF.FIELD_LABELS).map(([key, label]) => ({
      value: key, label, count: NSF.fieldCounts[key] || 0,
    })));
    dropdowns.grantTypes.setOptions(Object.entries(GRANT_TYPE_GROUP_LABELS).flatMap(([level, groupLabel]) =>
      Object.entries(NSF.GRANT_TYPE_LABELS)
        .filter(([key]) => NSF.GRANT_TYPE_PHD_LIKELIHOOD[key] === level)
        .map(([key, label]) => ({ value: key, label, count: NSF.grantTypeCounts[key] || 0, group: groupLabel }))));
    dropdowns.states.setOptions(NSF.states.map((state) => ({ value: state, label: NSF.stateLabel(state), count: NSF.stateCounts[state] })));
    dropdowns.show.setOptions(Object.entries(SHOW_OPTIONS).map(([key, label]) => ({ value: key, label })));
    renderInstitutionOptions();

    const years = NSF.meta.sourceYears;
    const yearRange = years.length > 1 ? `${years[0]}–${years[years.length - 1]}` : years[0];
    byId("app-sub").textContent = `NSF awards ${yearRange}, updated at ${NSF.formatShortDate(NSF.meta.generated)}`;
    byId("coverage-note").textContent = `Covers grants NSF awarded in ${yearRange}.`;
    byId("source-note").textContent =
      `Source: NSF award files for awards made in ${years.join(" and ")}, updated ${NSF.formatDate(NSF.meta.generated)}. ` +
      "Excludes conferences, workshops, SBIR/STTR, I-Corps, fellowships, planning grants, REU sites and undergraduate education grants. " +
      "“Strong match” means the grant title or NSF program names the topic; other matches come from abstract words. " +
      "Centers and undergraduate colleges are hidden unless you include them under “Show”.";
  }

  // Controls mirror `filters`, so reset and chip removal only need to call this.
  function syncControlsFromFilters() {
    for (const dropdown of Object.values(dropdowns)) dropdown.sync();
    byId("phd-level").value = filters.phdLevel;
    byId("min-months").value = String(filters.minMonths);
    byId("min-amount").value = String(filters.minAmount);
    byId("search").value = filters.query;
  }

  // ---------------------------------------------------------------------------
  // Active filter chips
  // ---------------------------------------------------------------------------

  function activeFilterList() {
    const chips = [];
    const labelsByKind = { topics: NSF.TOPIC_LABELS, fields: NSF.FIELD_LABELS, grantTypes: NSF.GRANT_TYPE_LABELS };
    for (const kind of ["topics", "grantTypes", "fields"]) {
      for (const key of filters[kind]) chips.push({ label: labelsByKind[kind][key], remove: () => filters[kind].delete(key) });
    }
    if (filters.query) chips.push({ label: `“${filters.query}”`, remove: () => { filters.query = ""; } });
    const phdChipLabels = { likely: "Likely funds PhD", possible: "Likely or possible PhD funding" };
    if (filters.phdLevel !== "any") chips.push({ label: phdChipLabels[filters.phdLevel], remove: () => { filters.phdLevel = "any"; } });
    if (filters.collaborativeOnly) chips.push({ label: "Collaborative only", remove: () => { filters.collaborativeOnly = false; } });
    for (const state of filters.states) chips.push({ label: NSF.stateLabel(state), remove: () => { filters.states.delete(state); onStatesChanged(); } });
    for (const institution of filters.institutions) chips.push({ label: institution, remove: () => filters.institutions.delete(institution) });
    if (filters.minMonths) chips.push({ label: `${filters.minMonths}+ months left`, remove: () => { filters.minMonths = 0; } });
    if (filters.minAmount) chips.push({ label: `${NSF.formatMoney(filters.minAmount)}+ funding`, remove: () => { filters.minAmount = 0; } });
    if (filters.strongOnly) chips.push({ label: "Strong match", remove: () => { filters.strongOnly = false; } });
    if (filters.shortlistOnly) chips.push({ label: "My list", remove: () => { filters.shortlistOnly = false; } });
    if (filters.includeCenters) chips.push({ label: "With centers", remove: () => { filters.includeCenters = false; } });
    if (filters.includeUndergraduateColleges) chips.push({ label: "With RUI colleges", remove: () => { filters.includeUndergraduateColleges = false; } });
    return chips;
  }

  let currentChips = [];

  function renderActiveFilters() {
    currentChips = activeFilterList();
    byId("active-filters").innerHTML = currentChips.length
      ? currentChips.map((chip, index) => `<button class="filter-chip" type="button" data-chip="${index}" aria-label="Remove filter ${escapeHtml(chip.label)}">${escapeHtml(chip.label)}${removeIcon}</button>`).join("") +
        '<button class="clear-all" type="button" id="clear-all">Clear all</button>'
      : "";
    byId("filters-toggle-count").textContent = currentChips.length ? `(${currentChips.length} on)` : "";
  }

  // ---------------------------------------------------------------------------
  // Table rows
  // ---------------------------------------------------------------------------

  function startLabel(startDate) {
    const hasStarted = new Date(startDate + "T00:00:00") <= new Date();
    return `Grant ${hasStarted ? "started" : "starts"} ${NSF.formatDate(startDate)}`;
  }

  function phdPill(grant) {
    return `<span class="pill phd-${grant.phd}" title="${escapeHtml(grant.phdReason)}">${PHD_PILL_LABELS[grant.phd]}</span>`;
  }

  const PHD_PILL_LABELS = { likely: "PhD: likely", possible: "PhD: maybe", unlikely: "PhD: unlikely" };

  // Only "unlikely" earns a visible line; "maybe" keeps its reason in the pill's tooltip
  // so rows stay short.
  function phdCaveat(grant) {
    if (grant.phd !== "unlikely") return "";
    return `<div class="why">PhD funding: ${escapeHtml(grant.phdReason)}</div>`;
  }

  function grantPills(grant) {
    const typePill = grant.type === "career"
      ? '<span class="pill career">CAREER</span>'
      : grant.type === "standard" ? "" : `<span class="pill">${escapeHtml(NSF.GRANT_TYPE_LABELS[grant.type])}</span>`;
    const collabPill = grant.collab ? '<span class="pill">Collaborative</span>' : "";
    // Selected topics first, so the pill that explains the match is always visible.
    const topicKeys = [...grant.topicKeys].sort((a, b) => filters.topics.has(b) - filters.topics.has(a));
    const topicPills = topicKeys.slice(0, TOPIC_PILLS_SHOWN)
      .map((key) => `<span class="pill topic${key === NSF.OTHER_TOPIC ? " other" : ""}">${escapeHtml(NSF.TOPIC_LABELS[key])}</span>`);
    const hiddenTopicCount = topicKeys.length - TOPIC_PILLS_SHOWN;
    if (hiddenTopicCount > 0) topicPills.push(`<span class="pill">+${hiddenTopicCount} topic${hiddenTopicCount > 1 ? "s" : ""}</span>`);
    return phdPill(grant) + typePill + collabPill + topicPills.join("");
  }

  function otherGrantsList(otherGrants) {
    if (!otherGrants.length) return "";
    const items = otherGrants.map((grant) => `
      <li><a href="${NSF.awardUrl(grant.id)}" target="_blank" rel="noopener">${escapeHtml(grant.title)}</a>
        <div class="sub">${escapeHtml(NSF.PHD_LABELS[grant.phd])} · ${escapeHtml(NSF.GRANT_TYPE_LABELS[grant.type])} · ${startLabel(grant.start)} · ends ${NSF.formatDate(grant.end)} · ${NSF.formatMoney(grant.amount)}</div></li>`).join("");
    return `<details class="more-grants"><summary>${otherGrants.length} more grant${otherGrants.length > 1 ? "s" : ""}${chevronIcon}</summary><ul>${items}</ul></details>`;
  }

  function renderRow(result) {
    const { pi, leadGrant: grant, otherGrants } = result;
    const starred = NSF.isShortlisted(pi.id);
    return `<tr>
      <td class="star-cell"><button class="star" type="button" data-star="${escapeHtml(pi.id)}" aria-pressed="${starred}" aria-label="${starred ? "Remove" : "Add"} ${escapeHtml(pi.name)} ${starred ? "from" : "to"} my list">${starIcon}</button></td>
      <td class="pi-cell">
        <div class="name">${escapeHtml(pi.name)}</div>
        <div class="inst">${escapeHtml(pi.institution)}${pi.state ? ", " + pi.state : ""}</div>
        ${pi.email ? `<a class="email" href="mailto:${escapeHtml(pi.email)}">${escapeHtml(pi.email)}</a>` : ""}
        <div class="pi-start">${startLabel(grant.start)}</div>
      </td>
      <td>
        <a class="grant-title" href="${NSF.awardUrl(grant.id)}" target="_blank" rel="noopener">${escapeHtml(grant.title)}</a>
        <div class="pills">${grantPills(grant)}</div>
        ${phdCaveat(grant)}
        ${otherGrantsList(otherGrants)}
      </td>
      <td class="num" data-label="Ends">${NSF.formatDate(grant.end)}</td>
      <td class="num" data-label="Left"><span class="months">${Math.max(grant.monthsLeft, 0)}</span> mo</td>
      <td class="num" data-label="Funding">${NSF.formatMoney(result.matchingAmount)}</td>
    </tr>`;
  }

  // Header buttons and the sort select are two views of one setting.
  function renderSortState() {
    byId("sort").value = filters.sort;
    for (const header of document.querySelectorAll("th[data-sort-key]")) {
      if (header.dataset.sortKey === filters.sort) header.setAttribute("aria-sort", filters.sort === "name" ? "ascending" : "descending");
      else header.removeAttribute("aria-sort");
    }
  }

  function renderListCount() {
    byId("list-count").textContent = NSF.shortlistSize();
  }

  function render() {
    const results = NSF.applyFilters(filters);
    byId("count").innerHTML = `<strong>${results.length.toLocaleString()}</strong> professor${results.length === 1 ? "" : "s"}`;
    byId("rows").innerHTML = results.length
      ? results.slice(0, visibleCount).map(renderRow).join("")
      : '<tr><td class="empty" colspan="6">No professors match these filters. Remove a filter above, or include centers and undergraduate colleges under “Show”.</td></tr>';
    const remaining = results.length - visibleCount;
    byId("load-more").hidden = remaining <= 0;
    byId("load-more").textContent = `Show ${Math.min(PAGE_SIZE, remaining)} more (${remaining.toLocaleString()} left)`;
    renderActiveFilters();
    renderListCount();
    renderSortState();
  }

  function refresh() {
    visibleCount = PAGE_SIZE;
    render();
  }

  // ---------------------------------------------------------------------------
  // Events
  // ---------------------------------------------------------------------------

  byId("phd-level").addEventListener("change", (event) => { filters.phdLevel = event.target.value; refresh(); });
  byId("min-months").addEventListener("change", (event) => { filters.minMonths = Number(event.target.value); refresh(); });
  byId("min-amount").addEventListener("change", (event) => { filters.minAmount = Number(event.target.value); refresh(); });

  let searchTimer = 0;
  byId("search").addEventListener("input", (event) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { filters.query = event.target.value.trim(); refresh(); }, SEARCH_DELAY_MS);
  });
  byId("sort").addEventListener("change", (event) => { filters.sort = event.target.value; refresh(); });
  document.querySelector("thead").addEventListener("click", (event) => {
    const header = event.target.closest("[data-sort]");
    if (!header) return;
    filters.sort = header.dataset.sort;
    refresh();
  });

  byId("active-filters").addEventListener("click", (event) => {
    if (event.target.closest("#clear-all")) { resetFilters(); return; }
    const chip = event.target.closest("[data-chip]");
    if (!chip) return;
    currentChips[Number(chip.dataset.chip)].remove();
    renderInstitutionOptions();
    syncControlsFromFilters();
    refresh();
  });

  byId("rows").addEventListener("click", (event) => {
    const button = event.target.closest("[data-star]");
    if (!button) return;
    const starred = NSF.toggleShortlist(button.dataset.star);
    button.setAttribute("aria-pressed", starred);
    const name = button.closest("tr").querySelector(".name").textContent;
    button.setAttribute("aria-label", `${starred ? "Remove" : "Add"} ${name} ${starred ? "from" : "to"} my list`);
    renderListCount();
  });

  byId("load-more").addEventListener("click", () => { visibleCount += PAGE_SIZE; render(); });

  function resetFilters() {
    const sort = filters.sort;
    Object.assign(filters, NSF.createFilterState(), { sort });
    renderInstitutionOptions();
    syncControlsFromFilters();
    refresh();
  }
  byId("reset").addEventListener("click", resetFilters);

  byId("filters-toggle").addEventListener("click", () => {
    const open = byId("filters").dataset.open !== "true";
    byId("filters").dataset.open = open;
    byId("filters-toggle").setAttribute("aria-expanded", open);
  });

  // ---------------------------------------------------------------------------
  // My list dialog
  // ---------------------------------------------------------------------------

  function setListStatus(message, isError) {
    byId("list-status").textContent = message;
    byId("list-status").classList.toggle("error", Boolean(isError));
  }

  function renderSyncState() {
    const connected = NSFSync.isConnected();
    byId("sync-unavailable").hidden = NSFSync.isAvailable;
    byId("sync-form").hidden = !NSFSync.isAvailable || connected;
    byId("sync-connected").hidden = !NSFSync.isAvailable || !connected;
  }

  function setSyncStatus(message, isError) {
    byId("sync-status").textContent = message;
    byId("sync-status").classList.toggle("error", Boolean(isError));
  }
  NSFSync.onStatus(setSyncStatus);

  byId("sync-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    byId("sync-submit").disabled = true;
    try {
      const { addedFromOnline } = await NSFSync.connect(byId("sync-passphrase").value);
      byId("sync-passphrase").value = "";
      if (addedFromOnline) setSyncStatus(`Sync is on. ${addedFromOnline} professor${addedFromOnline === 1 ? "" : "s"} added from your online list.`);
      renderSyncState();
      render();
    } catch (error) {
      setSyncStatus(`Could not turn on sync: ${error.message}`, true);
    }
    byId("sync-submit").disabled = false;
  });
  byId("sync-disconnect").addEventListener("click", () => {
    NSFSync.disconnect();
    renderSyncState();
  });

  byId("open-list").addEventListener("click", () => {
    const size = NSF.shortlistSize();
    byId("list-summary").textContent = size
      ? `${size} professor${size > 1 ? "s" : ""} saved. Star or unstar anyone in the table.`
      : "Your list is empty. Use the star next to a professor to save them here.";
    setListStatus("");
    renderSyncState();
    byId("list-dialog").showModal();
  });
  byId("close-list").addEventListener("click", () => byId("list-dialog").close());
  byId("show-list").addEventListener("click", () => {
    filters.shortlistOnly = true;
    syncControlsFromFilters();
    refresh();
    byId("list-dialog").close();
  });
  byId("export-csv").addEventListener("click", () => {
    if (!NSF.shortlistSize()) { setListStatus("Your list is empty, so there is nothing to download.", true); return; }
    NSF.downloadFile("nsf-professor-list.csv", NSF.shortlistCsv(), "text/csv");
    setListStatus("Spreadsheet downloaded.");
  });
  byId("export-backup").addEventListener("click", () => {
    NSF.downloadFile(`nsf-list-backup-${new Date().toISOString().slice(0, 10)}.json`, NSF.shortlistBackup(), "application/json");
    setListStatus("Backup downloaded.");
  });
  byId("import-backup").addEventListener("click", () => byId("import-file").click());
  byId("import-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      const { addedCount, unknownCount } = NSF.importShortlistBackup(await file.text());
      const unknownNote = unknownCount ? ` ${unknownCount} saved professor${unknownCount > 1 ? "s are" : " is"} not in the current data (their grants may have ended).` : "";
      setListStatus(`Imported: ${addedCount} professor${addedCount === 1 ? "" : "s"} added.${unknownNote}`);
      render();
    } catch (error) {
      setListStatus(`Could not import this file. Choose a backup downloaded from this site. (${error.message})`, true);
    }
    event.target.value = "";
  });

  // ---------------------------------------------------------------------------
  // Theme
  // ---------------------------------------------------------------------------

  function applyTheme(theme) {
    const isDark = theme === "dark";
    if (isDark) document.documentElement.dataset.theme = "dark";
    else delete document.documentElement.dataset.theme;
    byId("theme-toggle").setAttribute("aria-pressed", isDark);
    byId("theme-toggle").setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
    byId("theme-toggle-label").textContent = isDark ? "Light mode" : "Dark mode";
  }
  byId("theme-toggle").addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    applyTheme(nextTheme);
  });

  applyTheme(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
  renderStaticOptions();
  render();
  // Adopts the online list after the first paint, so the table never waits on the network.
  NSFSync.startup().then(render);
})();
