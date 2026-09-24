// Keeps "My list" the same across devices through /api/list on the hosted site.
// The list is stored under a SHA-256 fingerprint of a passphrase the user picks;
// every device that enters the same passphrase shares one list.
(function () {
  "use strict";

  const SYNC_KEY_STORAGE = "nsf-sync-key";
  // Set while a local change has not reached the server yet.
  const PENDING_STORAGE = "nsf-sync-pending";
  // Batches quick successive stars into one write (the free tier allows 1,000 a day).
  const PUSH_DELAY_MS = 1500;
  const MIN_PASSPHRASE_LENGTH = 12;

  // The API and crypto.subtle exist only when the page is served over https or
  // from localhost, not when index.html is opened from disk.
  const isAvailable = location.protocol === "https:" || ["localhost", "127.0.0.1"].includes(location.hostname);

  let pushTimer = 0;
  let statusListener = () => {};

  function syncKey() {
    return localStorage.getItem(SYNC_KEY_STORAGE);
  }

  function reportStatus(message, isError = false) {
    statusListener(message, isError);
  }

  async function fingerprint(passphrase) {
    const bytes = new TextEncoder().encode(`nsf-fund-search:${passphrase.trim()}`);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  async function fetchRemoteIds(key) {
    const response = await fetch(`/api/list?key=${key}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`server answered ${response.status}`);
    return (await response.json()).ids;
  }

  async function pushNow() {
    const key = syncKey();
    if (!key) return;
    try {
      const response = await fetch(`/api/list?key=${key}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ ids: NSF.shortlistIds() }),
      });
      if (!response.ok) throw new Error(`server answered ${response.status}`);
      localStorage.removeItem(PENDING_STORAGE);
      reportStatus(`Synced: ${NSF.shortlistSize()} professor${NSF.shortlistSize() === 1 ? "" : "s"} saved online.`);
    } catch (error) {
      reportStatus("Could not reach the sync server. Your change is saved here and will sync the next time the page opens.", true);
    }
  }

  function schedulePush() {
    if (!syncKey()) return;
    localStorage.setItem(PENDING_STORAGE, "1");
    clearTimeout(pushTimer);
    pushTimer = setTimeout(pushNow, PUSH_DELAY_MS);
  }

  // Merges this browser's list with the one stored online, so turning sync on
  // never loses picks from either side.
  async function connect(passphrase) {
    if (passphrase.trim().length < MIN_PASSPHRASE_LENGTH) {
      throw new Error(`Use at least ${MIN_PASSPHRASE_LENGTH} characters, for example four random words.`);
    }
    const key = await fingerprint(passphrase);
    const remoteIds = await fetchRemoteIds(key);
    const localCount = NSF.shortlistSize();
    NSF.replaceShortlist([...new Set([...NSF.shortlistIds(), ...remoteIds])]);
    localStorage.setItem(SYNC_KEY_STORAGE, key);
    await pushNow();
    return { addedFromOnline: NSF.shortlistSize() - localCount };
  }

  function disconnect() {
    clearTimeout(pushTimer);
    localStorage.removeItem(SYNC_KEY_STORAGE);
    localStorage.removeItem(PENDING_STORAGE);
    reportStatus("Sync is off. Your list stays in this browser.");
  }

  // On page load: if the last change never reached the server, this browser's
  // list wins; otherwise the online list wins, so removals made on another
  // device carry over here.
  async function startup() {
    if (!isAvailable || !syncKey()) return;
    if (localStorage.getItem(PENDING_STORAGE)) {
      await pushNow();
      return;
    }
    try {
      NSF.replaceShortlist(await fetchRemoteIds(syncKey()));
      reportStatus(`Synced: ${NSF.shortlistSize()} professor${NSF.shortlistSize() === 1 ? "" : "s"} saved online.`);
    } catch (error) {
      reportStatus("Could not reach the sync server. Showing the list saved in this browser.", true);
    }
  }

  NSF.onShortlistChange(schedulePush);

  window.NSFSync = {
    isAvailable,
    isConnected: () => Boolean(syncKey()),
    connect,
    disconnect,
    startup,
    onStatus: (listener) => { statusListener = listener; },
  };
})();
