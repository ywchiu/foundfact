import { t } from "../shared/i18n.js";
import { renderError, renderReport, renderSkeleton, renderSteps } from "../shared/report.js";
import { getConfig } from "../config.js";

const $ = (s) => document.getElementById(s);
let current = 0;
let lastItem = null;
let verificationPort;
const panelWindow = await chrome.windows.getCurrent();

async function show(item) {
  if (item?.windowId != null && item.windowId !== panelWindow.id) return;
  const run = ++current;
  verificationPort?.disconnect();
  verificationPort = null;
  const cfg = await getConfig();
  if (run !== current) return;
  const lang = cfg.lang;
  $("title").textContent = t("brand", lang);
  $("opts").textContent = lang === "en" ? "Settings" : "設定";
  $("lang").textContent = lang === "en" ? "中文" : "EN";
  document.documentElement.lang = lang === "en" ? "en" : "zh-Hant";
  lastItem = item;
  if (!item?.post) {
    $("empty").textContent = lang === "en"
      ? "Click “Why?” on a flagged post to start a verification."
      : "在動態牆上點擊紅條的「看原因」，Agent 就會開始查證。";
    return;
  }
  $("empty").hidden = true;
  const p = $("post");
  p.hidden = false;
  const b = document.createElement("b");
  b.textContent = item.post.author ? `${item.post.author}\n` : "";
  p.replaceChildren(b, document.createTextNode(item.post.text));
  $("stepsTitle").hidden = false;
  $("stepsTitle").textContent = t("steps", lang);
  renderSkeleton($("report"));
  const steps = [];
  renderSteps($("steps"), steps, lang);
  const port = chrome.runtime.connect({ name: "verify" });
  verificationPort = port;
  // Chrome may suspend a service worker during a long search. Port messages keep the active run alive.
  const heartbeat = setInterval(() => { try { port.postMessage({ type: "ping" }); } catch { clearInterval(heartbeat); } }, 20000);
  let finished = false;
  port.onDisconnect.addListener(() => {
    clearInterval(heartbeat);
    if (!finished && run === current) {
      const detail = document.createElement("p"); detail.className = "vf-error-box";
      detail.textContent = lang === "en" ? "The check stopped. Click Why to retry." : "查證已停止，請再點一次「看原因」。";
      $("report").replaceChildren(detail);
    }
  });
  port.onMessage.addListener(({ type, data }) => {
    if (run !== current) return;
    if (type === "step") { steps.push(data); renderSteps($("steps"), steps, lang); }
    if (type === "report") renderReport($("report"), data, lang);
    if (type === "done" || type === "error") { finished = true; clearInterval(heartbeat); }
    if (type === "error") {
      renderError($("report"), "err_generic", lang);
      const detail = document.createElement("p"); detail.textContent = data; $("report").append(detail);
    }
  });
  port.postMessage({ post: item.post, lang, pressure: item.screen?.pressure ?? null });
}

$("lang").addEventListener("click", async () => {
  const { lang } = await getConfig();
  await chrome.storage.local.set({ lang: lang === "en" ? "zh" : "en" });
});
// a language switch re-runs the current verification so the agent answers in that language
chrome.storage.local.onChanged.addListener((ch) => { if (ch.lang) show(lastItem); });
chrome.storage.session.get("vfPost").then(({ vfPost }) => show(vfPost));
chrome.storage.session.onChanged.addListener((ch) => { if (ch.vfPost?.newValue) show(ch.vfPost.newValue); });

window.addEventListener("pagehide", () => verificationPort?.disconnect());
