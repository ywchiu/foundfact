import { describe, expect, it } from "vitest";
import { renderReport, renderSteps, parseSSE } from "../report.js";
import { t } from "../i18n.js";

const XSS = '<img src=x onerror="window.__pwned=1">';
const report = {
  post_id: "p1", risk: "high", summary: "典型投資詐騙 " + XSS, lang: "zh", pressure: 2,
  claims: [{ id: "c1", text: "魏哲家帶單 " + XSS }, { id: "c2", text: "保證獲利" }],
  verdicts: [
    { claim_id: "c1", verdict: "refuted", evidence_ids: ["w1"], rationale: "官方澄清" },
    { claim_id: "c2", verdict: "insufficient", evidence_ids: [], rationale: "" },
  ],
  evidence: [{ id: "w1", source_type: "web", url: "https://tfc-taiwan.org.tw/x", title: "假帳號 " + XSS, snippet: XSS }],
  similar: [{ case_id: "k1", title: "飆股群組詐騙", scam_type: "investment", similarity: 0.91, url: "https://a/1" }],
  actions: ["撥打 165"],
};

describe("renderReport", () => {
  it("shows insufficient label in both languages", () => {
    const el = document.createElement("div");
    renderReport(el, report, "zh");
    expect(el.textContent).toContain("證據不足");
    renderReport(el, { ...report, lang: "en" }, "en");
    expect(el.textContent).toContain("Insufficient evidence");
    expect(el.textContent).not.toContain("證據不足");
  });

  it("links evidence safely in a new tab", () => {
    const el = document.createElement("div");
    renderReport(el, report, "zh");
    const a = el.querySelector('a[href="https://tfc-taiwan.org.tw/x"]');
    expect(a).not.toBeNull();
    expect(a.target).toBe("_blank");
    expect(a.rel).toContain("noopener");
  });

  it("never injects HTML from report content", () => {
    const el = document.createElement("div");
    renderReport(el, report, "zh");
    expect(el.querySelector("img")).toBeNull();
    expect(el.textContent).toContain("<img");
  });

  it("drops non-http evidence urls", () => {
    const el = document.createElement("div");
    const bad = { ...report, evidence: [{ ...report.evidence[0], url: "javascript:alert(1)" }] };
    renderReport(el, bad, "zh");
    expect(el.querySelector('a[href^="javascript"]')).toBeNull();
  });
});

describe("renderSteps", () => {
  it("shows each step once with its latest status and keeps search sub-log", () => {
    const el = document.createElement("div");
    renderSteps(el, [
      { step: "extract", status: "running", detail: "抽出" },
      { step: "extract", status: "done", detail: "抽出 2 項" },
      { step: "search", status: "running", detail: "Muse 上網搜尋證據" },
      { step: "search", status: "running", detail: "🔎 魏哲家 詐騙" },
    ], "zh");
    const items = el.querySelectorAll("[data-step]");
    expect([...items].map((i) => i.dataset.step)).toEqual(["extract", "search"]);
    expect(items[0].dataset.status).toBe("done");
    expect(items[1].dataset.status).toBe("running");
    expect(items[1].textContent).toContain("魏哲家 詐騙");
  });
});

describe("parseSSE", () => {
  it("parses event/data blocks across chunk boundaries", () => {
    const p = parseSSE();
    const a = p.feed('event: step\ndata: {"step":"extract"');
    const b = p.feed(',"status":"done","detail":""}\n\nevent: done\ndata: {}\n\n');
    expect(a).toEqual([]);
    expect(b).toEqual([
      { event: "step", data: { step: "extract", status: "done", detail: "" } },
      { event: "done", data: {} },
    ]);
  });
});

describe("i18n", () => {
  it("falls back to zh for missing en keys and returns key when unknown", () => {
    expect(t("verdict_refuted", "en")).toBe("Refuted by evidence");
    expect(t("nope_key", "en")).toBe("nope_key");
  });
});

describe("renderSkeleton / renderError / icons", () => {
  it("skeleton is hidden from screen readers and has no spinner", async () => {
    const { renderSkeleton } = await import("../report.js");
    const el = document.createElement("div");
    renderSkeleton(el);
    const sk = el.querySelector(".vf-skel");
    expect(sk.getAttribute("aria-hidden")).toBe("true");
    expect(sk.children.length).toBe(4);
  });

  it("error box is an alert with an icon and localized text", async () => {
    const { renderError } = await import("../report.js");
    const el = document.createElement("div");
    renderError(el, "err_rate", "en");
    const box = el.querySelector(".vf-error-box");
    expect(box.getAttribute("role")).toBe("alert");
    expect(box.querySelector("svg")).not.toBeNull();
    expect(box.textContent).toContain("Too many checks");
  });

  it("steps render SVG icons, not glyphs", () => {
    const el = document.createElement("div");
    renderSteps(el, [{ step: "search", status: "running", detail: "q" }], "en");
    expect(el.querySelector(".vf-step-icon svg")).not.toBeNull();
  });

  it("icon() builds an svg with the requested size and throws nothing for known names", async () => {
    const { icon } = await import("../icons.js");
    const s = icon("arrow-right", 24);
    expect(s.tagName.toLowerCase()).toBe("svg");
    expect(s.getAttribute("width")).toBe("24");
    expect(s.getAttribute("aria-hidden")).toBe("true");
  });
});

describe("SSE robustness", () => {
  it("keeps events when a CRLF pair is split across chunks", () => {
    const p = parseSSE();
    const wire = 'event: step\r\ndata: {"a":1}\r\n\r\nevent: report\r\ndata: {"b":2}\r\n\r\n';
    for (let cut = 1; cut < wire.length; cut++) {
      const q = parseSSE();
      const got = [...q.feed(wire.slice(0, cut)), ...q.feed(wire.slice(cut))];
      expect(got.map((e) => e.event), `cut at ${cut}`).toEqual(["step", "report"]);
    }
    expect(p).toBeTruthy();
  });

  it("reports an error when the stream breaks after a 200", async () => {
    const { streamVerify } = await import("../report.js");
    const body = new ReadableStream({
      start(c) { c.enqueue(new TextEncoder().encode('event: step\ndata: {"s":1}\n\n')); c.error(new Error("reset")); },
    });
    const orig = globalThis.fetch;
    globalThis.fetch = async () => new Response(body, { status: 200 });
    const errs = [];
    try {
      await streamVerify("", {}, { onError: (k) => errs.push(k) });
    } finally { globalThis.fetch = orig; }
    expect(errs).toEqual(["err_generic"]);
  });
});

describe("image support", () => {
  async function run(res) {
    const { streamVerify } = await import("../report.js");
    const orig = globalThis.fetch;
    globalThis.fetch = async () => res;
    const errs = [];
    try { await streamVerify("", {}, { onError: (k) => errs.push(k) }); } finally { globalThis.fetch = orig; }
    return errs;
  }
  it("maps an unreadable image to its own message, once", async () => {
    const body = 'event: error\ndata: {"error": "image_unreadable"}\n\n';
    expect(await run(new Response(body, { status: 200 }))).toEqual(["err_image"]);
  });
  it("maps 413 to the image-too-large message", async () => {
    expect(await run(new Response("", { status: 413 }))).toEqual(["err_image_big"]);
  });
  it("shows the image step first", async () => {
    const { renderSteps } = await import("../report.js");
    const el = document.createElement("div");
    renderSteps(el, [{ step: "extract", status: "running", detail: "" }, { step: "image", status: "done", detail: "" }], "en");
    expect([...el.querySelectorAll("[data-step]")].map((n) => n.dataset.step)).toEqual(["image", "extract"]);
  });
  it("has image strings in both languages", async () => {
    const { t } = await import("../i18n.js");
    for (const k of ["err_image", "err_image_big", "add_image", "add_image_hint", "remove_image"]) {
      expect(t(k, "zh")).not.toBe(k);
      expect(t(k, "en")).not.toBe(t(k, "zh"));
    }
  });
});
