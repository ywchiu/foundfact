import * as fb from "./fb.js";
import * as threads from "./threads.js";
import { createScanner } from "./scanner.js";
import { mountBanner, unmountBanner } from "./banner.js";

const adapter = /threads\.(com|net)$/.test(location.hostname) ? threads : fb;
let lang = "zh";

async function boot() {
  const cfg = await chrome.storage.local.get(["lang", "enabled"]);
  lang = cfg.lang || "zh";
  if (cfg.enabled === false) return;
  const posts = new Map();
  const screenFn = async (batch) => {
    batch.forEach((p) => posts.set(p.id, p));
    const res = await chrome.runtime.sendMessage({ type: "screen", posts: batch });
    if (!res?.ok) throw new Error(res?.error || "screen failed");
    return res.results;
  };
  // the click handler must stay synchronous up to sendMessage so it still counts as a user gesture
  const mount = (el, r) => mountBanner(el, r, lang, () =>
    chrome.runtime.sendMessage({ type: "open_panel", post: posts.get(r.post_id), screen: r }));
  const scanner = createScanner(adapter, screenFn, { mount, unmount: unmountBanner });
  scanner.start();
  chrome.storage.onChanged.addListener((ch, area) => {
    if (area !== "local" || !ch.lang) return;
    lang = ch.lang.newValue;
    for (const el of adapter.findPosts(document)) { // re-label existing banners in the new language
      const r = scanner.results.get(el.dataset.vfId);
      if (r && r.label !== "none") mount(el, r);
    }
  });
}
boot();
