// Facebook feed adapter. FB obfuscates classes and only marks comments as role=article, so posts are
// found via the ad-rendering roles FB uses for every feed story: the smallest ancestor of a
// profile_name that also contains a like_button is one post.
const R = (role) => `[data-ad-rendering-role="${role}"]`;
const SEE_MORE = /(…|\.\.\.)?\s*(查看更多|顯示更多|See more)\s*$/;
const DOMAIN = /^(?:[a-z0-9-]+\.)+[a-z]{2,}$/i;

export const platform = "facebook";

export function findPosts(root = document) {
  const out = new Set();
  for (const pn of root.querySelectorAll(R("profile_name"))) {
    let el = pn.parentElement;
    while (el && el !== root && !el.querySelector(R("like_button"))) el = el.parentElement;
    if (el && el !== root && el.querySelectorAll(R("profile_name")).length === 1) out.add(el);
  }
  return [...out];
}

export function hash(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0).toString(36);
}

// External link target (l.facebook.com unwrapped), or null for Facebook's own links.
function urlOf(href) {
  try {
    let u = new URL(href, "https://www.facebook.com");
    if (/(^|\.)l\.facebook\.com$/.test(u.hostname) && u.searchParams.get("u")) u = new URL(u.searchParams.get("u"));
    if (/facebook\.com$|fbcdn\.net$/.test(u.hostname)) return null;
    return u;
  } catch {
    return null;
  }
}

export function extractPost(el) {
  const msg = el.querySelector(R("story_message"));
  const text = (msg?.innerText ?? msg?.textContent ?? "").replace(SEE_MORE, "").trim();
  const pn = el.querySelector(R("profile_name"));
  const author = (pn?.innerText ?? pn?.textContent ?? "").split("\n")[0].trim();
  const domains = new Set();
  const links = new Set();
  for (const a of (msg ?? el).querySelectorAll("a[href]")) {
    const u = urlOf(a.getAttribute("href"));
    if (!u) continue;
    domains.add(u.hostname.replace(/^www\./, "").toLowerCase());
    if (links.size < 5) links.add(u.href);
  }
  const meta = (el.querySelector(R("meta"))?.textContent ?? "").trim().toLowerCase();
  if (DOMAIN.test(meta)) domains.add(meta.replace(/^www\./, ""));
  const title = (el.querySelector(R("title"))?.textContent ?? "").trim();
  const full = [text, title].filter(Boolean).join("\n");
  const image_urls = [...el.querySelectorAll("img[src]")].map((i) => i.getAttribute("src"))
    .filter((s) => /scontent|fbcdn/.test(s)).slice(0, 3);
  if (!full) return null;
  return { id: `fb-${hash(author + "\u0000" + full.slice(0, 300))}`, platform, author, text: full,
           link_domains: [...domains], links: [...links], image_urls };
}
