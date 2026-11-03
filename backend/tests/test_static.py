from fastapi.testclient import TestClient

from app.api import Services, create_app


def test_serves_web_shared_and_privacy(settings, store, fake_muse):
    c = TestClient(create_app(Services.build(settings, store=store, muse=fake_muse)))
    r = c.get("/")
    assert r.status_code == 200 and "FoundFact" in r.text
    assert c.get("/shared/report.js").status_code == 200
    p = c.get("/privacy")
    assert p.status_code == 200 and "Muse" in p.text
    assert c.get("/health").json() == {"ok": True}


def test_unknown_path_serves_custom_404(settings, store, fake_muse):
    c = TestClient(create_app(Services.build(settings, store=store, muse=fake_muse)))
    r = c.get("/no-such-page")
    assert r.status_code == 404 and "FoundFact" in r.text and 'href="/"' in r.text


def test_static_files_revalidate_so_cdn_never_serves_stale_code(settings, store, fake_muse):
    c = TestClient(create_app(Services.build(settings, store=store, muse=fake_muse)))
    for path in ("/", "/app.js", "/shared/report.js", "/shared/report.css"):
        assert c.get(path).headers.get("cache-control") == "no-cache", path
    assert "immutable" in c.get("/shared/fonts/geist-latin.woff2").headers.get("cache-control", "")
