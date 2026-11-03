// Red/amber banner injected at the top of a flagged post, isolated in Shadow DOM.
import { t } from "../shared/i18n.js";

const CSS = `
:host { all: initial; display: block; }
.bar { display: flex; align-items: center; justify-content: space-between; gap: 10px;
  font: 600 13px/1.4 -apple-system, BlinkMacSystemFont, "PingFang TC", "Noto Sans TC", sans-serif;
  padding: 8px 12px; border-radius: 8px 8px 0 0; margin: 0 0 6px; }
.high { background: #e53935; color: #fff; }
.check { background: #fff3df; color: #8a4f00; border-bottom: 1px solid #f3cf8a; }
.side { display: flex; align-items: center; gap: 8px; white-space: nowrap; }
.brand { font-weight: 500; opacity: .85; font-size: 11.5px; }
button { all: unset; cursor: pointer; font-weight: 700; padding: 3px 10px; border-radius: 999px;
  background: rgba(255,255,255,.95); color: #b71c1c; font-size: 12px; }
.check button { background: #8a4f00; color: #fff; }
button:focus-visible { outline: 2px solid #1f5eff; outline-offset: 2px; }
`;

export function hasBanner(el) {
  return !!el.querySelector(":scope > .vf-host");
}

export function unmountBanner(el) {
  el.querySelectorAll(":scope > .vf-host").forEach((h) => h.remove());
  el.style.removeProperty("box-shadow");
}

export function mountBanner(el, result, lang, onWhy) {
  // identical banner already there: touch nothing, or the feed observer sees our own mutation and rescans
  const key = [result.post_id, result.label, result.scam_type, result.answered_by, result.link_hit?.domain, lang].join("|");
  const existing = el.querySelector(":scope > .vf-host");
  if (existing && existing.dataset.vfKey === key) return;
  unmountBanner(el);
  const host = document.createElement("div");
  host.className = "vf-host";
  host.dataset.vfKey = key;
  const root = host.attachShadow({ mode: "open" });
  const style = document.createElement("style");
  style.textContent = CSS;
  const high = result.label === "high";
  const bar = document.createElement("div");
  bar.className = `bar ${high ? "high" : "check"}`;
  bar.setAttribute("role", "note");
  const msg = document.createElement("span");
  const type = result.scam_type ? t(`type_${result.scam_type}`, lang) : "";
  const linkHit = result.answered_by === "blocklist" && result.link_hit?.domain;
  msg.textContent = "⚠ " + (linkHit ? t("banner_link", lang, { d: result.link_hit.domain })
    : high ? t("banner_type", lang, { type: type || (lang === "en" ? "a" : "") }) : t("banner_check", lang));
  const side = document.createElement("span");
  side.className = "side";
  const brand = document.createElement("span");
  brand.className = "brand";
  brand.textContent = t("by", lang);
  const btn = document.createElement("button");
  btn.type = "button";
  btn.textContent = `${t("why", lang)} →`;
  btn.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); onWhy(); });
  side.append(brand, btn);
  bar.append(msg, side);
  root.append(style, bar);
  el.prepend(host);
  el.style.setProperty("box-shadow", high ? "inset 5px 0 0 #e53935" : "inset 5px 0 0 #f3a73b");
}
