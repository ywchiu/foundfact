# FoundFact eval: tune_jev

Split `tune`, **n = 14** posts (gold scams + hard negatives; see data/eval/scam.jsonl). Held-out known cases are removed from the case store and the hunch seed.

## Stage 1 (screen)

| provider | n | accuracy | flag recall | flag precision | p50 ms | p99 ms | cost / 1k posts | agree w/ muse | answered_by |
|---|---|---|---|---|---|---|---|---|---|
| jev | 14 | 0.79 | 0.89 | 0.80 | 521 | 607 | $0.03 | — | {'jev': 14} |

## hunch student (local provider)

```
{
 "Does this social media post show scam ta": {
  "graduated": true,
  "mode": "one_sided",
  "cv_agreement": 0.9381188118811881,
  "audit": null
 },
 "Does this post state a specific factual ": {
  "graduated": false,
  "mode": null,
  "cv_agreement": 0.7663230240549829,
  "audit": null
 },
 "How much urgency or pressure language do": {
  "graduated": false,
  "mode": null,
  "cv_agreement": 0.6872852233676976,
  "audit": null
 }
}
```
