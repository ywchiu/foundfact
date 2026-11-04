import { describe, expect, it, vi } from "vitest";
import { verifyDirect, enforceEvidence, searchEvidence, consumeSSE } from "../direct-verify.js";
const json = value => new Response(JSON.stringify(value));
const chat = value => json({ choices: [{ message: { content: JSON.stringify(value) } }] });
const claims = [{ id: "c1", text: "Example pays £2000" }];
const input = { post: { id: "test", platform: "threads", text: "Retyping role £2000 no experience DM", image_urls: [] }, lang: "en" };
const cfg = { museKey: "muse-test-secret" };
const output = [{ type: "message", content: [{ text: "Authorities warn of fake job fees.", annotations: [{ type: "url_citation", url: "https://agency.example/advice", title: "Advice", start_index: 0, end_index: 33 }] }] }];
const stream = events => new Response(events.map(e => `data: ${JSON.stringify(e)}\r\n\r\n`).join(""), { headers: { "content-type": "text/event-stream" } });
describe("browser-only Muse verification", () => {
  it("runs a real pipeline against only the Meta API and enforces insufficient for unknown evidence", async () => {
    const fetchFn = vi.fn(async (url, opts) => {
      const body = JSON.parse(opts.body);
      if (url.endsWith("/responses")) return stream([{ type: "response.completed", response: { output } }]);
      const name = body.response_format.json_schema.name;
      if (name === "claims") return chat({ claims: claims.map(c => c.text) });
      if (name === "verdicts") return chat({ verdicts: [{ claim_id: "c1", verdict: "supported", evidence_ids: ["invented"], rationale: "No evidence about this offer" }] });
      if (name === "conclusion") return chat({ risk: "high", summary: "Suspicious offer; its pay cannot be verified.", actions: ["Do not send money"] });
      throw new Error("Unexpected request");
    });
    const onStep = vi.fn(), onReport = vi.fn();
    const { report, cacheable } = await verifyDirect(cfg, input, { fetchFn, loadData: async () => ({ cases: [], blocklist: new Map() }), onStep, onReport });
    expect(fetchFn).toHaveBeenCalledTimes(4);
    expect(fetchFn.mock.calls.every(([url]) => url.startsWith("https://api.meta.ai/v1/"))).toBe(true);
    expect(report.verdicts[0].verdict).toBe("insufficient"); expect(report.verdicts[0].evidence_ids).toEqual([]);
    expect(report.evidence[0].url).toBe("https://agency.example/advice");
    expect(report.actions.some(a => a.includes("165"))).toBe(true);
    expect(cacheable).toBe(true); expect(onReport).toHaveBeenCalledTimes(1);
    expect(onStep.mock.calls.map(([s]) => s.step)).toContain("search");
  });
  it("requires a user key before any fetch", async () => {
    const fetchFn = vi.fn(); await expect(verifyDirect({}, input, { fetchFn })).rejects.toThrow("API key"); expect(fetchFn).not.toHaveBeenCalled();
  });
  it("aborts without starting the next paid operation", async () => {
    const controller = new AbortController(); controller.abort(); const fetchFn = vi.fn();
    await expect(verifyDirect(cfg, input, { fetchFn, signal: controller.signal })).rejects.toThrow(); expect(fetchFn).not.toHaveBeenCalled();
  });
  it("does not use image evidence, empty search hits, or invented source IDs as proof", () => {
    const ev = [{ id: "i1", source_type: "image", snippet: "post says so" }, { id: "w1", source_type: "web", snippet: "" }];
    expect(enforceEvidence(claims, [{ claim_id: "c1", verdict: "refuted", evidence_ids: ["i1", "w1", "fake"] }], ev)[0]).toMatchObject({ verdict: "insufficient", evidence_ids: [] });
  });
  it("rejects non-HTTP source URLs", () => {
    expect(searchEvidence([{ type: "web_search_call", results: [{ url: "javascript:alert(1)" }] }])).toEqual([]);
  });
  it("does not accept a truncated SSE response as completed", async () => {
    const fetchFn = vi.fn(async (url, opts) => url.endsWith("/responses") ? stream([{ type: "response.output_item.done", item: output[0] }]) : chat(JSON.parse(opts.body).response_format.json_schema.name === "claims" ? { claims: ["claim"] } : JSON.parse(opts.body).response_format.json_schema.name === "verdicts" ? { verdicts: [] } : { risk: "check", summary: "Unclear", actions: [] }));
    const { report, cacheable } = await verifyDirect(cfg, input, { fetchFn, loadData: async () => ({ cases: [], blocklist: new Map() }) });
    expect(cacheable).toBe(false); expect(report.evidence).toEqual([]);
  });
  it("parses split Unicode and final SSE line without newline", async () => {
    const bytes = new TextEncoder().encode('data: {"text":"查證"}');
    const response = { body: new ReadableStream({ start(c) { c.enqueue(bytes.slice(0, 17)); c.enqueue(bytes.slice(17)); c.close(); } }) };
    const found = []; await consumeSSE(response, ev => found.push(ev)); expect(found).toEqual([{ text: "查證" }]);
  });
});
