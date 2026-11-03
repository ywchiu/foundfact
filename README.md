# FoundFact 查證助手

**A scam check that lives in your feed.** FoundFact is a Chrome extension and web app. It flags likely scam
posts as you scroll Facebook and Threads. Click **Why?** and a Meta Muse agent investigates that post live,
searching the web, matching it against known scams and reading the post's images. You get back a short report
in which every claim is tied to its evidence.

Built by [LargitData 大數軟體](https://www.largitdata.com) for the Meta Global AI Developer Hackathon
(Startups track · Build for Your World).

- Live demo: **https://foundfact.infominer.io**
- Demo video (3 min): _TBD_

## The problem

In Taiwan, a large share of fraud starts in the social feed. Typical lures are:

- fake celebrity investment groups, where a famous founder "gives away books" if you add a LINE account;
- "work from home, NT$290/hour, DM me" job posts;
- prize notices that ask for a "small shipping fee".

Fact-checkers such as the Taiwan FactCheck Center and MyGoPen debunk these lures every week. But people meet a
scam in the feed, not on a fact-check site, and the lure usually works before anyone searches.

FoundFact brings the check to the place where people meet the scam, and shows its sources instead of just
returning a verdict.

## How it works

```
 Facebook / Threads feed                             FoundFact backend (FastAPI, one container)
┌──────────────────────────┐   visible posts (batched)  ┌───────────────────────────────────────────┐
│ content script            │ ─────────────────────────▶ │ /screen  — Stage 1 "System 1" (fast)      │
│  site adapters (FB, Thr.) │                            │   provider = local | jev | muse            │
│  Shadow-DOM red banner    │ ◀───────────────────────── │   local: hunch + EmbeddingGemma 2 student  │
└────────────┬─────────────┘   label high / none         │          (confident "no" → no LLM call)    │
             │ click "Why?"                              │          else → Muse as teacher             │
┌────────────▼─────────────┐                            │   jev:   TypeSafe Jev 1.14 (OpenRouter)    │
│ Chrome Side Panel         │   SSE: agent steps         │   muse:  Muse, json_schema, minimal effort │
│  live agent steps          │ ◀───────────────────────── │                                             │
│  sourced report            │ ─────────────────────────▶ │ /verify  — Stage 2 "System 2" (Muse agent) │
└──────────────────────────┘   post text + image URLs   │   1 read images, copy their text (vision)  │
                                                         │   2 extract checkable claims               │
 Web app (/) — paste a post or a                         │   3 match 137 known cases; check links    │
 screenshot, same report                                 │   4 Muse web_search per claim             │
                                                         │   5 judge each claim against evidence     │
                                                         │   6 conclude: risk, scam type, actions    │
                                                         └───────────────────────────────────────────┘
```

- **Known fraud links come first.**
  - Short links (reurl.cc, bit.ly, lihi…) are resolved to their final URL on the server, using HEAD requests
    with a 3 s timeout. Nothing is rendered.
  - The final host is looked up in 115,585 domains that Taiwan's National Police Agency suspended for fraud.
  - A hit is flagged in under 1 ms with no model call, and the banner names the domain.
  - The list comes from data.gov.tw datasets [176455](https://data.gov.tw/dataset/176455) and
    [160055](https://data.gov.tw/dataset/160055) under the Open Government Data License v1, and is rebuilt by
    `data/scripts/build_blocklist.py`.
  - Free-hosting tenants (e.g. `shopeetw88.github.io`) are matched, but platforms such as `github.io` and
    `google.com` never are.
- **Stage 1 runs on every post, so it has to be cheap.** You choose the provider in the extension options:
  - **local** is a [hunch](https://github.com/undrgrnd-labs/hunch) proxy over a Google EmbeddingGemma 2 student.
    Muse taught it, and once it had learned to agree with Muse on the question "does this post show scam
    tactics?", it began answering that question by itself. A confident local "no" (about 64% of everyday
    posts) costs no LLM call. Every other post goes to Muse, which answers it and keeps teaching the student.
  - **jev** is TypeSafe's Jev 1.14 System One model, which returns typed probabilities in about 0.5 s.
  - **muse** asks Muse directly.
- **Stage 2 runs only when a person asks for it.**
  - The Muse agent streams each step to the side panel.
  - Images are read first. Muse copies their visible text, so a screenshot of a text message is checked like
    pasted text, including any URL in it. The post's own image is never counted as evidence for its claims.
  - Every claim in the report must cite evidence the agent actually retrieved. Claims without evidence are
    downgraded to "insufficient", never "refuted".
  - Results are cached for 24 h. A per-IP rate limit and a daily dollar budget protect the public deployment.
- **Scope:** this build looks for scams only. It does not judge political or news content.

### Where Muse is used

| Use | API features |
|---|---|
| Stage-1 screening | Chat Completions with `response_format: json_schema` and `reasoning_effort: minimal` |
| Teacher for the local student | Same schema, called by hunch through `/teacher/v1/answer` (local-only) |
| Reading images and screenshots | Multimodal `image_url` input; transcribes visible text, URLs included |
| Live investigation | Responses API with the `web_search` tool, streamed |
| Building the known-case store | Turning fact-check articles into short claim/verdict cases |

## Results

**Evaluation set:** 30 posts in `data/eval/scam.jsonl`, split by event into **tune** and **test**.

- **Scams**:
  - 12 known cases held out from the case store and from the student's training data.
  - 8 job posts from Threads with scam signals (labelled high risk; not confirmed as scams, see `data/eval/codex_review.md`).
- **Hard negatives** (10):
  - anti-fraud notices from banks and brands;
  - real giveaway winner posts that say "DM us to claim";
  - legitimate part-time jobs with an address.

Stage 1 on the **tune** split (n = 14; thresholds were tuned on this split, so treat these numbers as
indicative):

| provider | accuracy | scam recall | precision | p50 latency | cost / 1k posts |
|---|---|---|---|---|---|
| Muse | 0.93 | 0.89 | 1.00 | 2.6 s | $5.08 |
| local (hunch student → Muse) | 0.93 | 0.89 | 1.00 | 1.8 s† | ~$1.9† |
| Jev 1.14 | 0.79 | 0.89 | 0.80 | 0.53 s | $0.03 |

Stage 1 on the held-out **test** split (n = 16: 11 scams, 5 hard negatives; one run,
[`eval/results/meta.md`](eval/results/meta.md); a second run with bounded search scored Muse 0.75, one post apart):

| provider | accuracy | scam recall | precision | p50 latency | cost / 1k posts |
|---|---|---|---|---|---|
| Muse | 0.81 | 0.82 | 0.90 | 2.7 s | $4.93 |
| local (hunch student → Muse) | 0.88 | 0.82 | 1.00 | 4.7 s* | ~$3.7 |
| Jev 1.14 | 0.69 | 0.73 | 0.80 | 0.56 s | $0.03 |

† 11 of 14 tune posts were replays from the hunch cache, which flatters latency and cost; a run without the cache measured 4.2 s and $2.80 per 1k ([`eval/results/tune.md`](eval/results/tune.md)).

\* On unseen posts, 12 of 16 went to the teacher (Muse), so the local path paid Muse latency plus the proxy hop.
The student answered 4 locally. Its speed advantage shows up on ordinary feed traffic, where most posts are
confident "no"s.

**Stage 2** (Muse agent, 11 test scams; [`eval/results/meta_fastsearch.md`](eval/results/meta_fastsearch.md)):

- Web search runs at low reasoning effort, and the prompt asks for at most 3 searches, no video pages and inline
  citations. The search cap is a prompt instruction, not enforced by code.
- Effect of the bound:

  | | unbounded | bounded |
  |---|---|---|
  | p50 latency | 57 s | **20 s** |
  | cost per post | $0.19 | **$0.03** |
  | claim-verdict accuracy | 73% | 64% |

- Claim-verdict accuracy is the share of claims whose verdict matches gold (11 claims, so one claim is 9
  points).
- 82% of reports say "high risk", with or without the bound.
- When the gold verdict is "insufficient", the agent abstains instead of guessing in 100% of cases.

The hard cases are fake-news-style lures (a "lawsuit" story about a celebrity) and a fake LINE login page that
looks like an ordinary how-to. All three providers missed the fake LINE login page.

**Student preflight:** the preflight ran on 821 public posts labelled by Muse (US$3.24 in total). The
`is_scam_like` question graduates one-sided at layer 12 of EmbeddingGemma 2 (16 ms):

- About 64% of posts get a local "no".
- 4 of 102 Muse "yes" answers are missed.

The other two questions (whether the post makes a checkable claim, and how much pressure it applies) did not
graduate and stay with Muse. Details: [`docs/notes/hunch-preflight.md`](docs/notes/hunch-preflight.md).

## Built during the hackathon vs. pre-existing

**Built during the hackathon** (Nov 2–4, 2026, inside the Oct 27 – Nov 4 building period; everything in this repository):

- The two-stage design.
- The backend:
  - the Muse client and the verification agent;
  - stage-1 providers and the Jev/OpenRouter integration;
  - rate, budget and cache guards.
- The Chrome extension (MV3) with its Facebook and Threads adapters, Shadow-DOM banners and Side Panel.
- The known-fraud-link check: short-link resolution plus the police fraud-domain list.
- The web app (text or screenshot input, English and Traditional Chinese) and the shared report renderer.
- The 137-case known-scam store and the Muse teacher integration for hunch.
- The preflight labelling, the evaluation set and harness, and the deployment files.

**Pre-existing, used as tools or data sources:**

- **InfoMiner** (LargitData's social-listening platform): used only to fetch public fan-page and Threads posts
  for labelling and evaluation, and to collect fact-check articles. No InfoMiner code is in this repo.
- **Third-party open source and models**:
  - [hunch](https://github.com/undrgrnd-labs/hunch) and eg2cpu (MIT/Apache-2.0);
  - Google EmbeddingGemma 2 (Apache-2.0);
  - TypeSafe Jev, reached via OpenRouter.
- **`ywchiu/gemma-embed-peft`**: LargitData's earlier embedding research. It is **not** used in this demo.

## Running it

You need Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 20+, and Chrome.

```bash
cp .env.example .env            # MUSE_API=...  (OPENROUTER_KEY=... optional, for Jev)
cd backend && uv sync && uv run uvicorn app.api:app --port 8000
# open http://127.0.0.1:8000  — web app
```

**Optional: the local stage-1 student.**

```bash
git clone https://github.com/undrgrnd-labs/hunch ~/hunch && cd ~/hunch && uv sync --all-packages
uv run python -m hunch serve --db /path/to/fraud_detection/data/hunch.db \
  --backend http://127.0.0.1:8000/teacher/v1/answer --port 8765 --layer 12
# seed it once with teacher labels:  uv run python data/scripts/seed_hunch.py --exclude-eval
```

**Load the extension:**

1. Run `bash extension/build.sh`.
2. Open `chrome://extensions`, turn on Developer mode, click **Load unpacked**, and choose `extension/`.
3. Open Facebook or Threads.

**Run the tests:**

```bash
(cd backend && uv run pytest -q)   # 106 tests
npm install && npm test            # 32 tests (extension adapters, scanner, renderer)
```

**Deploy:** the live site runs on a small VM behind nginx and Cloudflare, see [`deploy/vm.md`](deploy/vm.md). On that server known-case matching uses Jev (`CASE_MATCHER=jev`) instead of EmbeddingGemma 2. [`deploy/cloudrun.md`](deploy/cloudrun.md) is an untested alternative.

## Privacy and safety

- API keys live only on the server. The extension and web app never see them.
- The extension reads only the visible text, author, links and image URLs of feed posts. It never reads
  messages or account data.
- Nothing is stored beyond a 24-hour result cache. See [`/privacy`](web/privacy.html).
- No political content: the Meta build screens for scams only.

## Repository layout

```
backend/    FastAPI app: screening, Muse agent, guards (app/), tests/
extension/  Chrome MV3 extension: content scripts, side panel, options
web/        public web app + privacy page
shared/     report renderer, i18n, styles shared by web and extension
data/       known-scam cases, eval set, preflight reports, data scripts
eval/       evaluation harness and results
deploy/     VM guide (nginx, systemd), Dockerfile and Cloud Run guide
docs/       design spec, plan, notes, video script, submission checklist
```

## License

MIT © 2026 LargitData. See [LICENSE](LICENSE).
