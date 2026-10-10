// Data model for the site: normalizes window.NSF_DATA, filters it, and keeps
// the shortlist in localStorage. app.js only renders and wires up events.
(function () {
  "use strict";

  const data = window.NSF_DATA;
  const FIELD_LABELS = data.fields;
  const TOPIC_LABELS = data.topics;
  const TOPIC_GROUPS = data.topicGroups;
  const GRANT_TYPE_LABELS = data.grantTypes;
  const PHD_LABELS = data.phdLikelihood;
  const GRANT_TYPE_PHD_LIKELIHOOD = data.grantTypePhdLikelihood;
  // Lower rank = more likely to pay a PhD research assistant.
  const PHD_RANK = { likely: 0, possible: 1, unlikely: 2 };
  // Filter values: which likelihood levels each option keeps.
  const PHD_FILTER_LEVELS = { any: ["likely", "possible", "unlikely"], possible: ["likely", "possible"], likely: ["likely"] };
  const OTHER_TOPIC = "other";

  const SHORTLIST_STORAGE_KEY = "nsf-shortlist-v1";

  // A PhD needs about five years of support, so runway beyond 60 months adds
  // nothing when ranking; ties go to on-topic matches and CAREER awards.
  const USEFUL_RUNWAY_MONTHS = 60;

  const STATE_NAMES = {
    AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California", CO: "Colorado",
    CT: "Connecticut", DE: "Delaware", DC: "District of Columbia", FL: "Florida", GA: "Georgia",
    HI: "Hawaii", ID: "Idaho", IL: "Illinois", IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky",
    LA: "Louisiana", ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan", MN: "Minnesota",
    MS: "Mississippi", MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada", NH: "New Hampshire",
    NJ: "New Jersey", NM: "New Mexico", NY: "New York", NC: "North Carolina", ND: "North Dakota",
    OH: "Ohio", OK: "Oklahoma", OR: "Oregon", PA: "Pennsylvania", PR: "Puerto Rico", RI: "Rhode Island",
    SC: "South Carolina", SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont",
    VA: "Virginia", VI: "U.S. Virgin Islands", GU: "Guam", WA: "Washington", WV: "West Virginia",
    WI: "Wisconsin", WY: "Wyoming",
  };

  function stateLabel(stateCode) {
    return STATE_NAMES[stateCode] ? `${STATE_NAMES[stateCode]} - ${stateCode}` : stateCode;
  }

  function toDisplayName(rawName) {
    if (rawName !== rawName.toUpperCase()) return rawName;
    return rawName.toLowerCase().replace(/\b([a-z])/g, (letter) => letter.toUpperCase());
  }

  // A topic match is "strong" when the grant title names it or NSF filed the grant
  // under a topic program; abstract-only matches are weaker evidence.
  function isStrongReasonList(reasons) {
    return reasons.some((reason) => reason.startsWith("title:") || reason.startsWith("program:"));
  }

  function normalizeGrant(rawGrant) {
    const topicKeys = Object.keys(rawGrant.topics);
    const strongTopicKeys = topicKeys.filter((key) => isStrongReasonList(rawGrant.topics[key]));
    const phdReason = rawGrant.phdReason || data.grantTypePhdReasons[rawGrant.type];
    return { ...rawGrant, topicKeys, strongTopicKeys, phdReason };
  }

  function normalizePi(rawPi, index) {
    const grants = rawPi.grants.map(normalizeGrant);
    return {
      id: rawPi.email.toLowerCase() || `pi-${index}`,
      name: toDisplayName(rawPi.name),
      email: rawPi.email.toLowerCase(),
      institution: rawPi.institution || "",
      state: rawPi.state || "",
      department: rawPi.department || "",
      website: rawPi.website || "",
      scholar: rawPi.scholar || "",
      // "faculty", "not faculty", or "" when the lookup could not tell.
      role: rawPi.role || "",
      jobTitle: rawPi.jobTitle || "",
      grants,
      searchText: [rawPi.name, rawPi.department, rawPi.institution, stateLabel(rawPi.state), ...grants.map((grant) => `${grant.fullTitle} ${grant.programs}`)]
        .join(" ")
        .toLowerCase(),
    };
  }

  const pis = data.pis.map(normalizePi);

  // ---------------------------------------------------------------------------
  // Shortlist
  // ---------------------------------------------------------------------------

  function readShortlist() {
    try {
      return new Set(JSON.parse(localStorage.getItem(SHORTLIST_STORAGE_KEY) || "[]"));
    } catch (error) {
      return new Set();
    }
  }
  const shortlist = readShortlist();
  const shortlistListeners = [];

  // Every change is written to localStorage and announced, so sync can follow it.
  function saveShortlist() {
    localStorage.setItem(SHORTLIST_STORAGE_KEY, JSON.stringify([...shortlist]));
    for (const listener of shortlistListeners) listener();
  }

  // Used by sync to adopt the list stored on the server.
  function replaceShortlist(ids) {
    shortlist.clear();
    for (const id of ids) shortlist.add(id);
    localStorage.setItem(SHORTLIST_STORAGE_KEY, JSON.stringify([...shortlist]));
  }

  function toggleShortlist(piId) {
    if (shortlist.has(piId)) shortlist.delete(piId);
    else shortlist.add(piId);
    saveShortlist();
    return shortlist.has(piId);
  }

  function shortlistBackup() {
    return JSON.stringify({ app: "nsf-professor-finder", version: 1, savedAt: new Date().toISOString(), ids: [...shortlist] }, null, 2);
  }

  // Merges rather than replaces, so importing an old backup never loses newer picks.
  function importShortlistBackup(fileText) {
    const parsed = JSON.parse(fileText);
    const ids = Array.isArray(parsed) ? parsed : parsed.ids;
    if (!Array.isArray(ids)) throw new Error("This file has no list of professors in it.");
    const knownIds = new Set(pis.map((pi) => pi.id));
    let addedCount = 0;
    let unknownCount = 0;
    for (const id of ids) {
      if (typeof id !== "string") continue;
      if (!knownIds.has(id)) unknownCount += 1;
      if (!shortlist.has(id)) addedCount += 1;
      shortlist.add(id);
    }
    saveShortlist();
    return { addedCount, unknownCount };
  }

  // ---------------------------------------------------------------------------
  // Filtering
  // ---------------------------------------------------------------------------

  function createFilterState() {
    return {
      query: "",
      topics: new Set(),
      fields: new Set(),
      grantTypes: new Set(),
      collaborativeOnly: false,
      phdLevel: "any",
      states: new Set(),
      institutions: new Set(),
      minMonths: 0,
      minAmount: 0,
      strongOnly: false,
      shortlistOnly: false,
      includeUndergraduateColleges: false,
      includeCenters: false,
      sort: "runway",
    };
  }

  function grantMatches(grant, filters) {
    if (!filters.includeUndergraduateColleges && grant.rui) return false;
    if (!filters.includeCenters && grant.type === "center" && !filters.grantTypes.has("center")) return false;
    if (filters.topics.size && !grant.topicKeys.some((key) => filters.topics.has(key))) return false;
    if (filters.strongOnly) {
      const relevantStrong = filters.topics.size
        ? grant.strongTopicKeys.filter((key) => filters.topics.has(key))
        : grant.strongTopicKeys;
      if (!relevantStrong.length) return false;
    }
    if (filters.fields.size && !filters.fields.has(grant.field)) return false;
    if (filters.grantTypes.size && !filters.grantTypes.has(grant.type)) return false;
    if (filters.collaborativeOnly && !grant.collab) return false;
    if (!PHD_FILTER_LEVELS[filters.phdLevel].includes(grant.phd)) return false;
    if (grant.monthsLeft < filters.minMonths) return false;
    return true;
  }

  function usefulRunway(months) {
    return Math.min(months, USEFUL_RUNWAY_MONTHS);
  }

  // The grant a row leads with: the one most likely to fund a PhD student, then the
  // longest useful runway, then the strongest topic evidence.
  function pickLeadGrant(grants) {
    return grants.reduce((best, grant) => {
      const phdDifference = PHD_RANK[best.phd] - PHD_RANK[grant.phd];
      if (phdDifference !== 0) return phdDifference > 0 ? grant : best;
      const runwayDifference = usefulRunway(grant.monthsLeft) - usefulRunway(best.monthsLeft);
      if (runwayDifference !== 0) return runwayDifference > 0 ? grant : best;
      return grant.strongTopicKeys.length > best.strongTopicKeys.length ? grant : best;
    });
  }

  function evaluatePi(pi, filters, queryTerms) {
    if (filters.shortlistOnly && !shortlist.has(pi.id)) return null;
    if (filters.states.size && !filters.states.has(pi.state)) return null;
    if (filters.institutions.size && !filters.institutions.has(pi.institution)) return null;
    if (!queryTerms.every((term) => pi.searchText.includes(term))) return null;
    const matchingGrants = pi.grants.filter((grant) => grantMatches(grant, filters));
    if (!matchingGrants.length) return null;
    const matchingAmount = matchingGrants.reduce((sum, grant) => sum + (grant.amount || 0), 0);
    if (matchingAmount < filters.minAmount) return null;
    const leadGrant = pickLeadGrant(matchingGrants);
    return {
      pi,
      leadGrant,
      otherGrants: pi.grants.filter((grant) => grant !== leadGrant),
      matchingAmount,
      phdRank: PHD_RANK[leadGrant.phd],
      hasStrong: matchingGrants.some((grant) => grant.strongTopicKeys.length),
      hasCareer: matchingGrants.some((grant) => grant.type === "career"),
    };
  }

  const SORTERS = {
    runway: (a, b) =>
      usefulRunway(b.leadGrant.monthsLeft) - usefulRunway(a.leadGrant.monthsLeft) ||
      a.phdRank - b.phdRank ||
      b.hasStrong - a.hasStrong ||
      b.hasCareer - a.hasCareer ||
      a.pi.name.localeCompare(b.pi.name),
    newest: (a, b) => b.leadGrant.start.localeCompare(a.leadGrant.start) || a.pi.name.localeCompare(b.pi.name),
    amount: (a, b) => b.matchingAmount - a.matchingAmount,
    name: (a, b) => a.pi.name.localeCompare(b.pi.name),
    institution: (a, b) => a.pi.institution.localeCompare(b.pi.institution) || a.pi.name.localeCompare(b.pi.name),
  };

  function applyFilters(filters) {
    const queryTerms = filters.query.toLowerCase().split(/\s+/).filter(Boolean);
    const results = [];
    for (const pi of pis) {
      const result = evaluatePi(pi, filters, queryTerms);
      if (result) results.push(result);
    }
    return results.sort(SORTERS[filters.sort]);
  }

  // Professors per option, counted over all grants (the numbers next to each checkbox).
  function countPisBy(keyOfGrant) {
    const counts = {};
    for (const pi of pis) {
      const keys = new Set(pi.grants.flatMap(keyOfGrant));
      for (const key of keys) counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }

  function countPisByState() {
    const counts = {};
    for (const pi of pis) counts[pi.state] = (counts[pi.state] || 0) + 1;
    return counts;
  }

  // Universities with at least one listed professor, limited to the given states
  // when any are selected.
  function institutionsIn(stateCodes) {
    const counts = new Map();
    for (const pi of pis) {
      if (stateCodes.size && !stateCodes.has(pi.state)) continue;
      counts.set(pi.institution, (counts.get(pi.institution) || 0) + 1);
    }
    return [...counts].map(([name, count]) => ({ name, count })).sort((a, b) => a.name.localeCompare(b.name));
  }

  // ---------------------------------------------------------------------------
  // Export and formatting
  // ---------------------------------------------------------------------------

  function csvCell(value) {
    const text = String(value ?? "");
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function shortlistCsv() {
    const header = ["Name", "Email", "Department", "Institution", "State", "Role", "Website", "Google Scholar", "Grant", "Grant type", "PhD funding", "Collaborative", "Field", "Topics", "Starts", "Ends", "Months left at Fall 2027", "Amount USD", "Award URL"];
    const rows = pis
      .filter((pi) => shortlist.has(pi.id))
      .flatMap((pi) =>
        pi.grants.map((grant) => [
          pi.name, pi.email, pi.department, pi.institution, stateLabel(pi.state), pi.role, pi.website, pi.scholar,
          grant.fullTitle, GRANT_TYPE_LABELS[grant.type], PHD_LABELS[grant.phd], grant.collab ? "yes" : "no", FIELD_LABELS[grant.field],
          grant.topicKeys.map((key) => TOPIC_LABELS[key]).join("; "),
          grant.start, grant.end, grant.monthsLeft, grant.amount, awardUrl(grant.id),
        ])
      );
    return [header, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
  }

  function downloadFile(fileName, content, mimeType) {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([content], { type: mimeType }));
    link.download = fileName;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function awardUrl(awardId) {
    return `https://www.nsf.gov/awardsearch/showAward?AWD_ID=${awardId}`;
  }

  function formatMoney(amount) {
    if (amount >= 1e6) return `$${(amount / 1e6).toFixed(amount >= 1e7 ? 0 : 1)}M`;
    return `$${Math.round(amount / 1e3)}K`;
  }

  function formatDate(isoDate) {
    return new Date(isoDate + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" });
  }

  // Formats as "10 Oct 26". Both parsing and formatting use UTC so the day
  // cannot shift with the browser's timezone.
  function formatShortDate(isoDate) {
    const date = new Date(isoDate + "T00:00:00Z");
    const day = date.getUTCDate();
    const month = date.toLocaleDateString("en-US", { month: "short", timeZone: "UTC" });
    const twoDigitYear = date.toLocaleDateString("en-US", { year: "2-digit", timeZone: "UTC" });
    return `${day} ${month} ${twoDigitYear}`;
  }

  function escapeHtml(text) {
    return String(text ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  }

  window.NSF = {
    meta: data,
    pis,
    FIELD_LABELS,
    TOPIC_LABELS,
    TOPIC_GROUPS,
    GRANT_TYPE_LABELS,
    PHD_LABELS,
    GRANT_TYPE_PHD_LIKELIHOOD,
    OTHER_TOPIC,
    states: [...new Set(pis.map((pi) => pi.state).filter(Boolean))].sort((a, b) => stateLabel(a).localeCompare(stateLabel(b))),
    stateLabel,
    institutionsIn,
    stateCounts: countPisByState(),
    topicCounts: countPisBy((grant) => grant.topicKeys),
    fieldCounts: countPisBy((grant) => [grant.field]),
    grantTypeCounts: countPisBy((grant) => [grant.type]),
    createFilterState,
    applyFilters,
    isShortlisted: (piId) => shortlist.has(piId),
    shortlistSize: () => shortlist.size,
    shortlistIds: () => [...shortlist],
    replaceShortlist,
    onShortlistChange: (listener) => shortlistListeners.push(listener),
    toggleShortlist,
    shortlistBackup,
    importShortlistBackup,
    shortlistCsv,
    downloadFile,
    isStrongReasonList,
    awardUrl,
    formatMoney,
    formatDate,
    formatShortDate,
    escapeHtml,
  };
})();
