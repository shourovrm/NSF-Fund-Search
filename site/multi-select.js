// A combobox that holds a list of options, so one filter can take several values.
// The field is a text input: typing filters the list (autosuggest), and ticked options
// sit in a "Selected" group at the top. The panel opens in place (not as an overlay) so
// the scrolling filter sidebar never clips it.
//
// Accessibility pattern: ARIA 1.2 combobox. The input has role="combobox" and points at a
// role="listbox" (aria-multiselectable) through aria-controls; the highlighted option is
// announced through aria-activedescendant, so keyboard focus never leaves the input.
(function () {
  "use strict";

  const chevronIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M6 9l6 6 6-6"/></svg>';
  const openDropdowns = new Set();

  function escapeHtml(text) {
    return String(text ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }

  function escapeRegExp(text) {
    return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  // Lower-cases, treats "&" as the word "and", and collapses whitespace, so that
  // "physics and astronomy" finds "Physics & Astronomy".
  function normalizeForMatch(text) {
    return String(text ?? "").toLowerCase().replace(/&/g, " and ").replace(/\s+/g, " ").trim();
  }

  // Builds the pattern used only to find which part of the label to bold. It accepts
  // either "and" or "&" wherever the query has "and", and ignores spacing differences.
  function buildMatchPattern(query) {
    const normalizedQuery = normalizeForMatch(query);
    if (!normalizedQuery) return null;
    const source = normalizedQuery
      .split("and")
      .map((part) => escapeRegExp(part).replace(/ /g, "\\s*"))
      .join("(?:and|&)");
    return new RegExp(source, "i");
  }

  // Escapes every piece separately, so the query never reaches innerHTML as markup.
  function highlightLabelHtml(label, pattern) {
    const match = pattern ? pattern.exec(label) : null;
    if (!match) return escapeHtml(label);
    const before = label.slice(0, match.index);
    const after = label.slice(match.index + match[0].length);
    return `${escapeHtml(before)}<mark>${escapeHtml(match[0])}</mark>${escapeHtml(after)}`;
  }

  // Ticked options come first in the order they were ticked (a Set iterates in insertion
  // order); the rest keep their original order.
  function orderSelectedFirst(options, selectedValues) {
    const optionByValue = new Map(options.map((option) => [option.value, option]));
    const selectedOptions = [];
    for (const value of selectedValues) {
      if (optionByValue.has(value)) selectedOptions.push(optionByValue.get(value));
    }
    const remainingOptions = options.filter((option) => !selectedValues.has(option.value));
    return { selectedOptions, remainingOptions };
  }

  // Only one dropdown is open at a time; clicking elsewhere closes it. The composed path
  // is read because a clicked row may already be detached from the page by the time this
  // handler runs (the Selected group is rebuilt on each tick).
  document.addEventListener("click", (event) => {
    const clickPath = event.composedPath();
    for (const dropdown of openDropdowns) {
      if (!clickPath.includes(dropdown.root)) dropdown.close();
    }
  });

  /**
   * @param root        empty element to render into
   * @param options     name (accessible label), placeholder (shown when nothing is
   *                    selected), getSelected() -> Set of values,
   *                    onChange(value, isChecked), onClear().
   *                    `searchable` is accepted but ignored: every field has autosuggest.
   */
  function createMultiSelect(root, { name, placeholder, getSelected, onChange, onClear }) {
    const listboxId = `${root.id}-listbox`;
    const selectedHeadingId = `${root.id}-selected-heading`;
    let entries = [];
    let groups = [];
    let query = "";
    let normalizedQuery = "";
    let matchPattern = null;
    let activeRow = null;

    root.classList.add("multi-select");
    root.innerHTML = `
      <div class="ms-field">
        <input class="ms-input" type="text" role="combobox" aria-expanded="false" aria-controls="${listboxId}" aria-autocomplete="list" aria-label="${escapeHtml(name)}" placeholder="${escapeHtml(placeholder)}" autocomplete="off" spellcheck="false">
        <span class="ms-chevron">${chevronIcon}</span>
      </div>
      <div class="ms-panel" hidden>
        <div class="ms-scroll">
          <div class="ms-listbox" id="${listboxId}" role="listbox" aria-multiselectable="true" aria-label="${escapeHtml(name)}">
            <div class="ms-selected-group" role="group" aria-labelledby="${selectedHeadingId}" hidden>
              <p class="ms-group" id="${selectedHeadingId}">Selected</p>
              <div class="ms-selected-rows"></div>
            </div>
            <div class="ms-main-rows"></div>
          </div>
          <p class="ms-empty" role="status" hidden></p>
        </div>
        <div class="ms-footer"><button class="ms-clear" type="button">Clear</button><button class="ms-done" type="button">Done</button></div>
      </div>`;
    const input = root.querySelector(".ms-input");
    const chevron = root.querySelector(".ms-chevron");
    const panel = root.querySelector(".ms-panel");
    const scrollContainer = root.querySelector(".ms-scroll");
    const listbox = root.querySelector(".ms-listbox");
    const selectedGroup = root.querySelector(".ms-selected-group");
    const selectedRowsContainer = root.querySelector(".ms-selected-rows");
    const mainRowsContainer = root.querySelector(".ms-main-rows");
    const emptyMessage = root.querySelector(".ms-empty");
    const clearButton = root.querySelector(".ms-clear");

    const dropdown = {
      root,
      open() {
        if (!panel.hidden) return;
        for (const other of openDropdowns) other.close();
        panel.hidden = false;
        input.setAttribute("aria-expanded", "true");
        openDropdowns.add(dropdown);
      },
      close() {
        if (panel.hidden) return;
        panel.hidden = true;
        input.setAttribute("aria-expanded", "false");
        openDropdowns.delete(dropdown);
        setActiveRow(null, false);
        if (query) clearQuery();
      },
      setOptions(nextOptions) {
        buildMainRows(nextOptions);
        applyQuery();
        renderSummary();
      },
      // Re-reads the current selection, e.g. after a chip removal or reset.
      sync() {
        refreshSelection();
      },
    };

    function isOpen() {
      return !panel.hidden;
    }

    function buildRowHtml(entry, rowId, isChecked) {
      const count = entry.option.count === undefined ? "" : `<span class="ms-count">${entry.option.count.toLocaleString()}</span>`;
      return `<div class="ms-option" role="option" id="${rowId}" aria-selected="${isChecked}" data-index="${entry.index}">` +
        `<input type="checkbox" tabindex="-1" aria-hidden="true" ${isChecked ? "checked" : ""}>` +
        `<span class="ms-label">${escapeHtml(entry.option.label)}</span>${count}</div>`;
    }

    // Built once per option list; later filtering only toggles `hidden` on these nodes.
    function buildMainRows(options) {
      entries = options.map((option, index) => ({
        option,
        index,
        normalizedLabel: normalizeForMatch(option.label),
        matches: true,
        mainRow: null,
        selectedRow: null,
        mainRowHasMarkup: false,
      }));

      const groupBlocks = [];
      let currentBlock = null;
      for (const entry of entries) {
        const groupName = entry.option.group || "";
        if (!currentBlock || currentBlock.groupName !== groupName) {
          currentBlock = { groupName, entries: [], html: "" };
          groupBlocks.push(currentBlock);
        }
        currentBlock.entries.push(entry);
        currentBlock.html += buildRowHtml(entry, `${root.id}-opt-${entry.index}`, false);
      }

      let html = "";
      groupBlocks.forEach((block, blockIndex) => {
        if (block.groupName) {
          const headingId = `${root.id}-group-${blockIndex}`;
          html += `<div class="ms-group-block" role="group" aria-labelledby="${headingId}" data-block="${blockIndex}"><p class="ms-group" id="${headingId}">${escapeHtml(block.groupName)}</p>${block.html}</div>`;
        } else {
          html += `<div class="ms-group-block" data-block="${blockIndex}">${block.html}</div>`;
        }
      });
      mainRowsContainer.innerHTML = html;

      for (const row of mainRowsContainer.querySelectorAll(".ms-option")) {
        entries[Number(row.dataset.index)].mainRow = row;
      }
      const blockElements = mainRowsContainer.querySelectorAll(".ms-group-block");
      groups = groupBlocks.map((block, blockIndex) => ({ element: blockElements[blockIndex], entries: block.entries }));
      activeRow = null;
      input.removeAttribute("aria-activedescendant");
    }

    function setLabelMarkup(row, entry) {
      row.querySelector(".ms-label").innerHTML = highlightLabelHtml(entry.option.label, matchPattern);
    }

    // Filters by toggling `hidden` on existing rows; nothing is rebuilt except the
    // small Selected group.
    function applyQuery() {
      for (const entry of entries) {
        entry.matches = !normalizedQuery || entry.normalizedLabel.includes(normalizedQuery);
        if (entry.matches && matchPattern) {
          setLabelMarkup(entry.mainRow, entry);
          entry.mainRowHasMarkup = true;
        } else if (entry.mainRowHasMarkup) {
          entry.mainRow.querySelector(".ms-label").textContent = entry.option.label;
          entry.mainRowHasMarkup = false;
        }
      }
      renderVisibility();
    }

    // Shows or hides rows and headings from the current query and selection.
    function renderVisibility() {
      const selected = getSelected();
      for (const entry of entries) {
        entry.mainRow.hidden = !entry.matches || selected.has(entry.option.value);
      }
      for (const group of groups) {
        group.element.hidden = group.entries.every((entry) => entry.mainRow.hidden);
      }
      rebuildSelectedGroup(selected);
      updateEmptyMessage();
      if (activeRow && (!activeRow.isConnected || activeRow.hidden)) setActiveRow(null, false);
    }

    // Only the ticked options are rebuilt, so ticking stays fast on a 1,500-row list.
    function rebuildSelectedGroup(selected) {
      const { selectedOptions } = orderSelectedFirst(entries.map((entry) => entry.option), selected);
      const entryByValue = new Map(entries.map((entry) => [entry.option.value, entry]));
      for (const entry of entries) entry.selectedRow = null;

      let html = "";
      for (const option of selectedOptions) {
        const entry = entryByValue.get(option.value);
        html += buildRowHtml(entry, `${root.id}-sel-${entry.index}`, true);
      }
      selectedRowsContainer.innerHTML = html;

      let visibleCount = 0;
      for (const row of selectedRowsContainer.querySelectorAll(".ms-option")) {
        const entry = entries[Number(row.dataset.index)];
        entry.selectedRow = row;
        row.hidden = !entry.matches;
        if (entry.matches) {
          visibleCount += 1;
          if (matchPattern) setLabelMarkup(row, entry);
        }
      }
      selectedGroup.hidden = visibleCount === 0;
    }

    function updateEmptyMessage() {
      const hasVisibleRow = listbox.querySelector(".ms-option:not([hidden])") !== null;
      if (hasVisibleRow) {
        emptyMessage.hidden = true;
        return;
      }
      emptyMessage.textContent = entries.length === 0 ? "No options" : `No matches for “${query.trim()}”`;
      emptyMessage.hidden = false;
    }

    function renderSummary() {
      const selected = getSelected();
      const { selectedOptions } = orderSelectedFirst(entries.map((entry) => entry.option), selected);
      let summary = placeholder;
      if (selectedOptions.length === 1) summary = selectedOptions[0].label;
      if (selectedOptions.length > 1) summary = `${selectedOptions.length} selected`;
      input.placeholder = summary;
      input.setAttribute("aria-label", selectedOptions.length === 0 ? name : `${name}, ${summary}`);
      root.classList.toggle("has-value", selectedOptions.length > 0);
      clearButton.disabled = selectedOptions.length === 0;
    }

    function refreshSelection() {
      const activeIdentity = describeRow(activeRow);
      renderVisibility();
      renderSummary();
      setActiveRow(findRow(activeIdentity), false);
    }

    function describeRow(row) {
      if (!row) return null;
      return { index: Number(row.dataset.index), inSelectedGroup: selectedRowsContainer.contains(row) };
    }

    // The same option has two possible rows (main list or Selected group); this finds the
    // one that exists now, preferring the kind it had before.
    function findRow(identity) {
      if (!identity) return null;
      const entry = entries[identity.index];
      if (!entry) return null;
      const preferred = identity.inSelectedGroup ? entry.selectedRow : entry.mainRow;
      const fallback = identity.inSelectedGroup ? entry.mainRow : entry.selectedRow;
      if (preferred && !preferred.hidden) return preferred;
      if (fallback && !fallback.hidden) return fallback;
      return null;
    }

    function visibleRows() {
      return Array.from(listbox.querySelectorAll(".ms-option:not([hidden])"));
    }

    function setActiveRow(row, shouldScroll) {
      if (activeRow && activeRow !== row) activeRow.classList.remove("is-active");
      activeRow = row;
      if (!row) {
        input.removeAttribute("aria-activedescendant");
        return;
      }
      row.classList.add("is-active");
      input.setAttribute("aria-activedescendant", row.id);
      if (shouldScroll) row.scrollIntoView({ block: "nearest" });
    }

    function moveActiveRow(step) {
      const rows = visibleRows();
      if (rows.length === 0) return;
      const currentPosition = rows.indexOf(activeRow);
      let nextPosition;
      if (currentPosition === -1) nextPosition = step > 0 ? 0 : rows.length - 1;
      else nextPosition = Math.min(rows.length - 1, Math.max(0, currentPosition + step));
      setActiveRow(rows[nextPosition], true);
    }

    function toggleRow(row) {
      const entry = entries[Number(row.dataset.index)];
      const nextRows = visibleRows();
      const followingRow = nextRows[nextRows.indexOf(row) + 1] || null;
      const anchorIdentity = describeRow(followingRow);
      const anchorTopBefore = followingRow ? followingRow.getBoundingClientRect().top : 0;

      const isChecked = !getSelected().has(entry.option.value);
      onChange(entry.option.value, isChecked);

      const activeIdentity = { index: entry.index, inSelectedGroup: isChecked };
      renderVisibility();
      renderSummary();
      setActiveRow(findRow(activeIdentity), false);

      // The ticked row jumps to the top of the list; shifting the scroll offset by the
      // anchor row's movement keeps the rows under the pointer where they were.
      const anchorRow = findRow(anchorIdentity);
      if (anchorRow) {
        scrollContainer.scrollTop += anchorRow.getBoundingClientRect().top - anchorTopBefore;
      }
    }

    function clearQuery() {
      input.value = "";
      setQuery("");
    }

    function setQuery(nextQuery) {
      query = nextQuery;
      normalizedQuery = normalizeForMatch(nextQuery);
      matchPattern = buildMatchPattern(nextQuery);
      applyQuery();
      scrollContainer.scrollTop = 0;
    }

    input.addEventListener("input", () => {
      dropdown.open();
      setQuery(input.value);
      setActiveRow(normalizedQuery ? visibleRows()[0] || null : null, false);
    });
    input.addEventListener("click", () => dropdown.open());
    chevron.addEventListener("mousedown", (event) => event.preventDefault());
    chevron.addEventListener("click", () => {
      if (isOpen()) dropdown.close();
      else dropdown.open();
      input.focus();
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        const wasOpen = isOpen();
        dropdown.open();
        // A press on a closed field opens the list and highlights the first or last row.
        if (wasOpen || !activeRow) moveActiveRow(event.key === "ArrowDown" ? 1 : -1);
      } else if (event.key === "Enter" && isOpen()) {
        event.preventDefault();
        if (activeRow) toggleRow(activeRow);
      } else if (event.key === " ") {
        // With a query typed, a space belongs to the query.
        if (query !== "") return;
        event.preventDefault();
        if (!isOpen()) dropdown.open();
        else if (activeRow) toggleRow(activeRow);
      } else if (event.key === "Escape") {
        if (query) {
          event.stopPropagation();
          clearQuery();
        } else if (isOpen()) {
          event.stopPropagation();
          dropdown.close();
        }
      } else if (event.key === "Tab") {
        dropdown.close();
      }
    });

    // Keeping focus in the input while the pointer works the list lets the user type, tick
    // and type again without clicking back into the field.
    panel.addEventListener("mousedown", (event) => {
      if (event.target.closest(".ms-option, button")) event.preventDefault();
    });
    listbox.addEventListener("click", (event) => {
      const row = event.target.closest(".ms-option");
      if (!row) return;
      toggleRow(row);
      input.focus();
    });
    listbox.addEventListener("mouseover", (event) => {
      const row = event.target.closest(".ms-option");
      if (row && row !== activeRow) setActiveRow(row, false);
    });
    clearButton.addEventListener("click", () => {
      onClear();
      refreshSelection();
      input.focus();
    });
    root.querySelector(".ms-done").addEventListener("click", () => {
      dropdown.close();
      input.focus();
    });

    renderSummary();
    return dropdown;
  }

  // Exposed so the pure helpers can be unit-tested outside a browser.
  createMultiSelect._helpers = { normalizeForMatch, buildMatchPattern, highlightLabelHtml, orderSelectedFirst };
  window.createMultiSelect = createMultiSelect;
})();
