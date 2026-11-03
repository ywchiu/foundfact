import json
from pathlib import Path

import httpx
import pytest
import respx

from app.config import Settings
from app.muse import MuseClient, MuseError

RAW = Path(__file__).resolve().parents[2] / "docs" / "notes" / "raw"
BASE = "https://api.meta.ai/v1"


def client():
    return MuseClient(Settings(muse_api="k"))


@respx.mock
async def test_chat_json_parses_content_and_tracks_cost():
    respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(200, json=json.loads(
        (RAW / "1_chat_json.json").read_text())))
    m = client()
    out = await m.chat_json("sys", "user", {"type": "object"}, "a")
    assert out == {"p_yes": 0.99}
    assert m.spent_usd > 0


@respx.mock
async def test_search_extracts_deduped_evidence():
    respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(200, json=json.loads(
        (RAW / "2_responses_search.json").read_text())))
    m = client()
    text, ev = await m.search("q", "zh")
    assert "詐騙" in text
    urls = [e.url for e in ev]
    assert len(urls) == len(set(urls)) and len(ev) >= 3
    assert [e.id for e in ev][:2] == ["w1", "w2"]
    tfc = next(e for e in ev if "tfc-taiwan" in (e.url or ""))
    assert tfc.title.startswith("近期社群出現") and tfc.snippet  # snippet from citation span
    assert m.spent_usd > 0.05  # tokens + 5 searches


@respx.mock
async def test_5xx_retries_then_raises():
    route = respx.post(f"{BASE}/chat/completions").mock(return_value=httpx.Response(503, json={}))
    m = client()
    with pytest.raises(MuseError):
        await m.chat_json("s", "u", {"type": "object"}, "a")
    assert route.call_count == 2  # one retry: a Muse outage must not hold a report step for minutes


SSE = "\n".join([
    'data: {"type":"response.output_item.done","item":{"type":"message","phase":"commentary","content":[{"type":"output_text","text":"正在查證"}]}}',
    "",
    'data: {"type":"response.output_item.done","item":{"type":"web_search_call","status":"completed","action":{"type":"search","query":"魏哲家 詐騙"},"results":[{"type":"text_result","title":"T1","url":"https://a.tw/1","snippet":""}]}}',
    "",
    'data: {"type":"response.output_item.done","item":{"type":"message","content":[{"type":"output_text","text":"結論：假的","annotations":[{"type":"url_citation","url":"https://a.tw/1","title":"T1","start_index":0,"end_index":5}]}]}}',
    "",
    'data: {"type":"response.completed","response":{"usage":{"input_tokens":1000,"output_tokens":100}}}',
    "",
])


@respx.mock
async def test_search_stream_yields_progress_then_final():
    respx.post(f"{BASE}/responses").mock(return_value=httpx.Response(
        200, text=SSE, headers={"content-type": "text/event-stream"}))
    m = client()
    events = [e async for e in m.search_stream("q", "zh")]
    kinds = [e["kind"] for e in events]
    assert kinds == ["commentary", "search", "final"]
    assert events[1]["detail"] == "魏哲家 詐騙"
    final = events[-1]
    assert final["text"] == "結論：假的" and final["evidence"][0].snippet == "結論：假的"


def test_evidence_snippets_strip_markdown():
    items = [{"type": "message", "content": [{"text": "* **官方** 澄清 `x`", "annotations": [
        {"type": "url_citation", "url": "https://a", "title": "T", "start_index": 0, "end_index": 16}]}]}]
    _, ev, _ = MuseClient._evidence(items)
    assert "**" not in ev[0].snippet and "`" not in ev[0].snippet and ev[0].snippet.startswith("官方")


def test_search_body_bounds_depth_and_requires_citations(settings):
    # unbounded search took ~60 s and US$0.7 per post (20 searches, 9 page opens incl. YouTube)
    body = MuseClient(settings)._search_body("c1. x", "zh", True)
    assert body["reasoning"] == {"effort": "low"}
    assert "最多搜尋 3 次" in body["input"] and "影片" in body["input"] and "引用" in body["input"]


async def test_image_fetch_refuses_private_addresses(monkeypatch):
    from app import linkcheck
    monkeypatch.setattr(linkcheck, "_host_ips", lambda h: ["169.254.169.254"])
    with pytest.raises(MuseError):
        await client().fetch_data_url("http://metadata.internal/latest")


@respx.mock
async def test_image_fetch_stops_reading_past_the_size_cap(monkeypatch):
    from app import linkcheck
    monkeypatch.setattr(linkcheck, "_host_ips", lambda h: ["93.184.216.34"])
    respx.get("https://cdn.example/big.jpg").mock(return_value=httpx.Response(
        200, headers={"content-type": "image/jpeg"}, content=b"x" * 6_000_000))
    with pytest.raises(MuseError):
        await client().fetch_data_url("https://cdn.example/big.jpg")


async def test_vision_read_passes_data_url_and_returns_text(monkeypatch):
    m = client()
    seen = {}

    async def fake_chat(system, user, schema, name, effort="minimal", images=None):
        seen["images"], seen["schema"] = images, schema
        return {"description": "a parcel notice", "text": "Update at https://x.cc"}
    monkeypatch.setattr(m, "chat_json", fake_chat)
    out = await m.vision_read("data:image/png;base64,AAAA", "en")
    assert out == {"description": "a parcel notice", "text": "Update at https://x.cc"}
    assert seen["images"] == ["data:image/png;base64,AAAA"]
    assert set(seen["schema"]["required"]) == {"description", "text"}
