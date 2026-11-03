"""Seed a running hunch proxy with the Muse teacher's answers (data/teacher/<question>.jsonl) via /v1/train.

    hunch serve --db data/hunch.db --backend http://127.0.0.1:8000/teacher/v1/answer --port 8765 --layer 4
    cd backend && uv run python ../data/scripts/seed_hunch.py [--url http://127.0.0.1:8765]
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.teacher import QUESTIONS, options  # noqa: E402


def answer_obj(q, a):
    if q["type"] == "noul":
        return {"type": "noul", "noul": a[0]}
    return {"type": q["type"], "probabilities": dict(zip(options(q), a))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8765")
    ap.add_argument("--exclude-eval", action="store_true", help="skip states whose text is in data/eval/scam.jsonl")
    a = ap.parse_args()
    ev = ROOT / "data" / "eval" / "scam.jsonl"
    skip = {json.loads(x)["post"]["text"] for x in ev.read_text().split("\n") if x.strip()} if a.exclude_eval else set()
    for qid, q in QUESTIONS.items():
        f = ROOT / "data" / "teacher" / f"{qid}.jsonl"
        if not f.exists():
            continue
        rows = [json.loads(x) for x in f.read_text().split("\n") if x.strip()]
        rows = [r for r in rows if r["span"]["text"] not in skip]
        cases = [{"state": r["span"], "answer": answer_obj(q, r["answer"]), "kind": "sampled"} for r in rows]
        r = httpx.post(f"{a.url}/v1/train", json={"question": q, "cases": cases}, timeout=600)
        print(qid, len(cases), r.status_code, json.dumps(r.json(), ensure_ascii=False)[:600])


if __name__ == "__main__":
    main()
