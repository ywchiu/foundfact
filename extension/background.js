import { getConfig, publicConfig, secureStorage } from "./config.js";
import { createScreenClient } from "./screen-client.js";
import { verifyDirect } from "./direct-verify.js";
import { fingerprint, reserveUsage, failure } from "./direct-api.js";
const secured = secureStorage();
const screen = createScreenClient({ storage: chrome.storage.session });
const social = sender => { try { return /^https?:$/.test(new URL(sender.url || sender.tab?.url).protocol) && /(^|\.)(facebook\.com|threads\.com|threads\.net)$/.test(new URL(sender.url || sender.tab?.url).hostname); } catch { return false; } };
function validPost(p) { return p && typeof p.id === "string" && p.id.length <= 200 && typeof p.text === "string" && p.text.length <= 20000 && ["facebook", "threads"].includes(p.platform) && ["links", "link_domains", "image_urls"].every(k => p[k] == null || Array.isArray(p[k]) && p[k].length <= 30 && p[k].every(s => typeof s === "string" && s.length < 10000)); }
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!social(sender)) return false;
  if (msg.type === "content_config") { secured.then(getConfig).then(cfg => sendResponse(publicConfig(cfg))); return true; }
  if (msg.type === "open_panel" && validPost(msg.post)) {
    // Keep this synchronous: Chrome requires a real user gesture to open the native panel.
    chrome.sidePanel.open({ tabId: sender.tab.id }).catch(() => {});
    chrome.storage.session.set({ vfPost: { post: msg.post, screen: msg.screen, windowId: sender.tab.windowId, at: Date.now() } });
    return false;
  }
  if (msg.type === "screen") {
    (async () => {
      try {
        if (!Array.isArray(msg.posts) || !msg.posts.length || msg.posts.length > 20 || !msg.posts.every(validPost)) throw failure("Invalid posts", 60000);
        if (!sender.tab?.active) throw failure("Feed screening paused in background tab", 60000);
        const cfg = await getConfig();
        if (!cfg.enabled) throw failure("Feed screening disabled", 60000);
        sendResponse({ ok: true, results: await screen(msg.posts, cfg) });
      } catch (e) { sendResponse({ ok: false, error: e.message, retryAfterMs: e.retryAfterMs || 5000 }); }
    })();
    return true;
  }
  return false;
});
// Content scripts receive only public settings, even after a key is changed.
chrome.storage.local.onChanged.addListener(async changes => {
  if (!["enabled", "lang", "jevKey", "jevService"].some(k => k in changes)) return;
  const cfg = publicConfig(await getConfig());
  for (const tab of await chrome.tabs.query({ url: ["*://*.facebook.com/*", "*://*.threads.com/*", "*://*.threads.net/*"] })) {
    chrome.tabs.sendMessage(tab.id, { type: "config_changed", config: cfg }).catch(() => {});
  }
});
let verifying = null;
chrome.runtime.onConnect.addListener(port => {
  // Only the extension's trusted native panel can start full checks; web content cannot.
  if (port.name !== "verify" || port.sender?.url !== chrome.runtime.getURL("sidepanel/index.html")) { port.disconnect(); return; }
  const controller = new AbortController(); let started = false;
  const emit = (type, data) => { if (!controller.signal.aborted) port.postMessage({ type, data }); };
  port.onDisconnect.addListener(() => controller.abort());
  port.onMessage.addListener(async input => {
    if (started) return; started = true;
    let ownLock = false;
    try {
      if (!validPost(input.post)) throw new Error("Invalid post");
      if (verifying && !verifying.signal.aborted) throw failure("Another full check is running. Please wait.");
      verifying = controller; ownLock = true;
      const cfg = await getConfig();
      if (!cfg.museKey) throw new Error("Add your Meta Muse API key in Settings / 請先在設定填入 Muse 金鑰");
      const scope = await fingerprint(cfg.museKey);
      const key = await fingerprint([scope, input.post.text, input.post.image_urls, input.post.links, input.post.link_domains, input.lang, input.pressure]);
      const state = (await chrome.storage.session.get("vfDirectVerifyState")).vfDirectVerifyState || { cache: {}, usage: {}, cooldowns: {} };
      for (const [k, v] of Object.entries(state.cache)) if (Date.now() - v.at >= 86400000) delete state.cache[k];
      const cached = state.cache[key];
      if (cached) {
        cached.steps.forEach(e => emit("step", e));
        emit("report", { ...cached.report, post_id: input.post.id }); emit("done", {}); return;
      }
      if (Date.now() < (state.cooldowns[scope] || 0)) throw failure("Muse is paused after a provider error. Please wait.", state.cooldowns[scope] - Date.now());
      reserveUsage(state, scope, 1, cfg.verifyHourlyLimit);
      await chrome.storage.session.set({ vfDirectVerifyState: state });
      const steps = [];
      try {
        const { report, cacheable } = await verifyDirect(cfg, input, { signal: controller.signal,
          onStep: e => { steps.push(e); emit("step", e); }, onReport: r => emit("report", r) });
        if (cacheable) state.cache[key] = { at: Date.now(), steps, report };
        while (Object.keys(state.cache).length > 50) delete state.cache[Object.keys(state.cache)[0]];
        await chrome.storage.session.set({ vfDirectVerifyState: state }); emit("done", {});
      } catch (e) {
        if (!controller.signal.aborted && e.retryAfterMs) { state.cooldowns[scope] = Date.now() + e.retryAfterMs; await chrome.storage.session.set({ vfDirectVerifyState: state }); }
        throw e;
      }
    } catch (e) { if (!controller.signal.aborted) emit("error", e.message); }
    finally { if (ownLock && verifying === controller) verifying = null; }
  });
});
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});
