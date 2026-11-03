"""Build data/blocklist.tsv (host<TAB>scam_type) from Taiwan's National Police Agency open data.

Sources (政府資料開放授權條款-第1版, attribution required):
  - 165反詐騙諮詢專線_遭停止解析涉詐網站  https://data.gov.tw/dataset/176455  (domains suspended for fraud)
  - 165反詐騙諮詢專線_假投資(博弈)網站      https://data.gov.tw/dataset/160055  (fake investment / gambling sites)

    python data/scripts/build_blocklist.py
"""
import csv
import io
import sys
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.linkcheck import Blocklist, normalize_host  # noqa: E402

API = "https://opdadm.moi.gov.tw/api/v1/no-auth/resource/api/dataset"
STOPPED = f"{API}/29E8E643-88ED-4952-B21E-BD42A3B7108C/resource/ED6DCC61-A0AC-4DE2-8571-92FDA7E55C48/download"
INVEST = f"{API}/033197D4-70F4-45EB-9FB8-6D83532B999A/resource/A00B1802-6A4A-42B4-B842-B66A2D937DAE/download"
# 網站性質 → our scam_type
TYPE = {"金融保險": "investment", "抽獎博弈": "investment", "電子商務": "shopping", "運輸倉儲": "shopping",
        "釣魚網站": "phishing", "資訊服務": "phishing", "政府機構與國營事業": "impersonation"}


def rows(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=120) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8-sig"))))


def main():
    entries: dict[str, str] = {}
    for r in rows(INVEST):
        if (h := normalize_host(r["網址"])):
            entries[h] = "investment"
    for r in rows(STOPPED):  # newer list wins on category
        if (h := normalize_host(r["網域"])):
            entries[h] = TYPE.get(r["網站性質"].strip(), "other")
    kept = Blocklist(entries).d  # drops allowlisted platforms and public suffixes
    out = ROOT / "data" / "blocklist.tsv"
    with out.open("w", encoding="utf-8") as f:
        f.write(f"# Built {date.today()} from Taiwan National Police Agency open data (data.gov.tw 176455, 160055),\n"
                "# 政府資料開放授權條款-第1版. host<TAB>scam_type\n")
        for h in sorted(kept):
            f.write(f"{h}\t{kept[h]}\n")
    print(f"wrote {out}: {len(kept)} hosts ({len(entries) - len(kept)} dropped by allowlist)",
          dict(Counter(kept.values())))


if __name__ == "__main__":
    main()
