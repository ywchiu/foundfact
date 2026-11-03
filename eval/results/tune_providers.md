# FoundFact eval: tune_providers

Split `tune`, **n = 14** posts (gold scams + hard negatives; see data/eval/scam.jsonl). Held-out known cases are removed from the case store and the hunch seed.

## Stage 1 (screen)

| provider | n | accuracy | flag recall | flag precision | p50 ms | p99 ms | cost / 1k posts | agree w/ muse | answered_by |
|---|---|---|---|---|---|---|---|---|---|
| muse | 14 | 0.93 | 0.89 | 1.00 | 2626 | 4303 | $5.08 | 1.00 | {'muse': 14} |
| local | 14 | 0.93 | 0.89 | 1.00 | 1812 | 2898 | $1.94 | 1.00 | {'cache': 11, 'proxy': 3} |
| jev | 14 | 0.79 | 0.89 | 0.80 | 531 | 742 | $0.00 | 0.86 | {'jev': 14} |

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
