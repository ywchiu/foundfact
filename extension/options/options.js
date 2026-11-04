import { getConfig } from "../config.js";
const $ = s => document.getElementById(s);
const cfg = await getConfig();
$("enabled").checked = cfg.enabled;
for (const name of ["lang", "jevService", "jevKey", "museKey", "screenHourlyLimit", "verifyHourlyLimit"]) $(name).value = cfg[name];
$("save").addEventListener("click", async () => {
  if (!["screenHourlyLimit", "verifyHourlyLimit"].every(k => $(k).reportValidity())) return;
  await chrome.storage.local.set({ enabled: $("enabled").checked, lang: $("lang").value, jevService: $("jevService").value,
    jevKey: $("jevKey").value.trim(), museKey: $("museKey").value.trim(),
    screenHourlyLimit: Number($("screenHourlyLimit").value), verifyHourlyLimit: Number($("verifyHourlyLimit").value) });
  // Remove legacy server configuration; keys never go to the old backend.
  await chrome.storage.local.remove(["backendUrl", "provider"]);
  $("saved").textContent = "✓ Saved";
});
