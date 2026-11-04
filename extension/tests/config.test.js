import { expect, it, vi, afterEach } from "vitest";
import { getConfig, publicConfig } from "../config.js";
afterEach(() => vi.unstubAllGlobals());
it("restricts local storage before reading secrets and exposes only public settings", async () => {
  const order = [];
  vi.stubGlobal("chrome", { storage: { local: { setAccessLevel: vi.fn(async v => { expect(v.accessLevel).toBe("TRUSTED_CONTEXTS"); order.push("restrict"); }), get: async () => { order.push("read"); return { jevKey: "private", museKey: "private2", lang: "en", enabled: true }; } } } });
  const cfg = await getConfig(); expect(order).toEqual(["restrict", "read"]);
  expect(publicConfig(cfg)).toEqual({ lang: "en", enabled: true, configured: true });
  expect(cfg.screenHourlyLimit).toBe(0); expect(cfg.verifyHourlyLimit).toBe(0);
});
