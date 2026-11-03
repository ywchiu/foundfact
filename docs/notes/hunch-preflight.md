# hunch preflight: can a local EmbeddingGemma 2 student take over stage 1?

Date: 2026-11-02. hunch at `~/project/hunch` (cloned from github.com/undrgrnd-labs/hunch; `uv sync --all-packages`
and `download.py embeddinggemma-2` took ~2 min; its 98 tests pass on this Mac).

## Data

- `data/posts.jsonl` (gitignored, third-party text): 821 posts = 684 public FB fan-page + Threads posts fetched
  from InfoMiner over the last 45 days in five buckets (investment, giveaway, celebrity, deals, everyday life;
  political keywords dropped) + 137 known scam cases from `data/cases.jsonl`.
- Teacher: Muse (`muse-spark-1.3`, `reasoning_effort=minimal`) through `backend/app/teacher.py`, one request per
  question, exactly as the hunch proxy would ask it (`data/scripts/label_teacher.py`).
- Cost: US$1.37 for 300 posts x 3 questions, then US$0.71 for the other 521 posts on `is_scam_like` only.
  Total **US$2.08** (+US$1.16 for the v2 relabel) (budget was US$30).

## Results (`examples/preflight/preflight.py`, the proxy's own graduation rules; reports in `data/teacher/`)

| question | units | teacher answers | best readout | verdict |
|---|---|---|---|---|
| `is_scam_like` (noul) | 300 | 55 yes / 245 no | layer 4, kappa 0.77 | backend only |
| `is_scam_like` (noul), v1 question | 821 | 101 yes / 720 no | layer 4, 6 ms | graduates one-sided: ~73% local, 5 of 101 "yes" missed |
| `is_scam_like` (noul), **v2 question** (adds fake-job tactics) | **821** | 102 yes / 719 no | **layer 12, 16 ms** | **graduates one-sided**: ~64% answered "no" locally, 4 of 102 teacher "yes" missed (`preflight_is_scam_like_v2.txt`) |
| `has_checkable_claim` (noul) | 300 | | layer 12, kappa 0.53 | backend only (needs reasoning) |
| `pressure` (score) | 300 | 175/97/19/9 | layer 12, QWK 0.49 | backend only (rare classes) |

Why v2: on the tune split Muse itself missed Threads fake-job posts (p≈0.2) with the v1 wording, so the question
was broadened and all 821 posts relabelled (US$1.16). The proxy now runs `--layer 12`.

Live proxy check (`hunch serve --layer 12`, seeded with the 821 answers via `/v1/train`,
`data/scripts/seed_hunch.py`): `is_scam_like` reports `graduated: true, mode: one_sided`, CV agreement 0.94.

## What this means for the product

The `local` stage-1 provider is a cascade (`Screener._hunch`):

1. Ask hunch only `is_scam_like`. A confident local "no" (~2 of 3 everyday posts) returns in ~300 ms with no
   Muse call: no banner.
2. Anything else is forwarded by hunch to its teacher (Muse), which also keeps teaching the student; Muse then
   answers `has_checkable_claim` and `pressure` in parallel.

Measured on 6 posts through `/screen` with `provider=local`: first pass 2 local / 4 forwarded (3-5 s each);
second pass all 6 from the student or its store (~300 ms each). Per the spec, if hunch is down, stage 1 falls
back to `FallbackStage1` (rules + case similarity).

Not graduated, by design: `has_checkable_claim` and `pressure` stay with Muse. Splitting `pressure` into
observable yes/no sub-questions (guide rules 2-3) is the obvious next experiment.
