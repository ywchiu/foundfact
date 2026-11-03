// Threads feed adapter. Each feed item is a [data-pressable-container] holding a /@user/post/CODE link;
// its body is the span[dir=auto] lines minus username, timestamp, counters and the translate button.
export const platform = "threads";
const POST_LINK = 'a[href*="/post/"]';
const COUNT = /^[\d,.]+\s*[萬千KkMm]?$/;
const REPOST = /(已轉發|reposted)$/i;
const TRANSLATE = /\s*\n?\s*(翻譯|Translate|查看翻譯|See translation)\s*$/;

export function findPosts(root = document) {
  return [...root.querySelectorAll('[data-pressable-container="true"]')]
    .filter((el) => el.querySelector(POST_LINK) && !el.parentElement?.closest('[data-pressable-container="true"]'));
}

// External link target (l.threads.com unwrapped), or null for Threads/Instagram's own links.
function urlOf(href) {
  try {
    let u = new URL(href, "https://www.threads.com");
    if (/(^|\.)l\.threads\.(com|net)$/.test(u.hostname) && u.searchParams.get("u")) u = new URL(u.searchParams.get("u"));
    if (/(^|\.)(threads\.(com|net)|instagram\.com|fbcdn\.net|cdninstagram\.com)$/.test(u.hostname)) return null;
    return u;
  } catch {
    return null;
  }
}

export function extractPost(el) {
  const link = el.querySelector(POST_LINK);
  const m = link?.getAttribute("href")?.match(/^\/@([^/]+)\/post\/([^/?#]+)/);
  if (!m) return null;
  const [, author, code] = m;
  const lines = [];
  for (const s of el.querySelectorAll('span[dir="auto"]')) {
    if (s.parentElement?.closest('span[dir="auto"]')) continue; // nested span: parent already counted
    if (s.closest(POST_LINK)) continue; // timestamp
    const txt = (s.innerText ?? s.textContent ?? "").replace(TRANSLATE, "").trim();
    if (!txt || COUNT.test(txt) || txt === author || REPOST.test(txt)) continue;
    const userLink = s.querySelector('a[href^="/@"]');
    if (userLink && (userLink.textContent ?? "").trim() === txt) continue; // username / mention-only line
    lines.push(txt);
  }
  const text = lines.join("\n").trim();
  if (!text) return null;
  const domains = new Set();
  const links = new Set();
  for (const a of el.querySelectorAll("a[href]")) {
    const u = urlOf(a.getAttribute("href"));
    if (!u) continue;
    domains.add(u.hostname.replace(/^www\./, "").toLowerCase());
    if (links.size < 5) links.add(u.href);
  }
  const image_urls = [...el.querySelectorAll("img[src]")]
    .filter((i) => !/大頭貼照|profile picture/i.test(i.getAttribute("alt") || ""))
    .map((i) => i.getAttribute("src")).filter((s) => /fbcdn|cdninstagram/.test(s)).slice(0, 3);
  return { id: `th-${code}`, platform, author, text, link_domains: [...domains], links: [...links], image_urls };
}
