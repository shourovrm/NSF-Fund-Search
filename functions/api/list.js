// Storage for "My list" sync: GET and PUT /api/list?key=<fingerprint>.
// The browser sends a SHA-256 fingerprint of the user's passphrase as the key,
// so the passphrase itself never reaches this server.

const KEY_PATTERN = /^[0-9a-f]{64}$/;
const MAX_SAVED_PROFESSORS = 2000;
const MAX_ID_LENGTH = 200;
const MAX_BODY_BYTES = 256 * 1024;

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

function readKey(request) {
  const key = new URL(request.url).searchParams.get("key") || "";
  return KEY_PATTERN.test(key) ? key : null;
}

function isValidIdList(ids) {
  return (
    Array.isArray(ids) &&
    ids.length <= MAX_SAVED_PROFESSORS &&
    ids.every((id) => typeof id === "string" && id.length > 0 && id.length <= MAX_ID_LENGTH)
  );
}

export async function onRequestGet({ request, env }) {
  const key = readKey(request);
  if (!key) return jsonResponse({ error: "Missing or malformed key." }, 400);
  const stored = await env.SHORTLISTS.get(`list:${key}`, "json");
  return jsonResponse(stored || { ids: [], updatedAt: null });
}

export async function onRequestPut({ request, env }) {
  const key = readKey(request);
  if (!key) return jsonResponse({ error: "Missing or malformed key." }, 400);

  const declaredLength = Number(request.headers.get("content-length") || 0);
  if (declaredLength > MAX_BODY_BYTES) return jsonResponse({ error: "List is too large." }, 413);
  const bodyText = await request.text();
  if (new TextEncoder().encode(bodyText).length > MAX_BODY_BYTES) {
    return jsonResponse({ error: "List is too large." }, 413);
  }

  let body;
  try {
    body = JSON.parse(bodyText);
  } catch (error) {
    return jsonResponse({ error: "Body must be JSON." }, 400);
  }
  if (!isValidIdList(body?.ids)) {
    return jsonResponse({ error: `Body must be {"ids": [...]} with at most ${MAX_SAVED_PROFESSORS} short strings.` }, 400);
  }

  const record = { ids: [...new Set(body.ids)], updatedAt: new Date().toISOString() };
  await env.SHORTLISTS.put(`list:${key}`, JSON.stringify(record));
  return jsonResponse(record);
}
