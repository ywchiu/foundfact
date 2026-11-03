import { t } from "../shared/i18n.js";
import { renderError, renderReport, renderSkeleton, renderSteps, streamVerify } from "../shared/report.js";
import { getConfig } from "../config.js";

const $ = (s) => document.getElementById(s);
let current = 0;
let lastItem = null;

async function show(item) {
  const cfg = await getConfig();
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
  const run = ++current;
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
  await streamVerify(cfg.backendUrl, { post: item.post, lang, pressure: item.screen?.pressure ?? null }, {
    onStep: (e) => { if (run !== current) return; steps.push(e); renderSteps($("steps"), steps, lang); },
    onReport: (r) => { if (run === current) renderReport($("report"), r, lang); },
    onError: (key) => {
      if (run === current) renderError($("report"), key, lang);
    },
  });
}

$("lang").addEventListener("click", async () => {
  const { lang } = await getConfig();
  await chrome.storage.local.set({ lang: lang === "en" ? "zh" : "en" });
});
// a language switch re-runs the current verification so the agent answers in that language
chrome.storage.local.onChanged.addListener((ch) => { if (ch.lang) show(lastItem); });
chrome.storage.session.get("vfPost").then(({ vfPost }) => show(vfPost));
chrome.storage.session.onChanged.addListener((ch) => { if (ch.vfPost?.newValue) show(ch.vfPost.newValue); });
