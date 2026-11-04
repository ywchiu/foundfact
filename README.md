# FoundFact 查證助手

**English** · [繁體中文](README.zh-TW.md)

**A scam check that lives in your feed.** FoundFact is a Chrome extension and web app. It flags likely scam
posts as you scroll Facebook and Threads. Click **Why?** and a Meta Muse agent investigates that post live,
searching the web, matching it against known scams and reading the post's images. You get back a short report
in which every claim is tied to its evidence.

Built by [LargitData 大數軟體](https://www.largitdata.com) for the Meta Global AI Developer Hackathon
(Startups track · Build for Your World).

- Live demo: **https://foundfact.infominer.io**
- Demo video (2:21): **https://youtu.be/v88sLQ7WtPA**

## The problem

Suspicious offers can appear while people scroll social feeds. Examples include:

- fake celebrity investment groups, where a famous founder "gives away books" if you add a LINE account;
- "work from home, NT$290/hour, DM me" job posts;
- prize notices that ask for a "small shipping fee".

Fact-checkers such as the Taiwan FactCheck Center and MyGoPen debunk these lures every week. But people meet a
scam in the feed, not on a fact-check site, and the lure usually works before anyone searches.

FoundFact brings the check to the place where people meet the scam, and shows its sources instead of just
returning a verdict.

## How it works

The **standalone extension (0.2.0)** calls the user's model providers directly. It does not call the FoundFact backend.

1. As a post becomes visible, its links are checked against the bundled police domain list, then Jev screens its text using the user's Jev key. There is no Muse fallback during scrolling.
2. A high-risk result adds a red banner. Clicking **Why?** opens Chrome's native side panel and starts a Muse investigation using the user's Meta key.
3. Muse reads the first supported image if present, extracts claims, reviews locally selected known-case candidates, searches the web, weighs evidence and returns a report. Claims without supporting evidence are marked **insufficient**.
4. Keys stay in trusted extension-local storage. Reports are cached in extension session storage for 24 hours. Optional local hourly caps and provider rate limits apply; the website's per-IP quota does not apply to extension checks.

The **public website** remains server-backed: paste text or upload a screenshot at https://foundfact.infominer.io. Server-side matching uses the known-case store and Taiwan police domain list; its public rate limits and daily budget remain in place. The server can resolve short links; the standalone extension never follows suspect links or resolves short links. Both support English and Traditional Chinese.

Reference data: **137 exposed scam cases** and **115,585 fraud websites from Taiwan police data**, from [dataset 176455](https://data.gov.tw/dataset/176455) and [160055](https://data.gov.tw/dataset/160055), under the Open Government Data License v1. The extension uses local text overlap followed by Muse to select relevant cases; this differs from the website's matcher.

The repository also includes a Muse-taught smaller-model experiment. In our first test it cleared about 64% of examples on its own. It is **not switched on for the public site or the standalone extension**. Evaluation figures below describe the tested server-backed paths, not measured accuracy or latency of the new standalone extension.

See [extension setup, limits and privacy](extension/BYOK.md).

### Where Muse is used

| Use | API features |
|---|---|
| Server-side screening experiment | Chat Completions with `response_format: json_schema` and `reasoning_effort: minimal` |
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
3. Open extension Settings, enter a Jev key (OpenRouter or TypeSafe) and a Meta Muse key, then Save.
4. Reload Facebook or Threads. The extension defaults to English. See [BYOK.md](extension/BYOK.md).

**Run the tests:**

```bash
(cd backend && uv run pytest -q)   # 107 tests
npm install && npm test            # 54 tests (extension, direct-provider guards, renderer)
```

**Deploy:** the live site runs on a small VM behind nginx and Cloudflare, see [`deploy/vm.md`](deploy/vm.md). On that server known-case matching uses Jev (`CASE_MATCHER=jev`) instead of EmbeddingGemma 2. [`deploy/cloudrun.md`](deploy/cloudrun.md) is an untested alternative.

## Privacy and safety

- Website provider keys stay on the server. Standalone extension users supply their own keys, stored locally in trusted extension contexts, not sent to social pages or FoundFact. Local storage is not encryption at rest.
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
