// Secrets are available only to extension pages and the service worker, never content scripts.
export const DEFAULTS = { lang: "en", enabled: true, jevService: "openrouter", jevKey: "", museKey: "", screenHourlyLimit: 0, verifyHourlyLimit: 0 };
export async function secureStorage() {
  await chrome.storage.local.setAccessLevel({ accessLevel: "TRUSTED_CONTEXTS" });
}
export async function getConfig() {
  await secureStorage();
  return { ...DEFAULTS, ...await chrome.storage.local.get(Object.keys(DEFAULTS)) };
}
export function publicConfig(cfg) { return { lang: cfg.lang, enabled: cfg.enabled, configured: !!cfg.jevKey }; }
