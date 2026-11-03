import json
import zlib

import numpy as np

from app.cases import CaseStore


class FakeEncoder:
    """Bag-of-characters hashing encoder; similar strings → similar vectors."""

    def encode(self, texts, query=False):
        out = np.zeros((len(texts), 64), dtype=np.float32)
        for i, t in enumerate(texts):
            for ch in t:
                out[i, zlib.crc32(ch.encode()) % 64] += 1
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(n == 0, 1, n)


def write_cases(path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))


ROWS = [
    {"case_id": "k1", "scam_type": "investment", "claim_text": "保證月報酬30% 加LINE領飆股",
     "verdict_text": "假投資", "source": "tfc", "url": "https://a/1", "date": "2026-10-01", "title": "飆股群組詐騙"},
    {"case_id": "k2", "scam_type": "phishing", "claim_text": "您的包裹地址錯誤請點連結更新",
     "verdict_text": "釣魚", "source": "mygopen", "url": "https://a/2", "date": "2026-09-01", "title": "包裹簡訊"},
    {"case_id": "k3", "scam_type": "shopping", "claim_text": "名牌包一折限時搶購",
     "verdict_text": "假購物", "source": "mygopen", "url": "https://a/3", "date": "2026-08-01", "title": "一折名牌"},
]


def test_knn_returns_sorted_top_k(tmp_path):
    p = tmp_path / "cases.jsonl"
    write_cases(p, ROWS)
    store = CaseStore(p, FakeEncoder())
    res = store.knn("保證報酬 加LINE 飆股", k=2)
    assert len(res) == 2
    assert res[0].case_id == "k1" and res[0].scam_type == "investment"
    assert res[0].similarity >= res[1].similarity


def test_knn_empty_store(tmp_path):
    p = tmp_path / "cases.jsonl"
    p.write_text("")
    assert CaseStore(p, FakeEncoder()).knn("anything") == []


def test_embeddings_cached_and_invalidated(tmp_path):
    p = tmp_path / "cases.jsonl"
    write_cases(p, ROWS[:2])
    CaseStore(p, FakeEncoder())
    assert (tmp_path / "cases.npy").exists()
    write_cases(p, ROWS)
    import os
    os.utime(p, (p.stat().st_atime, p.stat().st_mtime + 5))
    assert len(CaseStore(p, FakeEncoder()).knn("x", k=5)) == 3


def _jev_route(ps):
    import httpx
    import respx

    def reply(request):
        q = json.loads(request.content)["questions"]
        return httpx.Response(200, json={"answers": {k: {"type": "noul", "noul": ps.get(k, 0.1)} for k in q},
                                         "usage": {"cost": 0.00002}})
    return respx.post("https://openrouter.ai/api/alpha/decisions").mock(side_effect=reply)


def test_jev_store_shortlists_lexically_then_ranks_by_jev(tmp_path):
    import respx
    from app.cases import JevCaseStore
    from app.config import Settings
    p = tmp_path / "cases.jsonl"
    write_cases(p, ROWS)
    with respx.mock:
        route = _jev_route({"k1": 0.92})
        store = JevCaseStore(p, Settings(openrouter_key="or", data_dir=tmp_path), shortlist=2)
        res = store.knn("保證報酬 加LINE 飆股", k=2)
    body = json.loads(route.calls[0].request.content)
    assert set(body["questions"]) == {"k1", "k2"} or "k1" in body["questions"]
    assert len(body["questions"]) == 2 and body["model"] == "typesafe/jev-1.14"
    assert "保證月報酬30%" in json.dumps(body["state"], ensure_ascii=False)
    assert res[0].case_id == "k1" and res[0].similarity == 0.92
    assert store.spent_usd == 0.00002


def test_jev_store_without_key_or_on_error_returns_no_matches(tmp_path):
    import httpx
    import respx
    from app.cases import JevCaseStore
    from app.config import Settings
    p = tmp_path / "cases.jsonl"
    write_cases(p, ROWS)
    assert JevCaseStore(p, Settings(openrouter_key="", typesafe_api_key="", data_dir=tmp_path)).knn("飆股") == []
    with respx.mock:
        respx.post("https://openrouter.ai/api/alpha/decisions").mock(return_value=httpx.Response(500))
        assert JevCaseStore(p, Settings(openrouter_key="or", data_dir=tmp_path)).knn("飆股") == []


def test_services_use_jev_matcher_when_configured(tmp_path):
    from app.api import Services
    from app.cases import JevCaseStore
    from app.config import Settings
    write_cases(tmp_path / "cases.jsonl", ROWS)
    s = Services.build(Settings(muse_api="k", openrouter_key="or", case_matcher="jev", data_dir=tmp_path), muse=object())
    assert isinstance(s.store, JevCaseStore) and s.screener.store is s.store and s.verifier.store is s.store
