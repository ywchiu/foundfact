# Embedding comparison: EmbeddingGemma 2 vs gemma-embed-peft

Corpus: 137 fact-checked scam cases (`data/cases.jsonl`; types {'impersonation': 61, 'investment': 7, 'shopping': 10, 'phishing': 49, 'other': 10}). Machine: arm64 Darwin, PyTorch MPS/CPU, fp32.

- **A. headline → case**: query = fact-check headline, corpus = 137 case texts; gold = the same case.
- **B. same scam type (leave-one-out)**: query = a case text, corpus = the other 136; gold = same `scam_type`. Random-neighbour baseline hit@1 = 0.33.
- **mean pairwise cos**: average cosine between corpus vectors; near 1.0 means the vectors have collapsed.

| model | dim | A hit@1 | A hit@3 | A MRR | B hit@1 | B hit@3 | texts/s | mean pairwise cos |
|---|---|---|---|---|---|---|---|---|
| google/embeddinggemma-2 | 768 | 0.83 | 0.94 | 0.89 | 0.69 | 0.84 | 300.4 | 0.689 |
| ywchiu/gemma-embed-peft (first-token, as on card) | 1152 | 0.01 | 0.02 | 0.04 | 0.40 | 0.50 | 18.4 | 0.874 |
| ywchiu/gemma-embed-peft (mean pooling, diagnostic) | 1152 | 0.54 | 0.66 | 0.63 | 0.60 | 0.82 | 20.8 | 0.813 |
