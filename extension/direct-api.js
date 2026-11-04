// No FoundFact server, proxy, or remotely supplied endpoint is used by the extension.
export const JEV = {
  openrouter: { url: "https://openrouter.ai/api/alpha/decisions", model: "typesafe/jev-1.14" },
  typesafe: { url: "https://api.typesafe.ai/v1/systemone", model: "jev-latest" },
};
export const MUSE_BASE = "https://api.meta.ai/v1";
export const MUSE_MODEL = "muse-spark-1.3";
export const QUESTIONS = {
  is_scam_like: { type: "noul", instructions: "Does this social media post show scam tactics: guaranteed returns, impersonating a celebrity/government/brand, pushing readers to LINE/private chat, suspicious links, urgent pressure to pay/act, or too-good-to-be-true jobs (easy remote/home work, high pay, no experience, apply by private message, no named company or address)? Judge only from the post itself." },
  has_checkable_claim: { type: "noul", instructions: "Does this post state a specific factual claim that could be checked against outside sources (who said/did what, official announcements, numbers, events)?" },
  pressure: { type: "score", instructions: "How much urgency or pressure language does this post use?", criteria: ["No pressure", "Mild promotional language", "Clear urgency or guaranteed gains", "Extreme pressure: deadlines, threats, or demands to pay/transfer now"] },
};
export async function fingerprint(value) {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(JSON.stringify(value)));
  return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, "0")).join("");
}
export function failure(message, retryAfterMs = 5000) { return Object.assign(new Error(message), { retryAfterMs }); }
export async function apiRequest(url, key, body, { fetchFn = fetch, signal, timeout = 30000 } = {}) {
  if (!key) throw failure("Missing API key. Open FoundFact Settings.", 60000);
  const response = await fetchFn(url, { method: "POST", credentials: "omit", redirect: "error",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` }, body: JSON.stringify(body),
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(timeout)]) : AbortSignal.timeout(timeout) });
  if (!response.ok) {
    // Provider bodies can echo credentials or private input; never surface or log them.
    const h = response.headers.get("Retry-After");
    const retry = h ? (/^\d+(\.\d+)?$/.test(h) ? Number(h) * 1000 : Date.parse(h) - Date.now()) : NaN;
    throw failure(`Provider HTTP ${response.status}${[401, 403].includes(response.status) ? ": check your API key in Settings" : ""}`,
      Number.isFinite(retry) && retry >= 0 ? Math.max(1000, retry) : response.status === 429 ? 60000 : [401, 403].includes(response.status) ? 300000 : 5000);
  }
  return response;
}
// Charged locally before a provider request; rejected batches consume nothing. 0 disables this cap.
export function reserveUsage(state, scope, count, limit, now = Date.now()) {
  state.usage ||= {};
  const hits = (state.usage[scope] || []).filter(t => now - t < 3600000);
  if (limit > 0 && hits.length + count > limit) {
    const index = Math.max(0, hits.length + count - limit - 1);
    throw failure("Your local hourly limit was reached. Change it in Settings.", Math.max(1000, (hits[index] ?? now) + 3600000 - now));
  }
  // Unlimited mode needs no per-call history. Caps are local safety settings, not a server allowance.
  state.usage[scope] = limit > 0 ? [...hits, ...Array(count).fill(now)] : hits;
}
