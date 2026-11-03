"""Label posts with the Muse teacher (backend/app/teacher.py) in hunch preflight format.

Writes data/teacher/<question>.jsonl rows {"span": state, "answer": [...], "group": ...}; one teacher
request per question, as the hunch proxy would send it. Stops if spend exceeds --budget USD.

    cd backend && uv run python ../data/scripts/label_teacher.py [--n 300] [--cases 90] [--budget 30]
"""
import argparse
import asyncio
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings  # noqa: E402
from app.muse import MuseClient  # noqa: E402
from app.teacher import QUESTIONS, answer, options  # noqa: E402

OUT = ROOT / "data" / "teacher"


def to_list(q: dict, a: dict) -> list[float]:
    return [a["noul"]] if q["type"] == "noul" else [a["probabilities"][o] for o in options(q)]


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--cases", type=int, default=90)
    ap.add_argument("--budget", type=float, default=30.0)
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--questions", default=",".join(QUESTIONS), help="comma-separated question ids")
    ap.add_argument("--rest", action="store_true", help="label every post not yet labeled, appending")
    a = ap.parse_args()
    posts = [json.loads(x) for x in (ROOT / "data" / "posts.jsonl").read_text().split("\n") if x.strip()]
    rnd = random.Random(7)
    cases = [p for p in posts if p["source"].startswith("case:")]
    real = [p for p in posts if not p["source"].startswith("case:")]
    qs = {k: QUESTIONS[k] for k in a.questions.split(",")}
    if a.rest:
        done_texts = {json.loads(x)["span"]["text"] for k in qs if (OUT / f"{k}.jsonl").exists()
                      for x in (OUT / f"{k}.jsonl").read_text().split("\n") if x.strip()}
        sample = [p for p in posts if p["text"][:4000] not in done_texts]
    else:
        sample = rnd.sample(cases, min(a.cases, len(cases))) + rnd.sample(real, a.n - min(a.cases, len(cases)))
    rnd.shuffle(sample)
    muse = MuseClient(get_settings())
    OUT.mkdir(exist_ok=True)
    files = {k: (OUT / f"{k}.jsonl").open("a" if a.rest else "w") for k in qs}
    sem = asyncio.Semaphore(a.conc)
    done = 0

    async def one(p):
        nonlocal done
        state = {"platform": p["platform"], "author": p["author"], "text": p["text"][:4000],
                 "link_domains": p["link_domains"]}
        async with sem:
            if muse.spent_usd > a.budget:
                return
            outs = await asyncio.gather(*(answer({"state": state, "questions": {k: q}}, muse)
                                          for k, q in qs.items()), return_exceptions=True)
        for (k, q), o in zip(qs.items(), outs):
            if isinstance(o, Exception):
                continue
            files[k].write(json.dumps({"span": state, "answer": to_list(q, o["answers"][k]),
                                       "group": str(p["group"]), "source": p["source"]}, ensure_ascii=False) + "\n")
        done += 1
        if done % 50 == 0:
            print(f"{done} posts, spent ${muse.spent_usd:.2f}", flush=True)

    await asyncio.gather(*(one(p) for p in sample))
    for f in files.values():
        f.close()
    print(f"done {done} posts, spent ${muse.spent_usd:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
