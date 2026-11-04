import { afterEach, expect, it, vi } from "vitest";
const screen = vi.hoisted(() => vi.fn(async () => []));
vi.mock("../screen-client.js", () => ({ createScreenClient: () => screen }));
vi.mock("../config.js", () => ({ getConfig: async () => ({ enabled: true, lang: "en", jevKey: "private-key", museKey: "private-muse" }), secureStorage: async () => {}, publicConfig: c => ({ enabled: c.enabled, lang: c.lang, configured: !!c.jevKey }) }));
afterEach(() => { vi.unstubAllGlobals(); vi.resetModules(); screen.mockClear(); });
async function setup() {
  let handler, connect;
  vi.stubGlobal("chrome", { runtime: { onMessage: { addListener: fn => { handler = fn; } }, onConnect: { addListener: fn => { connect = fn; } }, onInstalled: { addListener() {} }, getURL: p => `chrome-extension://fixture/${p}` }, storage: { session: {}, local: { onChanged: { addListener() {} } } } });
  await import("../background.js"); return { handler, connect };
}
const sender = active => ({ url: "https://www.threads.com/@fixture/post/abc", tab: { id: 1, active } });
const post = { id: "abc", platform: "threads", text: "fixture" };
it("rejects inactive tabs and non-social senders before entering the shared queue", async () => {
  const { handler } = await setup(), reply = vi.fn();
  handler({ type: "screen", posts: [post] }, sender(false), reply);
  await vi.waitFor(() => expect(reply).toHaveBeenCalledWith(expect.objectContaining({ ok: false, retryAfterMs: 60000 })));
  expect(screen).not.toHaveBeenCalled();
  expect(handler({ type: "screen", posts: [post] }, { url: "https://attacker.example" }, reply)).toBe(false);
  handler({ type: "screen", posts: [post] }, sender(true), reply);
  await vi.waitFor(() => expect(screen).toHaveBeenCalledTimes(1));
});
it("sends content scripts only public settings, never keys", async () => {
  const { handler } = await setup(), reply = vi.fn();
  handler({ type: "content_config" }, sender(true), reply);
  await vi.waitFor(() => expect(reply).toHaveBeenCalledWith({ enabled: true, lang: "en", configured: true }));
  expect(JSON.stringify(reply.mock.calls)).not.toContain("private");
});
it("rejects full verification from content script ports", async () => {
  const { connect } = await setup(), disconnect = vi.fn();
  connect({ name: "verify", sender: sender(true), disconnect });
  expect(disconnect).toHaveBeenCalled();
});
