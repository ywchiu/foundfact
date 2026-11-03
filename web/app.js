import { t } from "/shared/i18n.js?v=r8";
import { icon } from "/shared/icons.js?v=r8";
import { renderError, renderReport, renderSkeleton, renderStage1, renderSteps, screen, streamVerify } from "/shared/report.js?v=r8";
import { COPY } from "/copy.js?v=r8";

const EXAMPLES = {
  zh: {
    sms: "【中華郵政】您的包裹因地址不完整無法投遞，請於24小時內點擊連結更新資料，逾期將退回：https://post-tw.cc/u8x",
    invest: "台積電董事長魏哲家親自帶你操作！保證月報酬30%，名額只剩最後20位，立即加入LINE群組領取飆股名單 👉 lin.ee/abc123",
    cs: "您好，這裡是蝦皮客服。系統顯示您誤升級為批發商會員，每月將自動扣款 6,800 元，請加入官方LINE客服 @shopee-tw 辦理解除分期。",
  },
  en: {
    sms: "USPS: Your package could not be delivered because the address is incomplete. Update your details within 24 hours or it will be returned: https://usps-redelivery.cc/u8x",
    invest: "Trade alongside Nvidia CEO Jensen Huang! Guaranteed 30% monthly returns. Only 20 spots left. Join our WhatsApp group now for free stock picks 👉 chat-vip-invest.cc/abc123",
    cs: "Hello, this is Amazon Customer Service. Your account was mistakenly upgraded to a wholesale membership and will be charged $299 every month. Message our support line on WhatsApp +1 (302) 555-0148 to cancel.",
  },
};
const MIN_CHARS = 8;
const IMG_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];
const MAX_DATA_URL = 700_000; // nginx accepts 1 MB per request; leave room for the JSON around it
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

const $ = (s) => document.querySelector(s);
const text = $("#text");
const err = $("#err");
let lang = "en";
try { if (localStorage.getItem("vf-lang") === "zh") lang = "zh"; } catch { /* storage blocked */ }
let busy = false;
let image = null; // data URL of the attached screenshot, already shrunk
let exKey = null; // which example is in the box, so a language switch can swap it

const c = (key) => COPY[lang][key] ?? COPY.zh[key] ?? "";

function fillIcons() {
  document.querySelectorAll("[data-icon]").forEach((el) => {
    if (!el.firstChild) el.append(icon(el.dataset.icon, el.classList.contains("ext-icon") || el.classList.contains("drop-icon") ? 24 : 20));
  });
}

function buildTagline() {
  const p = $("#tagline");
  const s = c("tagline");
  // zh has no spaces: split per character; en: per word
  const parts = lang === "zh" ? [...s] : s.split(/(\s+)/);
  p.replaceChildren(...parts.map((w) => {
    if (/^\s+$/.test(w)) return document.createTextNode(w);
    const span = document.createElement("span");
    span.className = "w";
    span.textContent = w;
    return span;
  }));
  p.setAttribute("aria-label", s);
  updateTagline();
}

function updateTagline() {
  const p = $("#tagline");
  const words = p.querySelectorAll(".w");
  if (reduced) { words.forEach((w) => w.classList.add("on")); return; }
  const r = p.getBoundingClientRect();
  const vh = innerHeight;
  // 0 when the paragraph top reaches 85% of the viewport, 1 when its bottom reaches 45%
  const progress = Math.min(1, Math.max(0, (vh * 0.85 - r.top) / (r.height + vh * 0.4)));
  const lit = Math.round(progress * words.length);
  words.forEach((w, i) => w.classList.toggle("on", i < lit));
}

function applyLang() {
  document.documentElement.lang = lang === "zh" ? "zh-Hant" : "en";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n, lang); });
  document.querySelectorAll("[data-c]").forEach((el) => { el.textContent = c(el.dataset.c); });
  text.placeholder = t("placeholder", lang);
  $("#rm-img").setAttribute("aria-label", t("remove_image", lang));
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  document.title = c("title");
  if (!err.hidden) showErr(err.dataset.key);
  buildTagline();
}

function showErr(key) {
  if (key) err.dataset.key = key; else delete err.dataset.key;
  err.textContent = key ? t(key, lang)
    : lang === "zh" ? `請貼上至少 ${MIN_CHARS} 個字的內容，或加入一張圖片。` : `Paste at least ${MIN_CHARS} characters or add an image to check.`;
  err.hidden = false;
  text.setAttribute("aria-invalid", "true");
}
// Shrink an image in the browser so it fits the request limit: at most 1600 px on the long side, JPEG,
// lowering quality and then size until the data URL is under MAX_DATA_URL.
async function shrink(file) {
  const bmp = await createImageBitmap(file);
  let scale = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  let q = 0.85;
  for (let i = 0; i < 8; i++) {
    const c = document.createElement("canvas");
    c.width = Math.round(bmp.width * scale);
    c.height = Math.round(bmp.height * scale);
    const g = c.getContext("2d");
    g.fillStyle = "#fff";
    g.fillRect(0, 0, c.width, c.height);
    g.drawImage(bmp, 0, 0, c.width, c.height);
    const url = c.toDataURL("image/jpeg", q);
    if (url.length <= MAX_DATA_URL) return url;
    if (q > 0.55) q -= 0.15; else scale *= 0.75;
  }
  throw new Error("too large");
}

async function attach(file) {
  if (!file) return;
  if (!IMG_TYPES.includes(file.type)) { showErr("image_bad"); return; }
  try {
    image = await shrink(file);
  } catch {
    image = null;
    showErr("err_image");
    return;
  }
  const thumb = $("#thumb");
  thumb.querySelector("img").src = image;
  thumb.hidden = false;
  $("#add-img").hidden = true;
  clearErr();
}

function detach() {
  image = null;
  $("#thumb").hidden = true;
  $("#thumb img").removeAttribute("src");
  $("#add-img").hidden = false;
  $("#file").value = "";
}

function clearErr() { err.hidden = true; text.removeAttribute("aria-invalid"); }

async function loadProviders() {
  try {
    const avail = await (await fetch("/providers")).json();
    const sel = $("#provider");
    for (const opt of sel.options) opt.disabled = !avail[opt.value];
    if (sel.selectedOptions[0]?.disabled) {
      const first = [...sel.options].find((o) => !o.disabled);
      if (first) sel.value = first.value;
    }
  } catch { /* keep defaults */ }
}

async function run() {
  const body = text.value.trim();
  if (busy) return;
  if (body.length < MIN_CHARS && !image) { showErr(); text.focus(); return; }
  clearErr();
  busy = true;
  const go = $("#go");
  go.disabled = true;
  go.setAttribute("aria-busy", "true");
  $("#empty").hidden = true;
  const post = { id: `web-${Date.now()}`, platform: "web", text: body, image_urls: image ? [image] : [] };
  const steps = [];
  $("#stage1").replaceChildren();
  renderSteps($("#steps"), steps, lang);
  renderSkeleton($("#report"));
  if (matchMedia("(max-width: 960px)").matches) {
    $(".panel").scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
  }
  let pressure = null;
  try {
    if (body.length < MIN_CHARS) throw new Error("image only: the first pass reads text"); // skip stage 1
    const s1 = await screen("", { ...post, image_urls: [] }, $("#provider").value);
    pressure = s1.pressure;
    renderStage1($("#stage1"), s1, lang);
  } catch { /* the first pass is optional on the web */ }
  let done = false;
  await streamVerify("", { post, lang, pressure }, {
    onStep: (e) => { steps.push(e); renderSteps($("#steps"), steps, lang); },
    onReport: (r) => { done = true; renderReport($("#report"), r, lang); },
    onError: (key) => { done = true; renderError($("#report"), key, lang); },
  });
  if (!done) renderError($("#report"), "err_generic", lang);
  busy = false;
  go.disabled = false;
  go.removeAttribute("aria-busy");
}

function reveal() {
  const els = document.querySelectorAll(".reveal");
  if (reduced || !("IntersectionObserver" in window)) { els.forEach((el) => el.classList.add("shown")); return; }
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { e.target.classList.add("shown"); io.unobserve(e.target); }
  }, { threshold: 0.12, rootMargin: "0px 0px -8% 0px" });
  els.forEach((el) => io.observe(el));
}

text.addEventListener("input", () => {
  $("#count").textContent = `${text.value.length} / 4000`;
  if (!err.hidden && !err.dataset.key && text.value.trim().length >= MIN_CHARS) clearErr();
});
document.querySelectorAll("[data-ex]").forEach((b) => b.addEventListener("click", () => {
  exKey = b.dataset.ex;
  text.value = EXAMPLES[lang][exKey];
  text.dispatchEvent(new Event("input"));
  text.focus();
}));
document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => {
  const prev = lang;
  lang = b.dataset.lang;
  if (exKey && text.value === EXAMPLES[prev][exKey]) {
    text.value = EXAMPLES[lang][exKey];
    text.dispatchEvent(new Event("input"));
  }
  try { localStorage.setItem("vf-lang", lang); } catch { /* storage blocked */ }
  applyLang();
}));
$("#go").addEventListener("click", run);
$("#add-img").addEventListener("click", () => $("#file").click());
$("#file").addEventListener("change", (e) => attach(e.target.files[0]));
$("#rm-img").addEventListener("click", () => { detach(); $("#add-img").focus(); });
text.addEventListener("paste", (e) => {
  const f = [...(e.clipboardData?.files ?? [])].find((x) => x.type.startsWith("image/"));
  if (f) { e.preventDefault(); attach(f); }
});
for (const zone of [text, $("#add-img")]) {
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag"));
  zone.addEventListener("drop", (e) => {
    const f = [...(e.dataTransfer?.files ?? [])].find((x) => x.type.startsWith("image/"));
    zone.classList.remove("drag");
    if (f) { e.preventDefault(); attach(f); }
  });
}
text.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(); });
let ticking = false;
addEventListener("scroll", () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => { updateTagline(); ticking = false; });
}, { passive: true });

document.documentElement.classList.add("js");
fillIcons();
applyLang();
reveal();
loadProviders();
