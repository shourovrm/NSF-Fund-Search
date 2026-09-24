// A dropdown that holds a list of checkboxes, so one filter can take several values.
// The panel opens in place (not as an overlay) so the scrolling filter sidebar never
// clips it.
(function () {
  "use strict";

  const chevronIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M6 9l6 6 6-6"/></svg>';
  const openDropdowns = new Set();

  function escapeHtml(text) {
    return String(text ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }

  // Only one dropdown is open at a time; clicking elsewhere closes it.
  document.addEventListener("click", (event) => {
    for (const dropdown of openDropdowns) {
      if (!dropdown.root.contains(event.target)) dropdown.close();
    }
  });

  /**
   * @param root        empty element to render into
   * @param options     name (accessible label), placeholder (shown when nothing is
   *                    selected), searchable, getSelected() -> Set of values,
   *                    onChange(value, isChecked), onClear()
   */
  function createMultiSelect(root, { name, placeholder, searchable, getSelected, onChange, onClear }) {
    const panelId = `${root.id}-panel`;
    let optionList = [];

    root.classList.add("multi-select");
    root.innerHTML = `
      <button class="ms-button" type="button" aria-expanded="false" aria-controls="${panelId}" aria-label="${escapeHtml(name)}">
        <span class="ms-value"></span>${chevronIcon}
      </button>
      <div class="ms-panel" id="${panelId}" hidden>
        ${searchable ? `<input class="ms-search" type="search" placeholder="Search ${escapeHtml(name.toLowerCase())}" aria-label="Search ${escapeHtml(name.toLowerCase())}" autocomplete="off">` : ""}
        <div class="ms-options" role="group" aria-label="${escapeHtml(name)}"></div>
        <div class="ms-footer"><button class="ms-clear" type="button">Clear</button><button class="ms-done" type="button">Done</button></div>
      </div>`;
    const button = root.querySelector(".ms-button");
    const panel = root.querySelector(".ms-panel");
    const optionsContainer = root.querySelector(".ms-options");
    const searchInput = root.querySelector(".ms-search");

    const dropdown = {
      root,
      open() {
        for (const other of openDropdowns) other.close();
        panel.hidden = false;
        button.setAttribute("aria-expanded", "true");
        openDropdowns.add(dropdown);
        (searchInput || optionsContainer.querySelector("input"))?.focus();
      },
      close() {
        panel.hidden = true;
        button.setAttribute("aria-expanded", "false");
        openDropdowns.delete(dropdown);
        if (searchInput && searchInput.value) {
          searchInput.value = "";
          applySearch("");
        }
      },
      setOptions(nextOptions) {
        optionList = nextOptions;
        renderOptions();
      },
      // Re-reads the current selection, e.g. after a chip removal or reset.
      sync() {
        const selected = getSelected();
        for (const input of optionsContainer.querySelectorAll("input")) input.checked = selected.has(input.value);
        renderSummary();
      },
    };

    function renderOptions() {
      const selected = getSelected();
      let html = "";
      let currentGroup = null;
      for (const option of optionList) {
        if (option.group && option.group !== currentGroup) {
          currentGroup = option.group;
          html += `<p class="ms-group" data-group="${escapeHtml(option.group)}">${escapeHtml(option.group)}</p>`;
        }
        const count = option.count === undefined ? "" : `<span class="n">${option.count.toLocaleString()}</span>`;
        html += `<label class="check ms-option" data-group="${escapeHtml(option.group || "")}" data-search="${escapeHtml(option.label.toLowerCase())}">
          <input type="checkbox" value="${escapeHtml(option.value)}" ${selected.has(option.value) ? "checked" : ""}> ${escapeHtml(option.label)}${count}</label>`;
      }
      optionsContainer.innerHTML = html || '<p class="ms-empty">No options</p>';
      renderSummary();
    }

    function renderSummary() {
      const selected = getSelected();
      const labels = optionList.filter((option) => selected.has(option.value)).map((option) => option.label);
      const summary = root.querySelector(".ms-value");
      summary.textContent = labels.length === 0 ? placeholder : labels.length === 1 ? labels[0] : `${labels.length} selected`;
      root.classList.toggle("has-value", labels.length > 0);
      root.querySelector(".ms-clear").disabled = labels.length === 0;
    }

    function applySearch(query) {
      const term = query.trim().toLowerCase();
      const visibleGroups = new Set();
      for (const option of optionsContainer.querySelectorAll(".ms-option")) {
        const matches = !term || option.dataset.search.includes(term);
        option.hidden = !matches;
        if (matches) visibleGroups.add(option.dataset.group);
      }
      for (const groupLabel of optionsContainer.querySelectorAll(".ms-group")) {
        groupLabel.hidden = !visibleGroups.has(groupLabel.dataset.group);
      }
    }

    button.addEventListener("click", () => (panel.hidden ? dropdown.open() : dropdown.close()));
    optionsContainer.addEventListener("change", (event) => {
      onChange(event.target.value, event.target.checked);
      renderSummary();
    });
    root.querySelector(".ms-clear").addEventListener("click", () => {
      onClear();
      dropdown.sync();
    });
    root.querySelector(".ms-done").addEventListener("click", () => {
      dropdown.close();
      button.focus();
    });
    searchInput?.addEventListener("input", () => applySearch(searchInput.value));
    root.addEventListener("keydown", (event) => {
      if (event.key !== "Escape" || panel.hidden) return;
      event.stopPropagation();
      dropdown.close();
      button.focus();
    });

    renderSummary();
    return dropdown;
  }

  window.createMultiSelect = createMultiSelect;
})();
