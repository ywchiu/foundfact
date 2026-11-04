import json
from datetime import date

from fastapi.testclient import TestClient

from app.api import Services, create_app
from app.guard import BudgetGuard, RateLimiter, ResultCache, clip_text
from tests.test_agent import SCAM, AgentMuse

BODY = {"post": json.loads(SCAM.model_dump_json()), "lang": "zh"}


def client(settings, store, muse):
    return TestClient(create_app(Services.build(settings, store=store, muse=muse)))


def sse(c, body=BODY, headers=None):
    with c.stream("POST", "/verify", json=body, headers=headers or {}) as r:
        return r.status_code, "".join(r.iter_text())


def test_clip_text():
    assert len(clip_text("a" * 5000, 4000)) == 4000
    assert clip_text("abc", 4000) == "abc"


def test_rate_limit_eleventh_is_429(settings, store):
    settings.verify_per_ip_hour = 10
    c = client(settings, store, AgentMuse())
    codes = [sse(c, {**BODY, "post": {**BODY["post"], "text": f"{BODY['post']['text']} {i}"}})[0]
             for i in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429


def test_rate_limit_ignores_client_supplied_forwarded_for(settings, store):
    # uvicorn --proxy-headers already resolves the trusted proxy chain into request.client;
    # a raw X-Forwarded-For from the client must not mint a fresh rate-limit bucket.
    settings.verify_per_ip_hour = 1
    c = client(settings, store, AgentMuse())
    assert sse(c, headers={"x-forwarded-for": "1.1.1.1"})[0] == 200
    assert sse(c, {**BODY, "lang": "en"}, headers={"x-forwarded-for": "2.2.2.2"})[0] == 429


def test_screen_is_rate_limited_per_post(settings, store):
    settings.screen_per_ip_hour = 3
    c = client(settings, store, AgentMuse())
    posts = lambda n, o: [{"id": f"p{o + i}", "platform": "web", "text": f"hello {o + i}"} for i in range(n)]
    assert c.post("/screen", json={"posts": posts(2, 0), "provider": "local"}).status_code == 200
    r = c.post("/screen", json={"posts": posts(2, 2), "provider": "local"})
    assert r.status_code == 429
    assert 1 <= int(r.headers["Retry-After"]) <= 3600
    assert r.json()["error"] == "rate_limited"
    assert c.post("/screen", json={"posts": posts(1, 4), "provider": "local"}).status_code == 200


def test_screen_over_budget_answers_without_paid_models(settings, store, fake_muse):
    svc = Services.build(settings, store=store, muse=fake_muse)
    svc.screener.jev_spent_usd = settings.daily_budget_usd + 1  # Jev spend counts toward the budget
    c = TestClient(create_app(svc))
    r = c.post("/screen", json={"posts": [{"id": "a", "platform": "web", "text": "保證獲利 加LINE"}], "provider": "muse"})
    assert r.status_code == 200 and r.json()["results"][0]["answered_by"] == "fallback"
    assert fake_muse.calls == 0


def test_jev_spend_also_exhausts_verify_budget(settings, store):
    svc = Services.build(settings, store=store, muse=AgentMuse())
    svc.screener.jev_spent_usd = settings.daily_budget_usd + 1
    code, body = sse(TestClient(create_app(svc)))
    assert code == 503 and "budget_exhausted" in body


def test_verify_cache_key_includes_links(settings, store):
    muse = AgentMuse()
    c = client(settings, store, muse)
    sse(c)
    n = len(muse.names)
    sse(c, {**BODY, "post": {**BODY["post"], "links": ["https://evil.example/x"]}})
    assert len(muse.names) > n  # different links → not served from the first report's cache


def test_teacher_endpoint_is_off_unless_enabled(settings, store, fake_muse):
    c = TestClient(create_app(Services.build(settings, store=store, muse=fake_muse)))
    assert c.post("/teacher/v1/answer", json={}).status_code == 404
    settings.teacher_enabled = True
    c = TestClient(create_app(Services.build(settings, store=store, muse=fake_muse)))
    assert c.post("/teacher/v1/answer", json={}).status_code == 400  # reachable; bad body


def test_budget_exhausted_blocks_verify_not_screen(settings, store):
    muse = AgentMuse()
    c = client(settings, store, muse)
    muse.spent_usd = settings.daily_budget_usd + 1
    code, body = sse(c)
    assert code == 503 and "budget_exhausted" in body
    r = c.post("/screen", json={"posts": [{"id": "a", "platform": "web", "text": "hi"}]})
    assert r.status_code == 200


def test_identical_input_served_from_cache(settings, store):
    muse = AgentMuse()
    c = client(settings, store, muse)
    _, first = sse(c)
    n = len(muse.names)
    _, second = sse(c)
    assert len(muse.names) == n  # no new Muse calls
    assert "event: report" in second and "event: step" in second


def test_budget_resets_next_taipei_day():
    days = iter([date(2026, 11, 2), date(2026, 11, 2), date(2026, 11, 3)])
    g = BudgetGuard(1.0, today=lambda: next(days))
    assert g.allow(0.0)
    assert not g.allow(1.5)
    assert g.allow(1.5)  # new day, base resets


def test_cache_expires():
    t = [0.0]
    cache = ResultCache(ttl_s=10, clock=lambda: t[0])
    cache.put("k", 1)
    t[0] = 11
    assert cache.get("k") is None


def test_rate_limiter_window_slides():
    t = [0.0]
    rl = RateLimiter(1, window_s=100, clock=lambda: t[0])
    assert rl.check("a") and not rl.check("a")
    t[0] = 101
    assert rl.check("a")


def test_report_with_a_failed_step_is_not_cached(settings, store):
    muse = AgentMuse(search_fail=True)
    c = client(settings, store, muse)
    sse(c)
    n = len(muse.names)
    sse(c)
    assert len(muse.names) > n  # a transient failure must not be replayed for 24 h


def test_expired_cache_entries_and_idle_rate_buckets_are_dropped():
    now = [0.0]
    cache = ResultCache(ttl_s=10, clock=lambda: now[0])
    cache.put("a", 1)
    now[0] = 11
    cache.put("b", 2)
    assert "a" not in cache.data and "b" in cache.data
    rl = RateLimiter(1, window_s=10, clock=lambda: now[0])
    rl.check("1.1.1.1")
    now[0] = 30
    rl.check("2.2.2.2")
    assert "1.1.1.1" not in rl.hits


def test_whole_verification_has_a_deadline(settings, store):
    import asyncio as aio

    class SlowMuse(AgentMuse):
        async def chat_json(self, *a, **k):
            await aio.sleep(5)
            return await super().chat_json(*a, **k)

    settings.verify_timeout_s = 0.2
    code, body = sse(client(settings, store, SlowMuse()))
    assert code == 200 and "event: report" not in body and "event: error" in body


def test_batch_rate_limit_is_atomic_and_retry_after_is_precise():
    now = [0.0]
    limiter = RateLimiter(3, window_s=60, clock=lambda: now[0])
    assert limiter.check("ip", cost=2)
    now[0] = 10
    assert not limiter.check("ip", cost=2)
    assert len(limiter.hits["ip"]) == 2
    assert limiter.retry_after("ip", cost=2) == 50
    assert limiter.check("ip")  # rejected batch did not consume the remaining slot
    now[0] = 60
    assert limiter.check("ip", cost=2)
