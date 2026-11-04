import * as fb from "./fb.js";
import * as threads from "./threads.js";
import { createScanner } from "./scanner.js";
import { mountBanner, unmountBanner } from "./banner.js";

const adapter = /threads\.(com|net)$/.test(location.hostname) ? threads : fb;
let lang = "zh";

async function boot() {
  const cfg = await chrome.runtime.sendMessage({ type: "content_config" });
  if (!cfg) return;
  lang = cfg.lang || "zh";
  const posts = new Map();
  const screenFn = async (batch) => {
    batch.forEach((p) => posts.set(p.id, p));
    const res = await chrome.runtime.sendMessage({ type: "screen", posts: batch });
    if (!res?.ok) throw Object.assign(new Error(res?.error || "screen failed"), { retryAfterMs: res?.retryAfterMs });
    return res.results;
  };
  // the click handler must stay synchronous up to sendMessage so it still counts as a user gesture
  const mount = (el, r) => mountBanner(el, r, lang, () =>
    chrome.runtime.sendMessage({ type: "open_panel", post: posts.get(r.post_id), screen: r }));
  const scanner = createScanner(adapter, screenFn, { mount, unmount: unmountBanner });
  if (cfg.enabled !== false && cfg.configured) scanner.start();
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type !== "config_changed") return;
    const cfg = msg.config;
    if (cfg.enabled && cfg.configured) { scanner.stop(); scanner.start(); }
    else scanner.stop();
    lang = cfg.lang;
    for (const el of adapter.findPosts(document)) {
      const r = scanner.results.get(el.dataset.vfId);
      if (r && r.label !== "none") mount(el, r);
    }
  });
}
boot();
