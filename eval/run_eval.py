"""Evaluate FoundFact on data/eval/scam.jsonl.

    cd backend && uv run python ../eval/run_eval.py --split tune --sweep --no-verify
    cd backend && uv run python ../eval/run_eval.py --split test [--providers local,jev,muse] [--no-verify]

Stage 1 per provider: label accuracy, flag precision/recall, p50/p99 latency, answered_by mix, cost.
Stage 2 (Muse agent, gold-scam rows): claim-verdict accuracy, abstain rate on gold "insufficient", risk
accuracy, end-to-end latency, cost. Held-out known cases are removed from the case store for the whole run.
Writes eval/results/<name>.json and .md.
"""
import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "eval"))
from app.agent import Verifier  # noqa: E402
from app.linkcheck import Blocklist  # noqa: E402
from app.cases import CaseStore, GemmaEncoder  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models import Post  # noqa: E402
from app.muse import MuseClient  # noqa: E402
from app.screen import Screener  # noqa: E402
from metrics import label_metrics, pct, sweep, verdict_metrics  # noqa: E402

RES = ROOT / "eval" / "results"


def load(split: str) -> tuple[list[dict], set[str]]:
    rows = [json.loads(x) for x in (ROOT / "data" / "eval" / "scam.jsonl").read_text().split("\n") if x.strip()]
    held = {r["event_id"] for r in rows if r["kind"].startswith("known_case")}
    return [r for r in rows if split == "all" or r["split"] == split], held


def store_without(held: set[str]) -> CaseStore:
    raw = RES / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    src = ROOT / "data" / "cases.jsonl"
    keep = [x for x in src.read_text().split("\n") if x.strip() and json.loads(x)["case_id"] not in held]
    path = raw / "cases_eval.jsonl"
    if not path.exists() or path.read_text() != "\n".join(keep) + "\n":
        path.write_text("\n".join(keep) + "\n")
    return CaseStore(path, GemmaEncoder())


async def stage1(screener: Screener, muse, rows, provider):
    out, spent0 = [], muse.spent_usd + screener.jev_spent_usd
    for r in rows:
        res = await screener.screen_post(Post(**r["post"]), provider)
        out.append({"id": r["id"], "gold": r["gold_label"], "label": res.label, "p_scam": res.p_scam,
                    "p_claim": res.p_claim, "pressure": res.pressure, "latency_ms": res.latency_ms,
                    "answered_by": res.answered_by})
    lat = [o["latency_ms"] for o in out]
    spent = muse.spent_usd + screener.jev_spent_usd - spent0
    m = label_metrics([o["gold"] for o in out], [o["label"] for o in out])
    return out, m | {"p50_ms": pct(lat, 50), "p99_ms": pct(lat, 99),
                     "answered_by": dict(Counter(o["answered_by"] for o in out)),
                     "cost_usd": round(spent, 5),
                     "cost_per_1k_posts_usd": round(spent / max(len(out), 1) * 1000, 3)}


async def stage2(verifier: Verifier, store: CaseStore, muse, rows, s1):
    pressure = {o["id"]: o["pressure"] for o in s1}
    gold_v, pred_v, risks, lat, details = [], [], [], [], []
    spent0 = muse.spent_usd
    for r in [r for r in rows if r["gold_claims"]]:
        t0 = time.perf_counter()
        rep = None
        async for ev, data in verifier.stream(Post(**r["post"]), "zh", pressure.get(r["id"])):
            if ev == "report":
                rep = data
        lat.append((time.perf_counter() - t0) * 1000)
        risks.append(rep["risk"] if rep else "error")
        claims = rep["claims"] if rep else []
        verdict = {v["claim_id"]: v["verdict"] for v in (rep["verdicts"] if rep else [])}
        for g in r["gold_claims"]:
            if claims:
                sims = store.embed([c["text"] for c in claims]) @ store.embed([g["text"]], query=True)[0]
                best = claims[int(np.argmax(sims))]
                p = verdict.get(best["id"], "insufficient")
            else:
                p = "insufficient"
            gold_v.append(g["verdict"])
            pred_v.append(p)
        details.append({"id": r["id"], "risk": risks[-1], "claims": [(c["text"], verdict.get(c["id"])) for c in claims],
                        "n_evidence": len(rep["evidence"]) if rep else 0, "latency_ms": round(lat[-1])})
    vm = verdict_metrics(gold_v, pred_v)
    return details, vm | {"risk_high_rate": sum(x == "high" for x in risks) / len(risks) if risks else None,
                          "e2e_p50_ms": pct(lat, 50), "e2e_p99_ms": pct(lat, 99),
                          "cost_usd": round(muse.spent_usd - spent0, 4), "posts": len(risks)}


def hunch_status(url: str) -> dict:
    try:
        qs = httpx.get(f"{url}/v1/questions", timeout=3).json()
    except Exception as e:
        return {"error": type(e).__name__}
    items = qs.get("questions", qs) if isinstance(qs, dict) else qs
    out = {}
    for q in items if isinstance(items, list) else []:
        rep = q.get("report") or {}
        name = (q.get("spec") or {}).get("instructions", "")[:40]
        out[name] = {"graduated": q.get("graduated"), "mode": q.get("mode"),
                     "cv_agreement": rep.get("cv_agreement"), "audit": q.get("audit")}
    return out


def fmt(x, nd=2):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def markdown(name, split, n, s1, s2, hunch, agree, sw):
    L = [f"# FoundFact eval: {name}", "", f"Split `{split}`, **n = {n}** posts (gold scams + hard negatives; "
         "see data/eval/scam.jsonl). Held-out known cases are removed from the case store and the hunch seed.", "",
         "## Stage 1 (screen)", "",
         "| provider | n | accuracy | flag recall | flag precision | p50 ms | p99 ms | cost / 1k posts | agree w/ muse | answered_by |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for p, m in s1.items():
        L.append(f"| {p} | {m['n']} | {fmt(m['accuracy'])} | {fmt(m['flag_recall'])} | {fmt(m['flag_precision'])} | "
                 f"{fmt(m['p50_ms'], 0)} | {fmt(m['p99_ms'], 0)} | ${fmt(m['cost_per_1k_posts_usd'])} | "
                 f"{fmt(agree.get(p))} | {m['answered_by']} |")
    if sw:
        L += ["", f"Threshold sweep (muse): hi={sw['hi']}, mid={sw['mid']}, claim={sw['claim']} → accuracy {fmt(sw['accuracy'])}"]
    if s2:
        L += ["", "## Stage 2 (Muse agent, gold scams only)", "",
              f"- posts: {s2['posts']}, gold claims: {s2['n']}",
              f"- claim-verdict accuracy: {fmt(s2['accuracy'])}",
              f"- abstain rate (model says insufficient when gold is insufficient): {fmt(s2['abstain_rate'])}",
              f"- report risk = high: {fmt(s2['risk_high_rate'])}",
              f"- end-to-end latency p50 / p99: {fmt(s2['e2e_p50_ms'] / 1000 if s2['e2e_p50_ms'] else None, 1)} s / "
              f"{fmt(s2['e2e_p99_ms'] / 1000 if s2['e2e_p99_ms'] else None, 1)} s",
              f"- cost: ${fmt(s2['cost_usd'])} total, ${fmt(s2['cost_usd'] / max(s2['posts'], 1))} per verified post"]
    L += ["", "## hunch student (local provider)", "", "```", json.dumps(hunch, ensure_ascii=False, indent=1), "```"]
    return "\n".join(L) + "\n"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["tune", "test", "all"])
    ap.add_argument("--providers", default="muse")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    s = get_settings()
    rows, held = load(a.split)
    store = store_without(held)
    muse = MuseClient(s)
    screener = Screener(s, store, muse)
    s1, s1_rows = {}, {}
    for p in a.providers.split(","):
        s1_rows[p], s1[p] = await stage1(screener, muse, rows, p)
        print(p, json.dumps(s1[p], ensure_ascii=False), flush=True)
    if "local" in s1 and "muse" in s1:
        # forwarded is_scam_like calls are paid by the backend's teacher endpoint, not this process:
        # estimate each as one Muse question (a Muse screen asks three)
        fwd = s1["local"]["answered_by"].get("backend", 0)
        per_q = s1["muse"]["cost_usd"] / max(s1["muse"]["n"], 1) / 3
        s1["local"]["cost_usd"] = round(s1["local"]["cost_usd"] + fwd * per_q, 5)
        s1["local"]["cost_per_1k_posts_usd"] = round(s1["local"]["cost_usd"] / max(s1["local"]["n"], 1) * 1000, 3)
        s1["local"]["cost_note"] = f"includes {fwd} forwarded teacher calls estimated at ${per_q:.5f} each"
    base = s1_rows.get("muse")
    agree = {p: (sum(x["label"] == y["label"] for x, y in zip(rs, base)) / len(rs)) for p, rs in s1_rows.items()} if base else {}
    sw = sweep([{"gold": o["gold"], "p_scam": o["p_scam"], "p_claim": o["p_claim"]} for o in base]) if a.sweep and base else None
    if sw:
        print("sweep", sw)
    s2_detail, s2 = None, None
    if not a.no_verify:
        verifier = Verifier(muse, store, Blocklist.load(s.data_dir / "blocklist.tsv"))
        s2_detail, s2 = await stage2(verifier, store, muse, rows, s1_rows[a.providers.split(",")[0]])
        print("stage2", json.dumps(s2), flush=True)
    name = a.name or ("meta" if a.split == "test" else a.split)
    RES.mkdir(parents=True, exist_ok=True)
    hs = hunch_status(s.hunch_url)
    (RES / f"{name}.json").write_text(json.dumps({"split": a.split, "n": len(rows), "stage1": s1, "stage1_rows": s1_rows,
                                                  "agree_with_muse": agree, "sweep": sw, "stage2": s2,
                                                  "stage2_rows": s2_detail, "hunch": hs}, ensure_ascii=False, indent=1))
    (RES / f"{name}.md").write_text(markdown(name, a.split, len(rows), s1, s2, hs, agree, sw))
    print(f"wrote eval/results/{name}.md  (total Muse spend ${muse.spent_usd:.2f})")


if __name__ == "__main__":
    asyncio.run(main())
