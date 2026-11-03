"""Build data/cases.jsonl: known scam cases from TFC + MyGoPen fact-checks (via InfoMiner).

Each fact-check article is turned by Muse into {claim_text (the ORIGINAL suspicious message),
verdict_text, scam_type}. Non-scam and political/election items are dropped (Meta rules).

    cd backend && uv run python ../data/scripts/build_cases.py [--months 18] [--limit 0]
"""
import argparse
import asyncio
import json
import random
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings  # noqa: E402
from app.muse import MuseClient, MuseError  # noqa: E402

OUT = ROOT / "data" / "cases.jsonl"
RAW = ROOT / "data" / "raw_factchecks.jsonl"
TYPES = ["investment", "impersonation", "phishing", "shopping", "romance", "other"]

SCHEMA = {
    "type": "object",
    "properties": {
        "is_scam_case": {"type": "boolean"},
        "is_political": {"type": "boolean"},
        "scam_type": {"type": "string", "enum": TYPES},
        "claim_text": {"type": "string"},
        "verdict_text": {"type": "string"},
    },
    "required": ["is_scam_case", "is_political", "scam_type", "claim_text", "verdict_text"],
    "additionalProperties": False,
}
SYSTEM = ("You convert Taiwanese fact-check articles into scam case records. Reply with JSON only.")
PROMPT = """Fact-check article (title + body):
<article>
{title}
{body}
</article>

- is_scam_case: true only if the article debunks a SCAM or FRAUD attempt aimed at the public (fake investment groups, impersonating celebrities/government/companies, phishing links/SMS, fake shopping, romance scams, fake giveaways). Health myths, general rumors, and news misreadings are false.
- is_political: true if it involves politicians, parties, elections, government policy disputes, cross-strait or war topics.
- scam_type: best category.
- claim_text: the ORIGINAL suspicious message/post as victims saw it, in Traditional Chinese, 1-3 sentences, reconstructed from quotes in the article. NOT the fact-checker's explanation. Empty string if it cannot be recovered.
- verdict_text: one sentence: what the fact-checkers concluded and why."""


def fetch_articles(key: str, months: int) -> list[dict]:
    now = int(time.time())
    start = now - months * 30 * 86400
    out = []
    with httpx.Client(verify=False, timeout=90, headers={"auth-header": key}) as c:
        for src in ["tfc", "mygopen"]:
            page = 1
            while True:
                q = f"source: {src} && tm: (>={start} && <={now})"
                for attempt in range(3):
                    try:
                        r = c.post("https://api.infominer.io/querystring_search", json={
                            "querystring": q, "sorted": "tm", "page": page, "size": 100, "withPushs": False})
                        data = r.json().get("data") or []
                        break
                    except Exception:
                        time.sleep(2)
                else:
                    data = []
                out += [{"id": d.get("id"), "source": src, "title": d.get("title", ""),
                         "content": d.get("content", ""), "url": d.get("url"),
                         "date": (d.get("datetime") or "")[:10]} for d in data]
                print(f"{src} page {page}: {len(data)}", flush=True)
                if len(data) < 100:
                    break
                page += 1
    return out


async def convert(muse: MuseClient, arts: list[dict], conc: int = 8) -> list[dict]:
    sem = asyncio.Semaphore(conc)
    rows: list[dict] = []

    async def one(i, a):
        async with sem:
            try:
                r = await muse.chat_json(SYSTEM, PROMPT.format(title=a["title"], body=a["content"][:3500]),
                                         SCHEMA, "case")
            except MuseError as e:
                print("skip", a["url"], e)
                return
            if r["is_scam_case"] and not r["is_political"] and r["claim_text"].strip():
                rows.append({"case_id": f"{a['source']}-{a['id']}", "scam_type": r["scam_type"],
                             "claim_text": r["claim_text"].strip(), "verdict_text": r["verdict_text"].strip(),
                             "source": a["source"], "url": a["url"], "date": a["date"], "title": a["title"]})
            if i % 50 == 0:
                print(f"{i}/{len(arts)} kept={len(rows)} spent=${muse.spent_usd:.2f}", flush=True)

    await asyncio.gather(*(one(i, a) for i, a in enumerate(arts)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=18)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    if RAW.exists() and not args.refetch:
        arts = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]
    else:
        arts = fetch_articles(s.infominer_key, args.months)
        RAW.write_text("\n".join(json.dumps(a, ensure_ascii=False) for a in arts))
    seen, uniq = set(), []
    for a in arts:
        if a["url"] not in seen and a["content"]:
            seen.add(a["url"])
            uniq.append(a)
    if args.limit:
        uniq = uniq[: args.limit]
    print(f"articles: {len(uniq)}")
    muse = MuseClient(s)
    rows = asyncio.run(convert(muse, uniq))
    rows.sort(key=lambda r: r["date"], reverse=True)
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    print(f"wrote {len(rows)} cases to {OUT} (spent ${muse.spent_usd:.2f})")
    for r in random.sample(rows, min(10, len(rows))):
        print(f"- [{r['scam_type']}] CLAIM: {r['claim_text'][:80]} | VERDICT: {r['verdict_text'][:60]}")


if __name__ == "__main__":
    main()
