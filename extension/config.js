// Defaults; build.sh --release rewrites the backend URL.
export const DEFAULTS = { backendUrl: "http://127.0.0.1:8000", provider: "muse", lang: "zh", enabled: true };
export async function getConfig() {
  const got = await chrome.storage.local.get(Object.keys(DEFAULTS));
  return { ...DEFAULTS, ...got };
}
