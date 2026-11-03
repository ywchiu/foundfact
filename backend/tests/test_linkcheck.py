import pytest
import httpx
import respx

from app import linkcheck

from app.linkcheck import Blocklist, check_links, normalize_host, urls_of
from app.models import Post


def bl():
    return Blocklist({"evil-invest.com": "investment", "shop.fake.top": "shopping",
                      "play.google.com": "other", "com.tw": "other"})


def test_normalize_host_strips_scheme_path_www_and_dots():
    assert normalize_host(" https://WWW.Evil.com/path?q=1 ") == "evil.com"
    assert normalize_host("sm-shopmsbest.top/www") == "sm-shopmsbest.top"
    assert normalize_host("famistore.famiport.com.tw.") == "famistore.famiport.com.tw"
    assert normalize_host("stepup99") is None and normalize_host("") is None


def test_match_exact_subdomain_but_not_parent():
    b = bl()
    assert b.match("evil-invest.com") == ("evil-invest.com", "investment")
    assert b.match("app.evil-invest.com") == ("evil-invest.com", "investment")
    assert b.match("fake.top") is None  # listing a subdomain does not flag its parent
    assert b.match("good.com") is None


def test_allowlisted_platforms_and_public_suffixes_never_match():
    b = bl()
    assert b.match("play.google.com") is None
    assert b.match("anything.com.tw") is None
    assert len(b) == 2


def test_urls_of_reads_links_and_text():
    p = Post(id="1", platform="facebook", text="快加 https://reurl.cc/AbC 領 bit.ly/x9 好禮",
             links=["https://lin.ee/zz"])
    assert urls_of(p) == ["https://lin.ee/zz", "https://reurl.cc/AbC", "https://bit.ly/x9"]


@respx.mock
async def test_shortener_is_resolved_to_blocklisted_final_host(dns):
    respx.head("https://reurl.cc/AbC").mock(return_value=httpx.Response(
        301, headers={"location": "https://www.evil-invest.com/join"}))
    respx.head("https://www.evil-invest.com/join").mock(return_value=httpx.Response(200))
    p = Post(id="1", platform="facebook", text="快加 https://reurl.cc/AbC")
    hit = await check_links(p, bl())
    assert hit == {"domain": "evil-invest.com", "category": "investment",
                   "url": "https://www.evil-invest.com/join"}


@respx.mock
async def test_listed_domain_hits_without_any_network_call():
    route = respx.route().mock(side_effect=AssertionError("no fetch for non-shorteners"))
    p = Post(id="1", platform="facebook", text="x", link_domains=["shop.fake.top"])
    hit = await check_links(p, bl())
    assert hit["domain"] == "shop.fake.top" and hit["category"] == "shopping" and not route.called


@respx.mock
async def test_unreachable_shortener_is_not_a_hit():
    respx.head("https://bit.ly/x9").mock(side_effect=httpx.ConnectTimeout("t"))
    assert await check_links(Post(id="1", platform="facebook", text="bit.ly/x9 看"), bl()) is None


def test_hosting_platform_tenants_are_listed_but_the_platform_is_not():
    b = Blocklist({"shopeetw88.github.io": "shopping", "github.io": "other", "netlify.app": "other"})
    assert b.match("shopeetw88.github.io") == ("shopeetw88.github.io", "shopping")
    assert b.match("ywchiu.github.io") is None and b.match("github.io") is None
    assert len(b) == 1


@pytest.fixture
def dns(monkeypatch):
    table = {"reurl.cc": ["104.21.1.1"], "www.evil-invest.com": ["93.184.216.34"], "bit.ly": ["67.199.248.10"],
             "internal.example": ["10.0.0.5"], "v6.example": ["::1"]}
    monkeypatch.setattr(linkcheck, "_host_ips", lambda h: table.get(h) or (_ for _ in ()).throw(OSError(h)))
    return table


@pytest.mark.parametrize("url,ok", [
    ("https://reurl.cc/x", True),
    ("http://127.0.0.1:8020/teacher/v1/answer", False),
    ("https://169.254.169.254/latest/meta-data", False),
    ("https://internal.example/", False),
    ("https://v6.example/", False),
    ("ftp://reurl.cc/x", False),
    ("https://no-such-host.invalid/", False),
])
async def test_is_public_url(dns, url, ok):
    assert await linkcheck.is_public_url(url) is ok


@respx.mock
async def test_short_link_redirect_into_private_network_is_never_requested(dns):
    respx.head("https://bit.ly/in").mock(return_value=httpx.Response(302, headers={"location": "http://127.0.0.1:8020/x"}))
    inner = respx.route(host="127.0.0.1").mock(side_effect=AssertionError("SSRF"))
    assert await check_links(Post(id="1", platform="facebook", text="bit.ly/in"), bl()) is None
    assert not inner.called


async def test_userinfo_trick_is_judged_by_the_real_host(dns):
    assert await linkcheck.is_public_url("http://bit.ly:80@127.0.0.1:8020/health") is False
