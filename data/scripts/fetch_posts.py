"""Build data/posts.jsonl: real public FB/Threads posts (via InfoMiner) + known scam cases as posts.

Unlabeled; used to train/check the stage-1 student (hunch preflight). Political posts are dropped
(Meta rules). Output rows: {platform, author, text, link_domains, image_urls, source, group}.

    cd backend && uv run python ../data/scripts/fetch_posts.py [--per-bucket 70] [--days 45]
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import get_settings  # noqa: E402

OUT = ROOT / "data" / "posts.jsonl"
BUCKETS = {
    "invest": "(投資 OR 股票 OR 飆股 OR 獲利 OR 虛擬貨幣 OR 老師帶單)",
    "giveaway": "(免費 OR 贈送 OR 抽獎 OR 領取 OR 送完為止)",
    "celebrity": "(代言 OR 名人 OR 推薦 OR 分享 OR 親測)",
    "deal": "(優惠 OR 折扣 OR 限時 OR 特價 OR 清倉)",
    "life": "(美食 OR 旅遊 OR 天氣 OR 貓 OR 狗 OR 咖啡 OR 電影)",
}
POLITICAL = re.compile(r"選舉|立委|總統|政黨|民進黨|國民黨|民眾黨|議員|罷免|候選人|公投|戰爭|共軍|解放軍|兩岸|川普|習近平")
URL = re.compile(r"https?://([^/\s]+)")


def search(c: httpx.Client, q: str) -> list[dict]:
    for _ in range(3):
        try:
            r = c.post("https://api.infominer.io/querystring_search",
                       json={"querystring": q, "sorted": "tm", "page": 1, "size": 100, "withPushs": False})
            return r.json().get("data") or []
        except Exception:
            time.sleep(2)
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-bucket", type=int, default=70)
    ap.add_argument("--days", type=int, default=45)
    a = ap.parse_args()
    s = get_settings()
    now = int(time.time())
    start = now - a.days * 86400
    rows, seen = [], set()
    with httpx.Client(verify=False, timeout=90, headers={"auth-header": s.infominer_key}) as c:
        for src, platform in [("fans", "facebook"), ("threads", "threads")]:
            for name, kw in BUCKETS.items():
                data = search(c, f"source: {src} && {kw} && tm: (>={start} && <={now})")
                random.Random(name + src).shuffle(data)
                kept = 0
                for d in data:
                    text = (d.get("content") or d.get("title") or "").strip()
                    key = text[:120]
                    if len(text) < 15 or key in seen or POLITICAL.search(text):
                        continue
                    seen.add(key)
                    rows.append({"platform": platform, "author": d.get("author") or "", "text": text[:2000],
                                 "link_domains": sorted({h.lower().removeprefix("www.") for h in URL.findall(text)}),
                                 "image_urls": [], "source": f"infominer:{src}:{name}", "group": d.get("author") or d.get("id")})
                    kept += 1
                    if kept >= a.per_bucket:
                        break
                print(f"{src}/{name}: {kept} of {len(data)}", flush=True)
    for line in (ROOT / "data" / "cases.jsonl").read_text().splitlines():
        cs = json.loads(line)
        rows.append({"platform": "facebook", "author": "", "text": cs["claim_text"],
                     "link_domains": sorted({h.lower() for h in URL.findall(cs["claim_text"])}), "image_urls": [],
                     "source": f"case:{cs['scam_type']}", "group": cs["case_id"]})
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"wrote {len(rows)} posts to {OUT}")


if __name__ == "__main__":
    main()
