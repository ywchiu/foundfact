"""Known-scam link check: resolve short links to their final host, then look the host up in the National Police
Agency's list of domains suspended for fraud (data.gov.tw 176455 + 160055, built by data/scripts/build_blocklist.py).
A hit is answered in microseconds with no model call."""
import asyncio
import ipaddress
import re
import socket
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from .models import Post

SHORTENERS = {"bit.ly", "reurl.cc", "tinyurl.com", "t.ly", "pse.is", "is.gd", "ppt.cc", "shorturl.at", "lihi.cc",
              "lihi1.com", "lihi2.com", "lihi3.cc", "s.yam.com", "goo.gl", "t.co", "cutt.ly", "rb.gy", "tiny.cc",
              "ow.ly", "buff.ly", "rebrand.ly", "x.gd", "u.nu", "l.facebook.com", "lm.facebook.com", "l.threads.com"}
# Never flag these hosts or anything under them, whatever the list says: one company's namespace, where one bad
# entry (e.g. play.google.com) would flag millions of legitimate links.
ALLOW = {"google.com", "youtube.com", "facebook.com", "fb.com", "instagram.com", "threads.com", "threads.net",
         "line.me", "lin.ee", "apple.com", "microsoft.com", "gov.tw", "edu.tw", "shopee.tw", "momoshop.com.tw",
         "pchome.com.tw", "yahoo.com", "github.com", "t.me"}
# Suffixes under which each name is a different owner: country 2LDs and free hosting platforms. A listed tenant
# (shopeetw88.github.io) matches; the suffix itself is never listed or matched.
PUBLIC_2LD = {"com.tw", "net.tw", "org.tw", "idv.tw", "co.uk", "com.hk", "com.cn", "co.jp", "com.sg", "com.my",
              "github.io", "vercel.app", "netlify.app", "pages.dev", "web.app", "firebaseapp.com", "blogspot.com",
              "wixsite.com", "canva.site", "gamma.app", "herokuapp.com", "glitch.me", "weebly.com", "webflow.io"}
HOST_RE = re.compile(r"(?:[a-z0-9-]+\.)+[a-z0-9-]{2,}")
URL_IN_TEXT = re.compile(r"(https?://[^\s<>\"'）)]+)|\b((?:[a-z0-9-]+\.)+[a-z]{2,}/[^\s<>\"'）)]*)", re.I)
MAX_HOPS, TIMEOUT_S = 5, 3.0


def normalize_host(s: str) -> str | None:
    s = re.sub(r"^[a-z]+://", "", (s or "").strip().lower())
    s = s.split("/")[0].split("?")[0].split("#")[0].split(":")[0].strip(".").removeprefix("www.")
    return s if HOST_RE.fullmatch(s) else None


def _allowed(host: str) -> bool:
    parts = host.split(".")
    return any(".".join(parts[i:]) in ALLOW for i in range(len(parts)))


class Blocklist:
    def __init__(self, entries: dict[str, str] | None = None):
        self.d = {h: c for h, c in (entries or {}).items() if h not in PUBLIC_2LD and "." in h and not _allowed(h)}

    def __len__(self):
        return len(self.d)

    @classmethod
    def load(cls, path: Path) -> "Blocklist":
        """`host<TAB>category` per line; '#' comments. A missing file is an empty list."""
        entries = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith("#"):
                    host, _, cat = line.partition("\t")
                    if (h := normalize_host(host)):
                        entries[h] = cat.strip() or "other"
        return cls(entries)

    def match(self, host: str | None) -> tuple[str, str] | None:
        host = normalize_host(host or "")
        if not host or _allowed(host):
            return None
        parts = host.split(".")
        for i in range(len(parts) - 1):  # host itself, then parents down to two labels
            cand = ".".join(parts[i:])
            if cand in self.d:
                return cand, self.d[cand]
        return None


def urls_of(post: Post) -> list[str]:
    out = list(post.links)
    for m in URL_IN_TEXT.finditer(post.text):
        u = m.group(1) or "https://" + m.group(2)
        if u not in out:
            out.append(u)
    return out


def _host_ips(host: str) -> list[str]:
    return [ai[4][0] for ai in socket.getaddrinfo(host, None)]


async def is_public_url(url: str) -> bool:
    """http(s) URL whose host resolves only to globally routable addresses (no loopback, private,
    link-local or metadata ranges), so server-side fetches cannot be steered into the local network."""
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        ips = await asyncio.to_thread(_host_ips, p.hostname)
        return bool(ips) and all(ipaddress.ip_address(ip.split("%")[0]).is_global for ip in ips)
    except (OSError, ValueError, UnicodeError):
        return False


async def resolve(url: str, client: httpx.AsyncClient) -> str | None:
    """Follow redirects by hand (HEAD, then GET if HEAD is refused) without rendering anything.
    Every hop must be a public http(s) address."""
    for _ in range(MAX_HOPS):
        if not await is_public_url(url):
            return None
        try:
            r = await client.head(url)
            if r.status_code in (403, 405, 501):
                r = await client.get(url)
        except (httpx.HTTPError, ValueError):
            return None
        loc = r.headers.get("location")
        if r.is_redirect and loc:
            url = urljoin(url, loc)
            continue
        return url
    return url


async def check_links(post: Post, blocklist: Blocklist) -> dict | None:
    """First blocklist hit among the post's link hosts and its resolved short links, else None."""
    if not len(blocklist):
        return None
    urls = urls_of(post)
    hosts = [normalize_host(u) for u in urls] + [normalize_host(d) for d in post.link_domains]
    for u, h in zip(urls + [None] * len(post.link_domains), hosts):
        if (m := blocklist.match(h)):
            return {"domain": m[0], "category": m[1], "url": u}
    short = [u for u in urls if normalize_host(u) in SHORTENERS][:3]
    if not short:
        return None
    async with httpx.AsyncClient(timeout=TIMEOUT_S, follow_redirects=False,
                                 headers={"User-Agent": "Mozilla/5.0 FoundFact link check"}) as c:
        finals = await asyncio.gather(*(resolve(u, c) for u in short))
    for f in finals:
        if f and (m := blocklist.match(urlsplit(f).hostname)):
            return {"domain": m[0], "category": m[1], "url": f}
    return None
