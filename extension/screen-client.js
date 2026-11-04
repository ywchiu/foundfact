import { JEV, QUESTIONS, apiRequest, fingerprint, failure, reserveUsage } from "./direct-api.js";
import { loadLocalData, findBlocklistHit, domainsOf } from "./local-data.js";
const STATE_KEY = "vfDirectScreenState", TTL = 24 * 3600000;
export function createScreenClient({ fetchFn = fetch, storage, now = Date.now, loadData = loadLocalData } = {}) {
  let state = { cache: {}, cooldowns: {}, usage: {} }, ready, queue = Promise.resolve();
  const save = async () => { if (storage) await storage.set({ [STATE_KEY]: state }); };
  async function run(posts, cfg) {
    ready ||= (async () => { const saved = (await storage?.get(STATE_KEY))?.[STATE_KEY]; if (saved?.cache && saved?.cooldowns) state = saved; })();
    await ready;
    const service = JEV[cfg.jevService];
    if (!service) throw failure("Choose a Jev service in Settings.", 60000);
    const scope = await fingerprint([cfg.jevService, cfg.jevKey]);
    const keys = await Promise.all(posts.map(p => fingerprint([scope, p.platform, p.author, p.text, domainsOf(p)])));
    for (const [k, v] of Object.entries(state.cache)) if (now() - v.at >= TTL) delete state.cache[k];
    const { blocklist } = await loadData();
    for (let i = 0; i < posts.length; i++) {
      if (state.cache[keys[i]]) continue;
      const post = posts[i], start = now(), hit = findBlocklistHit(post, blocklist);
      let result = { post_id: post.id, label: "high", p_scam: 1, p_claim: 0, pressure: null, scam_type: null, similar: [], answered_by: "blocklist", provider: "jev", link_hit: hit };
      if (!hit) {
        if (!cfg.jevKey) throw failure("Add your Jev API key in FoundFact Settings to screen your feed.", 60000);
        const cooldown = state.cooldowns[scope] || 0;
        if (now() < cooldown) throw failure("Jev screening paused after a provider error", cooldown - now());
        reserveUsage(state, scope, 1, cfg.screenHourlyLimit, now());
        await save();
        try {
          const response = await apiRequest(service.url, cfg.jevKey, { model: service.model, state: {
            platform: post.platform, author: post.author, text: post.text.slice(0, 4000), link_domains: domainsOf(post),
          }, questions: QUESTIONS }, { fetchFn });
          const { answers: a } = await response.json();
          const p = Number(a?.is_scam_like?.noul), c = Number(a?.has_checkable_claim?.noul);
          if (![p, c].every(v => Number.isFinite(v) && v >= 0 && v <= 1)) throw new Error("Invalid Jev response");
          const probs = a.pressure?.probabilities;
          result = { ...result, label: p >= .8 ? "high" : p >= .5 ? "check" : "none", p_scam: p, p_claim: c,
            pressure: probs ? Math.round(Object.entries(probs).reduce((n, [k, v]) => n + Number(k) * Number(v), 0)) : null, answered_by: "jev" };
          state.cooldowns[scope] = 0;
        } catch (e) {
          state.cooldowns[scope] = now() + (e.retryAfterMs || 5000);
          await save(); throw e; // Never fall back to Muse, the website, or another paid provider.
        }
      }
      state.cache[keys[i]] = { at: now(), result: { ...result, latency_ms: now() - start } };
      while (Object.keys(state.cache).length > 300) delete state.cache[Object.keys(state.cache)[0]];
      await save();
    }
    return posts.map((post, i) => ({ ...state.cache[keys[i]].result, post_id: post.id }));
  }
  return (posts, cfg) => { const result = queue.then(() => run(posts, cfg)); queue = result.catch(() => {}); return result; };
}
