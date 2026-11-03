import json

from fastapi.testclient import TestClient

from app.agent import Verifier
from app.linkcheck import Blocklist
from app.api import Services, create_app
from app.models import Evidence, Post
from app.muse import MuseError

SCAM = Post(id="p1", platform="facebook", text="魏哲家老師帶你買飆股 保證月報酬30% 加LINE lin.ee/abc",
            link_domains=["lin.ee"])


class AgentMuse:
    def __init__(self, judge_ids=("w1",), search_fail=False, no_web=False, image_text="", vision_fail=False):
        self.judge_ids, self.search_fail, self.no_web = list(judge_ids), search_fail, no_web
        self.image_text, self.vision_fail = image_text, vision_fail
        self.spent_usd = 0.0
        self.names = []
        self.prompts = {}

    async def chat_json(self, system, user, schema, name, effort="minimal", images=None):
        self.names.append(name)
        self.prompts[name] = user
        if name == "claims":
            return {"claims": ["魏哲家在LINE群組帶單", "保證月報酬30%"]}
        if name == "verdicts":
            return {"verdicts": [
                {"claim_id": "c1", "verdict": "refuted", "evidence_ids": self.judge_ids, "rationale": "官方澄清"},
                {"claim_id": "c2", "verdict": "refuted", "evidence_ids": ["nope"], "rationale": "x"}]}
        if name == "conclusion":
            return {"risk": "high", "summary": "典型投資詐騙", "actions": ["不要加入LINE群組"]}
        raise AssertionError(name)

    async def search_stream(self, query, lang):
        if self.search_fail:
            raise MuseError("boom")
        yield {"kind": "commentary", "detail": "正在查證"}
        yield {"kind": "search", "detail": "魏哲家 詐騙"}
        ev = [] if self.no_web else [Evidence(id="w1", source_type="web", url="https://tfc-taiwan.org.tw/x",
                                              title="假帳號", snippet="魏哲家沒有經營社群")]
        yield {"kind": "final", "text": "假的", "evidence": ev}

    async def vision_read(self, url, lang):
        if self.vision_fail:
            raise MuseError("vision down")
        return {"description": "圖片顯示名人照片與LINE QR code", "text": self.image_text}


def run(verifier, post=SCAM, lang="zh"):
    import asyncio

    async def go():
        return [e async for e in verifier.stream(post, lang)]
    return asyncio.run(go())


def steps(events):
    return [(e[1]["step"], e[1]["status"]) for e in events if e[0] == "step"]


def report(events):
    return next(e[1] for e in events if e[0] == "report")


def test_stream_order(store):
    ev = run(Verifier(AgentMuse(), store, blocklist=Blocklist()))
    order = []
    for s, st in steps(ev):
        if st == "done":
            order.append(s)
    assert order == ["extract", "local", "search", "judge", "conclude"]
    for s in order:
        assert (s, "running") in steps(ev)
    assert [e[0] for e in ev][-2:] == ["report", "done"]


def test_bad_evidence_ids_become_insufficient(store):
    r = report(run(Verifier(AgentMuse(), store, blocklist=Blocklist())))
    verdicts = {v["claim_id"]: v["verdict"] for v in r["verdicts"]}
    assert verdicts == {"c1": "refuted", "c2": "insufficient"}


def test_search_failure_still_reports(store):
    ev = run(Verifier(AgentMuse(search_fail=True), store, blocklist=Blocklist()))
    assert ("search", "error") in steps(ev)
    assert [e[0] for e in ev][-2:] == ["report", "done"]


def test_no_web_results_message(store):
    ev = run(Verifier(AgentMuse(no_web=True), store, blocklist=Blocklist()))
    done = [e[1]["detail"] for e in ev if e[0] == "step" and e[1]["step"] == "search" and e[1]["status"] == "done"]
    assert "未找到網路來源" in done[0]
    en = run(Verifier(AgentMuse(no_web=True), store, blocklist=Blocklist()), lang="en")
    done = [e[1]["detail"] for e in en if e[0] == "step" and e[1]["step"] == "search" and e[1]["status"] == "done"]
    assert "No web sources found" in done[0]


def test_image_step_only_with_images(store):
    assert not any(s == "image" for s, _ in steps(run(Verifier(AgentMuse(), store, blocklist=Blocklist()))))
    with_img = SCAM.model_copy(update={"image_urls": ["https://x/img.jpg"]})
    ev = run(Verifier(AgentMuse(), store, blocklist=Blocklist()), post=with_img)
    assert ("image", "done") in steps(ev)
    assert any(e["source_type"] == "image" for e in report(ev)["evidence"])


def test_blocklist_hit_becomes_evidence_and_165_action(store):
    bad = SCAM.model_copy(update={"link_domains": ["lin.ee", "app.evil-invest.com"]})
    r = report(run(Verifier(AgentMuse(), store, blocklist=Blocklist({"evil-invest.com": "investment"})), post=bad))
    hit = [e for e in r["evidence"] if e["source_type"] == "blocklist"]
    assert len(hit) == 1 and hit[0]["title"] == "evil-invest.com" and "警政署" in hit[0]["snippet"]
    assert any("165" in a for a in r["actions"])


def test_verify_endpoint_streams_sse(settings, store):
    svc = Services.build(settings, store=store, muse=AgentMuse())
    c = TestClient(create_app(svc))
    with c.stream("POST", "/verify", json={"post": json.loads(SCAM.model_dump_json()), "lang": "zh"}) as r:
        assert r.status_code == 200
        body = "".join(r.iter_text())
    assert "event: step" in body and "event: report" in body and "event: done" in body


def test_web_evidence_capped(store):
    class Many(AgentMuse):
        async def search_stream(self, query, lang):
            yield {"kind": "final", "text": "", "evidence": [
                Evidence(id=f"w{i}", source_type="web", url=f"https://s/{i}", title="t", snippet="")
                for i in range(40)]}
    r = report(run(Verifier(Many(), store, blocklist=Blocklist())))
    assert sum(e["source_type"] == "web" for e in r["evidence"]) == 12


def test_open_page_detail_is_short_and_count_is_capped(store):
    class Pages(AgentMuse):
        async def search_stream(self, query, lang):
            yield {"kind": "open_page", "detail": "https://www.sfb.gov.tw/uploaddowndoc?file=publication/2024.pdf&filedisplay=05-%E5%B0%88%E9%A1%8C%E5%A0%B1%E5%B0%8E"}
            yield {"kind": "final", "text": "", "evidence": [
                Evidence(id=f"w{i}", source_type="web", url=f"https://s/{i}", title="t", snippet="")
                for i in range(30)]}
    ev = run(Verifier(Pages(), store, blocklist=Blocklist()))
    details = [e[1]["detail"] for e in ev if e[0] == "step" and e[1]["step"] == "search"]
    page = next(d for d in details if d.startswith("📄"))
    assert "%E5" not in page and "sfb.gov.tw" in page and len(page) <= 70
    assert details[-1] == "找到 12 個網路來源"


class LowMuse(AgentMuse):
    async def chat_json(self, system, user, schema, name, effort="minimal", images=None):
        if name == "conclusion":
            self.last_conclusion_prompt = user
            return {"risk": "low", "summary": "looks fine", "actions": []}
        return await super().chat_json(system, user, schema, name, effort, images)


def test_blocklist_hit_floors_risk_at_high_even_if_model_says_low(store):
    bad = SCAM.model_copy(update={"link_domains": ["app.evil-invest.com"]})
    r = report(run(Verifier(LowMuse(), store, blocklist=Blocklist({"evil-invest.com": "investment"})), post=bad))
    assert r["risk"] == "high" and any("165" in a for a in r["actions"])


def test_refuted_claim_floors_risk_at_check(store):
    r = report(run(Verifier(LowMuse(), store, blocklist=Blocklist()), post=SCAM))
    assert r["risk"] == "check"


def test_post_text_is_fenced_as_untrusted_data_in_conclusion_prompt(store):
    m = LowMuse()
    run(Verifier(m, store, blocklist=Blocklist()), post=SCAM)
    assert "<post>" in m.last_conclusion_prompt and "</post>" in m.last_conclusion_prompt


IMG = "data:image/png;base64," + "A" * 64


def test_image_is_read_before_extraction_and_its_text_is_checked(store):
    muse = AgentMuse(image_text="【郵局】包裹無法投遞 請至 https://post-tw.cc/u8x 更新")
    post = Post(id="p9", platform="web", text="", image_urls=[IMG])
    ev = run(Verifier(muse, store, blocklist=Blocklist({"post-tw.cc": "phishing"})), post=post)
    order = [s for s, st in steps(ev) if st == "running"]
    assert order.index("image") < order.index("extract")
    assert "post-tw.cc/u8x" in muse.prompts["claims"]
    r = report(ev)
    assert any(e["source_type"] == "blocklist" and e["title"] == "post-tw.cc" for e in r["evidence"])
    assert r["risk"] == "high"


def test_uploaded_image_evidence_has_no_url(store):
    post = Post(id="p9", platform="web", text="看圖", image_urls=[IMG])
    r = report(run(Verifier(AgentMuse(), store, blocklist=Blocklist()), post=post))
    img = [e for e in r["evidence"] if e["source_type"] == "image"]
    assert img and img[0]["url"] is None


def test_image_without_text_uses_description(store):
    muse = AgentMuse(image_text="")
    post = Post(id="p9", platform="web", text="", image_urls=[IMG])
    run(Verifier(muse, store, blocklist=Blocklist()), post=post)
    assert "LINE QR code" in muse.prompts["claims"]


def test_unreadable_image_only_post_ends_with_error(store):
    post = Post(id="p9", platform="web", text="", image_urls=[IMG])
    ev = run(Verifier(AgentMuse(vision_fail=True), store, blocklist=Blocklist()), post=post)
    assert ev[-1] == ("error", {"error": "image_unreadable"})
    assert not any(e[0] == "report" for e in ev)


def test_post_image_is_not_evidence_for_its_own_claims(store):
    muse = AgentMuse(image_text="包裹無法投遞")
    post = Post(id="p9", platform="web", text="", image_urls=[IMG])
    r = report(run(Verifier(muse, store, blocklist=Blocklist()), post=post))
    assert '"i1"' not in muse.prompts["verdicts"]
    img = next(e for e in r["evidence"] if e["source_type"] == "image")
    assert img["title"] == "貼文圖片"


def test_verdict_citing_the_post_image_becomes_insufficient(store):
    class CitesImage(AgentMuse):
        async def chat_json(self, system, user, schema, name, effort="minimal", images=None):
            if name == "verdicts":
                return {"verdicts": [{"claim_id": "c1", "verdict": "supported", "evidence_ids": ["i1"], "rationale": "x"}]}
            return await super().chat_json(system, user, schema, name, effort, images)
    post = Post(id="p9", platform="web", text="看圖", image_urls=[IMG])
    r = report(run(Verifier(CitesImage(), store, blocklist=Blocklist()), post=post))
    assert {v["claim_id"]: v["verdict"] for v in r["verdicts"]}["c1"] == "insufficient"
