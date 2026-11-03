# FoundFact eval: meta_fastsearch

Split `test`, **n = 16** posts (gold scams + hard negatives; see data/eval/scam.jsonl). Held-out known cases are removed from the case store and the hunch seed.

## Stage 1 (screen)

| provider | n | accuracy | flag recall | flag precision | p50 ms | p99 ms | cost / 1k posts | agree w/ muse | answered_by |
|---|---|---|---|---|---|---|---|---|---|
| muse | 16 | 0.75 | 0.73 | 0.89 | 2948 | 4998 | $4.93 | 1.00 | {'muse': 16} |

## Stage 2 (Muse agent, gold scams only)

- posts: 11, gold claims: 11
- claim-verdict accuracy: 0.64
- abstain rate (model says insufficient when gold is insufficient): 1.00
- report risk = high: 0.82
- end-to-end latency p50 / p99: 20.2 s / 27.3 s
- cost: $0.37 total, $0.03 per verified post

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
