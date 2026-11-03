import { getConfig } from "./config.js";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "open_panel") {
    // sidePanel.open must be called synchronously inside the user-gesture message handler
    chrome.sidePanel.open({ tabId: sender.tab.id });
    chrome.storage.session.set({ vfPost: { post: msg.post, screen: msg.screen, at: Date.now() } });
    return false;
  }
  if (msg.type === "screen") {
    (async () => {
      try {
        const cfg = await getConfig();
        const r = await fetch(`${cfg.backendUrl}/screen`, {
          method: "POST", headers: { "content-type": "application/json" },
          body: JSON.stringify({ posts: msg.posts, provider: cfg.provider }),
        });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        sendResponse({ ok: true, results: (await r.json()).results });
      } catch (e) {
        sendResponse({ ok: false, error: String(e) });
      }
    })();
    return true; // async response
  }
  return false;
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});
