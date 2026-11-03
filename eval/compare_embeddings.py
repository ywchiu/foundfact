"""Compare google/embeddinggemma-2 with LargitData's earlier ywchiu/gemma-embed-peft on scam-case retrieval.

Retrieval tasks over data/cases.jsonl (137 fact-checked scam cases), no API calls:
  A. headline → case: query = the fact-check article's headline, corpus = the 137 case claim texts
     (the suspicious message as people saw it). Gold = the same case. Measures matching across phrasings.
  B. same scam type (leave-one-out): query = one case's claim text, corpus = the other 136. Gold = any case
     with the same scam_type. Measures whether neighbours share the tactic.
Plus throughput (texts/s) on this machine.

gemma-embed-peft is run as its HF card describes (base gemma-3-1b-pt + LoRA, last hidden state of the first
token, L2-normalised, 1152-d), with the card's two code typos fixed; masked mean pooling is reported as a
diagnostic.

    cd backend && uv run --with peft python ../eval/compare_embeddings.py
"""
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "eval"))
from app.cases import GemmaEncoder  # noqa: E402
from metrics import retrieval_metrics  # noqa: E402

PEFT_BASE = "unsloth/gemma-3-1b-pt"  # ungated mirror of google/gemma-3-1b-pt, as on the model card
PEFT_ADAPTER = "ywchiu/gemma-embed-peft"


class PeftEncoder:
    def __init__(self, pooling: str = "first"):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch, self.pooling = torch, pooling
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.tok = AutoTokenizer.from_pretrained(PEFT_ADAPTER)
        base = AutoModelForCausalLM.from_pretrained(PEFT_BASE, torch_dtype=torch.float32)
        self.model = PeftModel.from_pretrained(base, PEFT_ADAPTER).to(self.device).eval()

    def encode(self, texts: list[str], query: bool = False) -> np.ndarray:
        torch = self.torch
        out = []
        for i in range(0, len(texts), 16):
            batch = self.tok(texts[i:i + 16], padding=True, truncation=True, max_length=256,
                             return_tensors="pt").to(self.device)
            with torch.no_grad():
                h = self.model(**batch, output_hidden_states=True).hidden_states[-1]
            if self.pooling == "first":
                v = h[:, 0]
            else:
                m = batch["attention_mask"].unsqueeze(-1).to(h.dtype)
                v = (h * m).sum(1) / m.sum(1)
            out.append(torch.nn.functional.normalize(v.float(), dim=-1).cpu().numpy())
        return np.concatenate(out)


def evaluate(name: str, enc, cases: list[dict]) -> dict:
    claims = [c["claim_text"] for c in cases]
    titles = [c["title"] for c in cases]
    enc.encode(claims[:4])  # warm-up
    t0 = time.perf_counter()
    docs = enc.encode(claims)
    qs = enc.encode(titles, query=True)
    secs = time.perf_counter() - t0
    loo_q = enc.encode(claims, query=True)
    a = retrieval_metrics(qs @ docs.T, [{i} for i in range(len(cases))])
    types = [c["scam_type"] for c in cases]
    b = retrieval_metrics(loo_q @ docs.T, [{j for j, t in enumerate(types) if t == ti} for ti in types],
                          exclude_self=True)
    # spread of the vectors: a collapsed encoder gives near-identical vectors (mean pairwise cos → 1)
    pair = docs @ docs.T
    spread = float(pair[np.triu_indices(len(docs), 1)].mean())
    return {"model": name, "dim": int(docs.shape[1]), "headline_to_case": a, "same_type_loo": b,
            "texts_per_s": round(2 * len(cases) / secs, 1), "mean_pairwise_cos": round(spread, 3)}


def fmt(x):
    return "—" if x is None else f"{x:.2f}"


def main():
    cases = [json.loads(line) for line in open(ROOT / "data" / "cases.jsonl", encoding="utf-8")]
    types = Counter(c["scam_type"] for c in cases)
    runs = [("google/embeddinggemma-2", lambda: GemmaEncoder()),
            ("ywchiu/gemma-embed-peft (first-token, as on card)", lambda: PeftEncoder("first")),
            ("ywchiu/gemma-embed-peft (mean pooling, diagnostic)", lambda: PeftEncoder("mean"))]
    res = []
    for name, make in runs:
        print("…", name, flush=True)
        res.append(evaluate(name, make(), cases))
    out = ROOT / "eval" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "embedding_compare.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    # majority baseline for task B: P(random other case has the same type)
    n = len(cases)
    base = sum(k * (k - 1) for k in types.values()) / (n * (n - 1))
    lines = [
        "# Embedding comparison: EmbeddingGemma 2 vs gemma-embed-peft",
        "",
        f"Corpus: {n} fact-checked scam cases (`data/cases.jsonl`; types {dict(types)}). "
        f"Machine: {platform.machine()} {platform.system()}, PyTorch MPS/CPU, fp32.",
        "",
        "- **A. headline → case**: query = fact-check headline, corpus = 137 case texts; gold = the same case.",
        f"- **B. same scam type (leave-one-out)**: query = a case text, corpus = the other 136; gold = same "
        f"`scam_type`. Random-neighbour baseline hit@1 = {base:.2f}.",
        "- **mean pairwise cos**: average cosine between corpus vectors; near 1.0 means the vectors have collapsed.",
        "",
        "| model | dim | A hit@1 | A hit@3 | A MRR | B hit@1 | B hit@3 | texts/s | mean pairwise cos |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in res:
        a, b = r["headline_to_case"], r["same_type_loo"]
        lines.append(f"| {r['model']} | {r['dim']} | {fmt(a['hit@1'])} | {fmt(a['hit@3'])} | {fmt(a['mrr'])} | "
                     f"{fmt(b['hit@1'])} | {fmt(b['hit@3'])} | {r['texts_per_s']} | {r['mean_pairwise_cos']} |")
    (out / "embedding_compare.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
