"""Known scam case stores: EmbeddingGemma 2 kNN (CaseStore) or bigram shortlist + Jev (JevCaseStore)."""
import json
from pathlib import Path
from typing import Protocol

import httpx
import numpy as np

from .models import SimilarCase


class Encoder(Protocol):
    def encode(self, texts: list[str], query: bool = False) -> np.ndarray: ...


class GemmaEncoder:
    """google/embeddinggemma-2 via sentence-transformers. Prompts per model card:
    queries use prompt_name="SearchQuery" ("task: search result | query: ..."),
    documents use prompt_name="Document" ("title: none | text: ...")."""

    def __init__(self, name: str = "google/embeddinggemma-2", device: str | None = None):
        from sentence_transformers import SentenceTransformer
        import torch
        device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.model = SentenceTransformer(name, device=device)

    def encode(self, texts: list[str], query: bool = False) -> np.ndarray:
        if not texts:
            return np.zeros((0, 768), dtype=np.float32)
        return self.model.encode(texts, prompt_name="SearchQuery" if query else "Document",
                                 normalize_embeddings=True, batch_size=32,
                                 convert_to_numpy=True).astype(np.float32)


class CaseStore:
    def __init__(self, path: Path, encoder: Encoder):
        self.path = Path(path)
        self.encoder = encoder
        self.cases = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()] \
            if self.path.exists() else []
        self.vecs = self._load_vectors()

    def _load_vectors(self) -> np.ndarray:
        cache = self.path.with_suffix(".npy")
        meta = self.path.with_suffix(".npy.meta")
        stamp = f"{self.path.stat().st_mtime if self.path.exists() else 0}:{len(self.cases)}"
        if cache.exists() and meta.exists() and meta.read_text() == stamp:
            return np.load(cache)
        vecs = self.embed([c["claim_text"] for c in self.cases])
        if self.cases:
            np.save(cache, vecs)
            meta.write_text(stamp)
        return vecs

    def embed(self, texts: list[str], query: bool = False) -> np.ndarray:
        return self.encoder.encode(texts, query=query)

    def knn(self, text: str, k: int = 3) -> list[SimilarCase]:
        if not self.cases:
            return []
        q = self.embed([text], query=True)[0]
        sims = self.vecs @ q
        idx = np.argsort(-sims)[:k]
        return [SimilarCase(case_id=self.cases[i]["case_id"],
                            title=self.cases[i].get("title") or self.cases[i]["claim_text"][:60],
                            scam_type=self.cases[i]["scam_type"], similarity=round(float(sims[i]), 4),
                            url=self.cases[i].get("url")) for i in idx]


def _bigrams(s: str) -> set[str]:
    s = "".join(ch.lower() for ch in s if not ch.isspace())
    return {s[i:i + 2] for i in range(len(s) - 1)} or ({s} if s else set())


class JevCaseStore:
    """Known-case matching without a local embedding model (small servers): a character-bigram shortlist,
    then one Jev request that asks, per shortlisted case, whether the post runs the same scam scheme.
    similarity = Jev's probability. Same .cases / .knn interface as CaseStore."""

    INSTRUCTIONS = ("Is the social media post `post` running the same scam scheme as the known scam case "
                    "`cases.{cid}` (same kind of lure and the same ask, e.g. add LINE, pay a fee, click a link), "
                    "even if names, numbers or wording differ?")

    def __init__(self, path: Path, settings, shortlist: int = 5):
        self.path, self.s, self.shortlist = Path(path), settings, shortlist
        self.cases = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()] \
            if self.path.exists() else []
        self.grams = [_bigrams(c["claim_text"] + c.get("title", "")) for c in self.cases]
        self.spent_usd = 0.0

    def _endpoint(self):
        if self.s.typesafe_api_key:
            return f"{self.s.typesafe_base}/systemone", self.s.typesafe_api_key, "jev-latest"
        if self.s.openrouter_key:
            return self.s.openrouter_decisions, self.s.openrouter_key, self.s.jev_openrouter_model
        return None

    def knn(self, text: str, k: int = 3) -> list[SimilarCase]:
        ep = self._endpoint()
        if not self.cases or not ep:
            return []
        q = _bigrams(text)
        lex = [len(q & g) / (len(q | g) or 1) for g in self.grams]
        idx = sorted(range(len(self.cases)), key=lambda i: -lex[i])[: self.shortlist]
        cand = {self.cases[i]["case_id"]: i for i in idx}
        state = {"post": text[:2000], "cases": {cid: self.cases[i]["claim_text"] for cid, i in cand.items()}}
        questions = {cid: {"type": "noul", "instructions": self.INSTRUCTIONS.format(cid=cid)} for cid in cand}
        url, key, model = ep
        try:
            r = httpx.post(url, headers={"Authorization": f"Bearer {key}"}, timeout=8,
                           json={"model": model, "state": state, "questions": questions})
            r.raise_for_status()
            data = r.json()
            self.spent_usd += float((data.get("usage") or {}).get("cost") or 0)
            ps = {cid: float(a["noul"]) for cid, a in data["answers"].items() if cid in cand}
        except (httpx.HTTPError, KeyError, ValueError, TypeError):
            return []
        top = sorted(ps, key=lambda c: -ps[c])[:k]
        return [SimilarCase(case_id=cid, title=self.cases[cand[cid]].get("title") or self.cases[cand[cid]]["claim_text"][:60],
                            scam_type=self.cases[cand[cid]]["scam_type"], similarity=round(ps[cid], 4),
                            url=self.cases[cand[cid]].get("url")) for cid in top]
