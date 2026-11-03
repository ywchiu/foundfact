import json

import httpx
import respx
from fastapi.testclient import TestClient

from app.api import Services, create_app
from app.models import Post
from app.screen import FallbackStage1, Screener, decide

SCAM = "保證月報酬30% 加LINE領飆股 👉 lin.ee/abc"


def post(text, pid="p1"):
    return Post(id=pid, platform="facebook", text=text)


def test_decide_thresholds():
    assert decide(0.9, 0) == "high"
    assert decide(0.5, 0) == "check"
    assert decide(0.1, 0.95) == "none"  # tuned (eval/results/tune.md): a checkable claim alone never flags
    assert decide(0.45, 0) == "none"
    assert decide(0.1, 0.1) == "none"


async def test_fallback_rules(store):
    fb = FallbackStage1(store)
    hi = await fb.screen(post(SCAM), "muse")
    lo = await fb.screen(post("今天去爬山好累，風景很美"), "muse")
    assert hi.p_scam >= 0.8 and hi.answered_by == "fallback"
    assert lo.p_scam < 0.4


async def test_muse_provider_uses_teacher(settings, store, fake_muse):
    s = Screener(settings, store, fake_muse)
    r = await s.screen_post(post(SCAM), "muse")
    assert r.provider == "muse" and r.answered_by == "muse"
    assert r.label == "high" and r.pressure == 2
    assert r.similar and r.similar[0].case_id == "k1"
    assert r.scam_type == "investment"


async def test_default_provider_is_muse(settings, store, fake_muse):
    r = await Screener(settings, store, fake_muse).screen_post(post(SCAM))
    assert r.provider == "muse"


@respx.mock
async def test_screen_falls_back_when_hunch_down(settings, store, fake_muse):
    respx.post(f"{settings.hunch_url}/v1/answer").mock(side_effect=httpx.ConnectError("down"))
    r = await Screener(settings, store, fake_muse).screen_post(post(SCAM), "local")
    assert r.answered_by == "fallback" and r.provider == "local"


@respx.mock
async def test_local_student_confident_no_skips_muse(settings, store, fake_muse):
    route = respx.post(f"{settings.hunch_url}/v1/answer").mock(return_value=httpx.Response(200, json={
        "answers": {"is_scam_like": {"type": "noul", "noul": 0.03, "answered_by": "proxy"}}, "answered_by": "proxy"}))
    r = await Screener(settings, store, fake_muse).screen_post(post("今天去爬山好累，風景很美"), "local")
    assert r.provider == "local" and r.answered_by == "proxy" and r.label == "none"
    assert list(json.loads(route.calls[0].request.content)["questions"]) == ["is_scam_like"]
    assert fake_muse.calls == 0


@respx.mock
async def test_local_student_forwards_and_muse_answers_rest(settings, store, fake_muse):
    respx.post(f"{settings.hunch_url}/v1/answer").mock(return_value=httpx.Response(200, json={
        "answers": {"is_scam_like": {"type": "noul", "noul": 0.95, "answered_by": "backend"}}, "answered_by": "backend"}))
    r = await Screener(settings, store, fake_muse).screen_post(post(SCAM), "local")
    assert r.answered_by == "backend" and r.label == "high" and r.p_scam == 0.95
    assert r.pressure == 2 and fake_muse.calls == 2  # claim + pressure only; hunch's teacher did is_scam_like


@respx.mock
async def test_local_cached_yes_still_asks_muse_the_rest(settings, store, fake_muse):
    respx.post(f"{settings.hunch_url}/v1/answer").mock(return_value=httpx.Response(200, json={
        "answers": {"is_scam_like": {"type": "noul", "noul": 0.99, "answered_by": "cache"}}, "answered_by": "cache"}))
    r = await Screener(settings, store, fake_muse).screen_post(post(SCAM), "local")
    assert r.answered_by == "cache" and r.label == "high" and r.pressure == 2 and fake_muse.calls == 2


@respx.mock
async def test_jev_provider_maps_answers(settings, store, fake_muse):
    settings.typesafe_api_key = "t"
    respx.post("https://api.typesafe.ai/v1/systemone").mock(return_value=httpx.Response(200, json={
        "answers": {"is_scam_like": {"type": "noul", "noul": 0.9},
                    "has_checkable_claim": {"type": "noul", "noul": 0.2},
                    "pressure": {"type": "score", "score": 2.4, "probabilities": {"0": 0, "1": 0.1, "2": 0.4, "3": 0.5}}}}))
    r = await Screener(settings, store, fake_muse).screen_post(post(SCAM), "jev")
    assert r.label == "high" and r.provider == "jev" and r.answered_by == "jev" and r.pressure == 2


@respx.mock
async def test_jev_via_openrouter_when_only_openrouter_key(settings, store, fake_muse):
    settings.typesafe_api_key, settings.openrouter_key = "", "or-key"
    route = respx.post("https://openrouter.ai/api/alpha/decisions").mock(return_value=httpx.Response(200, json={
        "model": "typesafe/jev-1.13-20260917",
        "answers": {"is_scam_like": {"type": "noul", "noul": 0.97},
                    "has_checkable_claim": {"type": "noul", "noul": 0.2},
                    "pressure": {"type": "score", "probabilities": {"0": 0, "1": 0, "2": 0.64, "3": 0.36}}},
        "usage": {"cost": 0.000015}}))
    s = Screener(settings, store, fake_muse)
    assert s.available()["jev"] is True
    r = await s.screen_post(post(SCAM), "jev")
    body = json.loads(route.calls[0].request.content)
    assert body["model"] == "typesafe/jev-1.14" and set(body["questions"]) == {"is_scam_like", "has_checkable_claim", "pressure"}
    assert route.calls[0].request.headers["authorization"] == "Bearer or-key"
    assert r.answered_by == "jev" and r.label == "high" and fake_muse.calls == 0
    assert s.jev_spent_usd == 0.000015


async def test_jev_without_key_falls_back(settings, store, fake_muse):
    s = Screener(settings, store, fake_muse)
    assert s.available()["jev"] is False
    r = await s.screen_post(post(SCAM), "jev")
    assert r.answered_by == "fallback"


async def test_muse_error_falls_back(settings, store):
    class Boom:
        spent_usd = 0

        async def chat_json(self, *a, **k):
            raise RuntimeError("muse down")
    r = await Screener(settings, store, Boom()).screen_post(post(SCAM), "muse")
    assert r.answered_by == "fallback"


def make_client(settings, store, fake_muse):
    return TestClient(create_app(Services.build(settings, store=store, muse=fake_muse)))


def test_screen_endpoint_long_and_url_only(settings, store, fake_muse):
    c = make_client(settings, store, fake_muse)
    r = c.post("/screen", json={"posts": [
        {"id": "a", "platform": "facebook", "text": "飆股" * 2500},
        {"id": "b", "platform": "threads", "text": "https://bit.ly/x"}], "provider": "muse"})
    assert r.status_code == 200
    assert [x["post_id"] for x in r.json()["results"]] == ["a", "b"]


def test_screen_rejects_empty(settings, store, fake_muse):
    c = make_client(settings, store, fake_muse)
    r = c.post("/screen", json={"posts": [{"id": "a", "platform": "facebook", "text": ""}]})
    assert r.status_code == 422


def test_screen_caps_batch_and_providers_endpoint(settings, store, fake_muse):
    c = make_client(settings, store, fake_muse)
    many = [{"id": str(i), "platform": "facebook", "text": "hi"} for i in range(21)]
    assert c.post("/screen", json={"posts": many}).status_code == 422
    assert c.get("/providers").json() == {"local": True, "jev": False, "muse": True}
    assert c.get("/health").json()["ok"] is True


async def test_blocklisted_link_flags_high_without_asking_the_model(settings, store, fake_muse):
    from app.linkcheck import Blocklist
    s = Screener(settings, store, fake_muse, blocklist=Blocklist({"evil-invest.com": "investment"}))
    r = await s.screen_post(Post(id="b", platform="facebook", text="今天天氣好",
                                 link_domains=["evil-invest.com"]), "muse")
    assert r.label == "high" and r.answered_by == "blocklist" and r.scam_type == "investment"
    assert r.link_hit["domain"] == "evil-invest.com" and fake_muse.calls == 0


def test_local_provider_unavailable_without_hunch_url(store, fake_muse):
    from app.config import Settings
    s = Screener(Settings(muse_api="k", openrouter_key="", hunch_url=""), store, fake_muse)
    assert s.available()["local"] is False
