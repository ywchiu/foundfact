"""Stage 1 (System 1) screening: provider = local (hunch) | jev (TypeSafe) | muse, with rule+kNN fallback."""
import asyncio
import re
import time

import httpx

from .cases import CaseStore
from .config import Settings
from .guard import clip_text
from .linkcheck import Blocklist, check_links
from .models import Post, Provider, ScreenResult
from .teacher import QUESTIONS, answer

TYPE_SIM = 0.75  # kNN similarity needed before we name a scam type (unrelated text sits ~0.65)

RULES: list[tuple[str, re.Pattern]] = [
    ("guaranteed_returns", re.compile(r"保證(獲利|報酬|賺)|穩賺|零風險|月報酬|日賺|翻倍|guaranteed (return|profit)", re.I)),
    ("line_redirect", re.compile(r"加\s*(line|賴)|line\s*群|lin\.ee|line\.me|私訊|加入群組|add (me on )?line", re.I)),
    ("hot_stock", re.compile(r"飆股|明牌|帶單|老師帶|跟單|內線", re.I)),
    ("urgency", re.compile(r"限時|最後\s*\d|倒數|立即|馬上|名額有限|今天截止|act now|limited time", re.I)),
    ("free_gift", re.compile(r"免費(領|送)|抽獎|中獎|贈送|領取|free gift|you won", re.I)),
    ("account_alert", re.compile(r"帳戶(異常|凍結)|驗證(身分|帳戶)|重複(扣款|訂閱)|解除分期|account (locked|suspended)", re.I)),
    ("click_link", re.compile(r"點(此|擊)?(連結|網址)|請點|click (here|the link)", re.I)),
]
SHORT_DOMAINS = {"bit.ly", "reurl.cc", "tinyurl.com", "lin.ee", "t.ly", "pse.is", "is.gd", "ppt.cc", "shorturl.at"}
URL_RE = re.compile(r"https?://([^/\s]+)|\b((?:[a-z0-9-]+\.)+[a-z]{2,})/", re.I)


def decide(p_scam: float, p_claim: float, hi: float = 0.8, mid: float = 0.5, claim: float = 1.01) -> str:
    # thresholds from the tune-split sweep (eval/results/tune.md); claim=1.01 disables claim-only flags
    if p_scam >= hi:
        return "high"
    if p_scam >= mid or p_claim >= claim:
        return "check"
    return "none"


def domains_of(post: Post) -> set[str]:
    found = {m.group(1) or m.group(2) for m in URL_RE.finditer(post.text)}
    return {d.lower().removeprefix("www.") for d in found | set(post.link_domains) if d}


def rule_score(post: Post) -> tuple[float, list[str]]:
    hits = [name for name, rx in RULES if rx.search(post.text)]
    if domains_of(post) & SHORT_DOMAINS:
        hits.append("short_link")
    return (0.85 if len(hits) >= 2 else 0.5 if hits else 0.0), hits


def expected_level(probs: dict) -> int:
    return int(round(sum(int(k) * float(v) for k, v in probs.items())))


class FallbackStage1:
    def __init__(self, store: CaseStore):
        self.store = store

    async def screen(self, post: Post, provider: Provider) -> ScreenResult:
        similar = await asyncio.to_thread(self.store.knn, post.text, 3)
        rs, _ = rule_score(post)
        knn = similar[0].similarity if similar else 0.0
        # map kNN similarity (unrelated≈0.65, near-duplicate≈0.9) to a scam score
        knn_score = max(0.0, min(1.0, (knn - 0.65) / 0.25))
        p = max(rs, knn_score)
        return _result(post, p, 0.5, None, similar, "fallback", provider)


def _result(post, p_scam, p_claim, pressure, similar, by, provider) -> ScreenResult:
    top = similar[0] if similar else None
    return ScreenResult(post_id=post.id, label=decide(p_scam, p_claim), p_scam=round(p_scam, 4),
                        p_claim=round(p_claim, 4), pressure=pressure,
                        scam_type=top.scam_type if top and top.similarity >= TYPE_SIM else None,
                        similar=similar, answered_by=by, provider=provider)


def _from_answers(post, ans: dict, similar, by, provider) -> ScreenResult:
    pr = ans.get("pressure") or {}
    pressure = expected_level(pr["probabilities"]) if pr.get("probabilities") else None
    return _result(post, float(ans["is_scam_like"]["noul"]), float(ans["has_checkable_claim"]["noul"]),
                   pressure, similar, by, provider)


def _state(post: Post, max_chars: int) -> dict:
    return {"platform": post.platform, "author": post.author, "text": clip_text(post.text, max_chars),
            "link_domains": sorted(domains_of(post))}


class Screener:
    def __init__(self, settings: Settings, store: CaseStore, muse, blocklist: Blocklist | None = None):
        self.s, self.store, self.muse = settings, store, muse
        self.blocklist = blocklist or Blocklist()
        self.fallback = FallbackStage1(store)
        self.jev_spent_usd = 0.0

    def available(self) -> dict[str, bool]:
        return {"local": bool(self.s.hunch_url), "jev": bool(self.s.typesafe_api_key or self.s.openrouter_key), "muse": bool(self.s.muse_api)}

    async def _muse(self, state):
        return (await answer({"state": state, "questions": QUESTIONS}, self.muse))["answers"]

    async def _hunch(self, state):
        """Cascade: the local EmbeddingGemma 2 student (hunch) answers is_scam_like; it graduated one-sided,
        so it answers only a confident "no" itself and forwards the rest to its teacher (Muse). Only then are
        the other two questions (which never graduated, docs/notes/hunch-preflight.md) asked of Muse."""
        rest = {k: q for k, q in QUESTIONS.items() if k != "is_scam_like"}
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(f"{self.s.hunch_url}/v1/answer",
                             json={"state": state, "questions": {"is_scam_like": QUESTIONS["is_scam_like"]}})
            r.raise_for_status()
            out = r.json()
        ans = dict(out["answers"])
        by = out.get("answered_by") if out.get("answered_by") in ("proxy", "cache") else "backend"
        if by != "backend" and ans["is_scam_like"]["noul"] < 0.5:  # low risk without a teacher call: done
            ans["has_checkable_claim"] = {"type": "noul", "noul": 0.0}
            return ans, by
        more = await answer({"state": state, "questions": rest}, self.muse)
        return ans | more["answers"], by

    async def _jev(self, state):
        if self.s.typesafe_api_key:
            url, key, model = f"{self.s.typesafe_base}/systemone", self.s.typesafe_api_key, "jev-latest"
        else:  # same request/response shape on OpenRouter's decisions endpoint
            url, key, model = self.s.openrouter_decisions, self.s.openrouter_key, self.s.jev_openrouter_model
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(url, headers={"Authorization": f"Bearer {key}"},
                             json={"model": model, "state": state, "questions": QUESTIONS})
            r.raise_for_status()
            data = r.json()
        self.jev_spent_usd += float((data.get("usage") or {}).get("cost") or 0)
        return data["answers"]

    async def screen_post(self, post: Post, provider: Provider = "muse", paid: bool = True) -> ScreenResult:
        t0 = time.perf_counter()
        try:
            hit = await check_links(post, self.blocklist)
        except Exception:
            hit = None
        if hit:  # known fraud domain: no model call
            return ScreenResult(post_id=post.id, label="high", p_scam=1.0, p_claim=0.0, pressure=None,
                                scam_type=hit["category"], similar=[], answered_by="blocklist", provider=provider,
                                latency_ms=int((time.perf_counter() - t0) * 1000), link_hit=hit)
        state = _state(post, self.s.max_chars)
        if not paid:  # daily budget spent: keyword rules only (case matching may call Jev, so skip it too)
            p, _ = rule_score(post.model_copy(update={"text": state["text"]}))
            res = _result(post, p, 0.5, None, [], "fallback", provider)
            res.latency_ms = int((time.perf_counter() - t0) * 1000)
            return res
        sim_task = asyncio.create_task(asyncio.to_thread(self.store.knn, state["text"], 3))
        try:
            if not self.available()[provider]:
                raise RuntimeError(f"provider {provider} unavailable")
            if provider == "muse":
                ans, by = await asyncio.wait_for(self._muse(state), 8), "muse"
            elif provider == "jev":
                ans, by = await asyncio.wait_for(self._jev(state), 8), "jev"
            else:
                ans, by = await asyncio.wait_for(self._hunch(state), 12)
            res = _from_answers(post, ans, await sim_task, by, provider)
        except Exception:
            sim_task.cancel()
            res = await self.fallback.screen(post.model_copy(update={"text": state["text"]}), provider)
        res.latency_ms = int((time.perf_counter() - t0) * 1000)
        return res
