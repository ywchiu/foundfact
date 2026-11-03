// Shared report renderer for the web app and the extension side panel. Never uses innerHTML.
import { t } from "./i18n.js?v=r8";
import { icon } from "./icons.js?v=r8";

const STEP_ORDER = ["image", "extract", "local", "search", "judge", "conclude"];
const STEP_ICON = { extract: "text-aa", local: "stack", image: "image", search: "magnifying-glass", judge: "scales",
                    conclude: "seal-check" };
const RISK_ICON = { high: "warning-circle", check: "flag", low: "check-circle" };

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null) continue;
    if (k === "class") el.className = v;
    else if (k === "dataset") Object.assign(el.dataset, v);
    else el.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

function safeUrl(u) {
  try {
    const url = new URL(u);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function link(url, text) {
  const href = safeUrl(url);
  return href ? h("a", { href, target: "_blank", rel: "noopener noreferrer" }, text) : h("span", {}, text);
}

export function renderSteps(container, events, lang = "zh") {
  const byStep = new Map();
  for (const e of events) {
    const cur = byStep.get(e.step) || { status: "running", head: "", log: [] };
    if (e.status === "running") {
      if (!cur.head) cur.head = e.detail;
      else cur.log.push(e.detail);
    } else {
      cur.done = e.detail;
    }
    cur.status = e.status;
    byStep.set(e.step, cur);
  }
  const list = h("ol", { class: "vf-steps" });
  for (const step of STEP_ORDER) {
    const s = byStep.get(step);
    if (!s) continue;
    const ic = s.status === "done" ? "check-circle" : s.status === "error" ? "warning-circle" : STEP_ICON[step];
    list.append(h("li", { dataset: { step, status: s.status }, class: `vf-step vf-${s.status}` },
      h("span", { class: "vf-step-icon" }, icon(ic, 16)),
      h("div", { class: "vf-step-body" },
        h("div", { class: "vf-step-title" }, t(`step_${step}`, lang)),
        h("div", { class: "vf-step-detail" }, s.done || s.head),
        s.log.length ? h("ul", { class: "vf-step-log" }, s.log.slice(-8).map((l) => h("li", {}, l))) : null)));
  }
  container.replaceChildren(list);
}

export function renderReport(container, r, lang = r.lang || "zh") {
  const evById = new Map(r.evidence.map((e) => [e.id, e]));
  const verdictOf = new Map(r.verdicts.map((v) => [v.claim_id, v]));

  const card = h("section", { class: `vf-verdict vf-risk-${r.risk}` },
    h("div", { class: "vf-risk" }, icon(RISK_ICON[r.risk] || "flag", 24), t(`risk_${r.risk}`, lang)),
    h("p", { class: "vf-summary" }, r.summary),
    r.pressure != null ? h("div", { class: "vf-meta" }, `${t("pressure", lang)}: ${r.pressure}/3`) : null);

  const claims = h("section", { class: "vf-section" }, h("h3", {}, t("claims", lang)),
    r.claims.map((c) => {
      const v = verdictOf.get(c.id) || { verdict: "insufficient", evidence_ids: [], rationale: "" };
      return h("div", { class: "vf-claim" },
        h("span", { class: `vf-tag vf-v-${v.verdict}` }, t(`verdict_${v.verdict}`, lang)),
        h("span", { class: "vf-claim-text" }, c.text),
        v.rationale ? h("p", { class: "vf-rationale" }, v.rationale) : null,
        v.evidence_ids.length ? h("ul", { class: "vf-cites" }, v.evidence_ids.map((id) => {
          const e = evById.get(id);
          if (!e) return null;
          return h("li", {}, h("span", { class: "vf-src" }, `[${id}] ${t(`src_${e.source_type}`, lang)}`), " ",
            e.url ? link(e.url, e.title) : h("span", {}, e.title),
            e.snippet ? h("blockquote", {}, e.snippet) : null);
        })) : null);
    }));

  const similar = r.similar?.length ? h("section", { class: "vf-section" }, h("h3", {}, t("similar", lang)),
    h("ul", { class: "vf-similar" }, r.similar.map((s) => h("li", {},
      h("span", { class: "vf-sim" }, `${t("similarity", lang)} ${s.similarity.toFixed(2)}`), " ",
      s.url ? link(s.url, s.title) : s.title)))) : null;

  const actions = h("section", { class: "vf-section vf-actions" }, h("h3", {}, t("actions", lang)),
    h("ul", {}, r.actions.map((a) => h("li", {}, a))));

  container.replaceChildren(card, claims, similar || "", actions);
}

// Skeleton shaped like the report, shown while the agent works (no spinners).
export function renderSkeleton(container) {
  container.replaceChildren(h("div", { class: "vf-skel", "aria-hidden": "true" }, h("span"), h("span"), h("span"), h("span")));
}

export function renderError(container, key, lang = "zh") {
  container.replaceChildren(h("p", { class: "vf-error-box", role: "alert" }, icon("warning-circle", 20), t(key, lang)));
}

export function renderStage1(container, s, lang = "zh") {
  container.replaceChildren(h("section", { class: `vf-stage1 vf-label-${s.label}` },
    h("div", { class: "vf-stage1-head" }, h("strong", {}, t("stage1", lang)), " ",
      h("span", { class: `vf-tag vf-l-${s.label}` }, t(`label_${s.label}`, lang))),
    h("div", { class: "vf-meta" }, t("stage1_by", lang, { p: s.answered_by, ms: s.latency_ms }),
      ` · P(scam) ${s.p_scam.toFixed(2)}`)));
}

export function parseSSE() {
  let buf = "";
  return {
    feed(chunk) {
      buf += chunk;
      // a CR at the end may be the first half of a CRLF split across chunks: hold it back
      const hold = buf.endsWith("\r") ? "\r" : "";
      if (hold) buf = buf.slice(0, -1);
      buf = buf.replace(/\r\n?/g, "\n");
      const out = [];
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const block = buf.slice(0, i);
        buf = buf.slice(i + 2);
        let event = "message";
        const data = [];
        for (const line of block.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
        }
        if (!data.length) continue;
        try {
          out.push({ event, data: JSON.parse(data.join("\n")) });
        } catch { /* ignore keep-alive / malformed */ }
      }
      buf += hold;
      return out;
    },
  };
}

export async function streamVerify(baseUrl, body, { onStep, onReport, onError, onDone } = {}) {
  let res;
  try {
    res = await fetch(`${baseUrl}/verify`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
    });
  } catch (e) {
    onError?.("err_generic");
    return;
  }
  if (res.status === 429) return onError?.("err_rate");
  if (res.status === 503) return onError?.("err_budget");
  if (res.status === 413) return onError?.("err_image_big");
  if (!res.ok || !res.body) return onError?.("err_generic");
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  const p = parseSSE();
  let gotReport = false;
  let failed = false;
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const { event, data } of p.feed(value)) {
        if (event === "step") onStep?.(data);
        else if (event === "report") { gotReport = true; onReport?.(data); }
        else if (event === "done") onDone?.();
        else if (event === "error" && data?.error === "image_unreadable" && !failed) { failed = true; onError?.("err_image"); }
      }
    }
  } catch { /* connection reset mid-stream: reported below */ }
  if (!gotReport && !failed) onError?.("err_generic");
}

export async function screen(baseUrl, post, provider) {
  const res = await fetch(`${baseUrl}/screen`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ posts: [post], provider }),
  });
  if (!res.ok) throw new Error(`screen ${res.status}`);
  return (await res.json()).results[0];
}
