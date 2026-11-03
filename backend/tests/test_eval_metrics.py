import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval"))
from metrics import label_metrics, pct, sweep, verdict_metrics  # noqa: E402


def test_label_metrics_exact_and_flag():
    m = label_metrics(["high", "none", "high", "none"], ["high", "check", "none", "none"])
    assert m["accuracy"] == 0.5
    assert m["flag_recall"] == 0.5 and m["flag_precision"] == 0.5 and m["n"] == 4


def test_sweep_picks_threshold_that_fits_gold():
    rows = [{"gold": "high", "p_scam": 0.65, "p_claim": 0.1}, {"gold": "none", "p_scam": 0.35, "p_claim": 0.9},
            {"gold": "none", "p_scam": 0.05, "p_claim": 0.2}]
    best = sweep(rows)
    assert best["accuracy"] == 1.0
    assert best["hi"] <= 0.65 and best["mid"] > 0.35 and best["claim"] > 0.9


def test_verdict_metrics_accuracy_and_abstain():
    gold = ["refuted", "refuted", "insufficient", "insufficient"]
    pred = ["refuted", "supported", "insufficient", "refuted"]
    m = verdict_metrics(gold, pred)
    assert m["accuracy"] == 0.5 and m["abstain_rate"] == 0.5 and m["n"] == 4


def test_pct():
    assert pct([1, 2, 3, 4, 100], 50) == 3 and pct([], 50) is None


def test_retrieval_metrics_hits_and_mrr():
    import numpy as np
    from metrics import retrieval_metrics
    sim = np.array([[0.9, 0.1, 0.5],   # gold 0 ranked 1st
                    [0.8, 0.2, 0.9],   # gold 1 ranked 3rd
                    [0.1, 0.7, 0.3]])  # gold 2 ranked 2nd
    m = retrieval_metrics(sim, [{0}, {1}, {2}])
    assert m["hit@1"] == 1 / 3 and m["hit@3"] == 1.0
    assert abs(m["mrr"] - (1 + 1 / 3 + 1 / 2) / 3) < 1e-9 and m["n"] == 3


def test_retrieval_metrics_excludes_self_for_leave_one_out():
    import numpy as np
    from metrics import retrieval_metrics
    sim = np.array([[1.0, 0.2, 0.6], [0.2, 1.0, 0.1], [0.6, 0.1, 1.0]])
    # same-type gold sets; self must not count
    m = retrieval_metrics(sim, [{0, 2}, {1}, {0, 2}], exclude_self=True)
    assert m["n"] == 2 and m["hit@1"] == 1.0  # row 1 has no other gold → skipped
