import { getConfig } from "../config.js";

const $ = (s) => document.getElementById(s);

async function refreshProviders(url) {
  try {
    const avail = await (await fetch(`${url}/providers`)).json();
    for (const o of $("provider").options) o.disabled = !avail[o.value];
    $("provHint").textContent = "";
  } catch {
    $("provHint").textContent = "無法連到後端 · Backend unreachable";
  }
}

const cfg = await getConfig();
$("enabled").checked = cfg.enabled;
$("lang").value = cfg.lang;
$("provider").value = cfg.provider;
$("backendUrl").value = cfg.backendUrl;
refreshProviders(cfg.backendUrl);
$("save").addEventListener("click", async () => {
  const backendUrl = $("backendUrl").value.replace(/\/+$/, "");
  await chrome.storage.local.set({ enabled: $("enabled").checked, lang: $("lang").value,
                                   provider: $("provider").value, backendUrl });
  $("saved").textContent = "✓";
  refreshProviders(backendUrl);
});
