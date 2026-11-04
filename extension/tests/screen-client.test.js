import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createScreenClient } from "../screen-client.js";
const cfg = { jevService: "openrouter", jevKey: "test-secret-jev", museKey: "never-used", screenHourlyLimit: 0 };
const post = (id, text = "same actual post") => ({ id, text, platform: "facebook", author: "fixture", links: [] });
const loadData = async () => ({ blocklist: new Map([["evil.example", "investment"]]), cases: [] });
const ok = async () => new Response(JSON.stringify({ answers: { is_scam_like: { noul: .96 }, has_checkable_claim: { noul: .63 } } }));
function session() { let data = {}; return { get: async () => structuredClone(data), set: async v => { data = structuredClone(v); } }; }
beforeEach(() => vi.stubGlobal("crypto", webcrypto));
afterEach(() => vi.unstubAllGlobals());
describe("standalone Jev screening", () => {
  it("deduplicates cross-tab content, calls only Jev directly, and stores no plaintext keys", async () => {
    const storage = session(), fetchFn = vi.fn(ok), screen = createScreenClient({ fetchFn, storage, loadData });
    const [a, b] = await Promise.all([screen([post("a")], cfg), screen([post("b")], cfg)]);
    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(fetchFn.mock.calls[0][0]).toBe("https://openrouter.ai/api/alpha/decisions");
    expect(JSON.parse(fetchFn.mock.calls[0][1].body).model).toBe("typesafe/jev-1.14");
    expect(a[0].answered_by).toBe("jev"); expect(b[0].post_id).toBe("b");
    expect(JSON.stringify(await storage.get())).not.toContain(cfg.jevKey);
    expect(JSON.stringify(fetchFn.mock.calls)).not.toContain(cfg.museKey);
  });
  it("never falls back to Muse or the backend with a missing key or provider failure", async () => {
    const fetchFn = vi.fn().mockRejectedValue(new Error("offline"));
    const screen = createScreenClient({ fetchFn, loadData });
    await expect(screen([post("a")], { ...cfg, jevKey: "" })).rejects.toThrow("API key");
    expect(fetchFn).not.toHaveBeenCalled();
    await expect(screen([post("a")], cfg)).rejects.toThrow("offline");
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });
  it("shares provider cooldown across worker restarts and honors the exact Retry-After", async () => {
    let time = 1000; const storage = session();
    const fetchFn = vi.fn().mockResolvedValueOnce(new Response("", { status: 429, headers: { "Retry-After": "2" } })).mockImplementation(ok);
    let screen = createScreenClient({ fetchFn, storage, loadData, now: () => time });
    await expect(screen([post("a")], cfg)).rejects.toMatchObject({ retryAfterMs: 2000 });
    screen = createScreenClient({ fetchFn, storage, loadData, now: () => time });
    await expect(screen([post("b")], cfg)).rejects.toThrow("paused");
    time += 2000; await screen([post("c")], cfg); expect(fetchFn).toHaveBeenCalledTimes(2);
  });
  it("uses separate credentials and keeps TypeSafe requests on TypeSafe", async () => {
    const fetchFn = vi.fn(ok), screen = createScreenClient({ fetchFn, loadData });
    await screen([post("a")], cfg);
    await screen([post("b")], { ...cfg, jevService: "typesafe", jevKey: "another-key" });
    expect(fetchFn.mock.calls[1][0]).toBe("https://api.typesafe.ai/v1/systemone");
    expect(JSON.parse(fetchFn.mock.calls[1][1].body).model).toBe("jev-latest");
  });
  it("blocks a known fraud domain locally without a key or network call", async () => {
    const fetchFn = vi.fn(), screen = createScreenClient({ fetchFn, loadData });
    const [r] = await screen([post("a", "https://sub.evil.example/free")], { ...cfg, jevKey: "" });
    expect(r.answered_by).toBe("blocklist"); expect(fetchFn).not.toHaveBeenCalled();
  });
  it("enforces only the optional local cap, with cached content free", async () => {
    const fetchFn = vi.fn(ok), screen = createScreenClient({ fetchFn, loadData });
    const cap = { ...cfg, screenHourlyLimit: 1 };
    await screen([post("a")], cap); await screen([post("b")], cap);
    await expect(screen([post("c", "different")], cap)).rejects.toThrow("local hourly limit");
    await screen([post("c", "different")], cfg); expect(fetchFn).toHaveBeenCalledTimes(2);
  });
  it("expires the cache after 24 hours", async () => {
    let time = 0; const fetchFn = vi.fn(ok), screen = createScreenClient({ fetchFn, loadData, now: () => time });
    await screen([post("a")], cfg); time += 86400000; await screen([post("b")], cfg);
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });
});
