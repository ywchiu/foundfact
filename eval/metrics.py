"""Pure metric helpers for run_eval.py (unit-tested in backend/tests/test_eval_metrics.py)."""
import itertools

import numpy as np

HI = [0.5, 0.6, 0.7, 0.8, 0.9]
MID = [0.2, 0.3, 0.4, 0.5]
CLAIM = [0.6, 0.7, 0.8, 0.9, 1.01]  # 1.01 = never flag on claims alone


def pct(xs, q):
    return float(np.percentile(xs, q, method="nearest")) if len(xs) else None


def label_metrics(gold: list[str], pred: list[str]) -> dict:
    n = len(gold)
    flag_g = [g != "none" for g in gold]
    flag_p = [p != "none" for p in pred]
    tp = sum(g and p for g, p in zip(flag_g, flag_p))
    return {"n": n, "accuracy": sum(g == p for g, p in zip(gold, pred)) / n if n else None,
            "flag_recall": tp / sum(flag_g) if sum(flag_g) else None,
            "flag_precision": tp / sum(flag_p) if sum(flag_p) else None}


def _decide(p_scam, p_claim, hi, mid, claim):
    return "high" if p_scam >= hi else "check" if (p_scam >= mid or p_claim >= claim) else "none"


def sweep(rows: list[dict]) -> dict:
    """Grid-search decide() thresholds on rows {gold, p_scam, p_claim}; best exact accuracy, then flag recall,
    then the most conservative (highest) thresholds."""
    best = None
    for hi, mid, claim in itertools.product(HI, MID, CLAIM):
        if mid >= hi:
            continue
        m = label_metrics([r["gold"] for r in rows], [_decide(r["p_scam"], r["p_claim"], hi, mid, claim) for r in rows])
        key = (m["accuracy"], m["flag_recall"] or 0, hi, mid, claim)
        if best is None or key > best[0]:
            best = (key, {"hi": hi, "mid": mid, "claim": claim} | m)
    return best[1]


def verdict_metrics(gold: list[str], pred: list[str]) -> dict:
    n = len(gold)
    ins = [p for g, p in zip(gold, pred) if g == "insufficient"]
    return {"n": n, "accuracy": sum(g == p for g, p in zip(gold, pred)) / n if n else None,
            "abstain_rate": sum(p == "insufficient" for p in ins) / len(ins) if ins else None}


def retrieval_metrics(sim, gold: list[set[int]], exclude_self: bool = False) -> dict:
    """hit@1, hit@3 and MRR for a query×corpus similarity matrix. gold[i] = corpus indices that count as
    correct for query i. exclude_self (leave-one-out, query i == corpus i): i is removed from the ranking and
    from gold; queries left with no gold are skipped."""
    import numpy as np
    h1 = h3 = rr = n = 0
    for i, g in enumerate(gold):
        s = np.asarray(sim[i], dtype=float).copy()
        g = set(g)
        if exclude_self:
            s[i] = -np.inf
            g.discard(i)
        if not g:
            continue
        order = np.argsort(-s, kind="stable")
        rank = next(r for r, j in enumerate(order, 1) if j in g)
        n += 1
        h1 += rank == 1
        h3 += rank <= 3
        rr += 1 / rank
    return {"n": n, "hit@1": h1 / n if n else None, "hit@3": h3 / n if n else None, "mrr": rr / n if n else None}
