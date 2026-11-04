// These are bundled release data, read from chrome-extension://, never a FoundFact backend.
let data;
export function loadLocalData(fetchFn = fetch) {
  data ||= Promise.all([fetchFn(chrome.runtime.getURL("data/blocklist.tsv")), fetchFn(chrome.runtime.getURL("data/cases.jsonl"))])
    .then(async ([b, c]) => {
      if (!b.ok || !c.ok) throw new Error("Bundled reference data unavailable");
      const blocklist = new Map((await b.text()).split(/\r?\n/).filter(l => l && !l.startsWith("#")).map(l => l.split("\t")));
      const cases = (await c.text()).split(/\r?\n/).filter(Boolean).map(l => JSON.parse(l));
      return { blocklist, cases };
    }).catch(e => { data = null; throw e; });
  return data;
}
export function domainsOf(post) {
  const out = new Set();
  const add = d => { try { out.add(new URL(d.includes("://") ? d : `https://${d}`).hostname.toLowerCase().replace(/^www\./, "")); } catch {} };
  for (const d of [...(post.link_domains || []), ...(post.links || [])]) add(d);
  for (const m of (post.text || "").matchAll(/(?:https?:\/\/)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d+)?(?:\/[^\s<>]*)?/gi)) add(m[0]);
  return [...out].sort();
}
export function findBlocklistHit(post, blocklist) {
  for (const domain of domainsOf(post)) {
    const parts = domain.split(".");
    while (parts.length >= 2) {
      const d = parts.join(".");
      if (blocklist.has(d)) return { domain, category: blocklist.get(d), url: null };
      parts.shift();
    }
  }
  return null; // Do not resolve short links or visit suspect sites.
}
