# FoundFact: 3-minute demo video script

The narration is in English. On-screen UI is shown in Traditional Chinese, with English subtitles where the UI
is in Chinese. The total runs about 3:00 at about 150 words per minute.

**Hard rules for recording:**

- Show no political, election or war content anywhere on screen. Before recording:
  - scroll the feed and check it;
  - hide any trending sidebars.
- Use the test FB account only.
  - Do not click links inside scam posts, add LINE accounts, or comment.
  - Show the report, not the scam site.
- Use the public Cloud Run URL. Don't use localhost.
- Blur the real names and avatars of private individuals in the feed. Brand pages and known scam templates are
  fine to show.

---

## 0:00–0:20 · The problem

**Screen:**

1. A Facebook feed scrolls past.
2. A post freezes in view: a "famous founder gives away free investing books, add LINE" ad.
3. Cut to a Threads post: "remote part-time, NT$290/hour, no experience, DM me."

**Voice-over (≈50 words):**

> In Taiwan, many scams don't start with a phone call. They start in your feed: a famous founder offering free
> investing books, a work-from-home job paying twice the going rate. Fact-checkers debunk these every week, but
> people see the scam here, not on a fact-check site.

## 0:20–1:10 · Live in the feed

**Screen:**

1. The extension is on. The same post now has a **red banner**: "這篇貼文可能是投資詐騙". Show the subtitle
   "This post may be an investment scam".
2. Click **看原因 →**. The Chrome Side Panel slides open.
3. The agent steps tick through live:
   - extract claims;
   - match known cases (2 similar cases);
   - read the image;
   - Muse web search;
   - weigh evidence;
   - conclude.
4. The report appears:
   - risk **高風險**, type investment;
   - claim "張忠謀、黃仁勳免費贈書" → **證據反駁** (refuted), with TFC / MyGoPen source cards;
   - the most similar known case, with its similarity score;
   - recommended actions, including the 165 hotline.
5. Press the language toggle. The same report is now in English.
6. Switch to Threads. A fake-job post gets the banner too.

**Voice-over (≈115 words):**

> FoundFact is a Chrome extension. As you scroll Facebook or Threads, it screens each post and puts a red banner
> on likely scams.
>
> Click "Why?" and a Meta Muse agent investigates that post live. First it pulls out the claims that can be
> checked. Then it matches them against known scams, reads the image, and runs Muse web search on each claim.
>
> The report is short and every verdict is tied to its evidence. This "free books from famous founders" offer
> is refuted, and the sources are right there. If the agent can't find evidence, it says "insufficient". It
> never invents a refutation.
>
> The same works on Threads, where the newest wave is fake remote jobs.

## 1:10–1:50 · Muse as teacher: a System 1 that runs on CPU

**Screen:**

1. Open extension options. The stage-1 model selector shows: Muse · Local EmbeddingGemma 2 · Jev.
2. A terminal shows `/screen` responses side by side:
   - `provider=muse`: `answered_by: muse`, about 2,600 ms;
   - `provider=local`: `answered_by: proxy`, about 300 ms end to end.
3. A graphic: Muse labels 821 public posts → the hunch student on EmbeddingGemma 2 → "graduated, one-sided,
   layer 12, 94% agreement".
4. A provider table: Muse / Local / Jev, with accuracy, latency and cost per 1,000 posts.

**Voice-over (≈95 words):**

> Screening every post with a large model is slow and expensive. So Muse also works as a teacher. We had Muse
> label 821 public posts. A small student built on Google's EmbeddingGemma 2 learned to agree with it. When
> the student is confident a post is ordinary, it answers on CPU in milliseconds. That's about two out of three
> posts. Everything else still goes to Muse, which keeps teaching the student.
>
> And before any model runs, links are checked: short links are unwrapped and matched against 115,000 domains
> Taiwan's police have shut down for fraud. A match is flagged in under a millisecond.
>
> Users can also pick TypeSafe's Jev for stage 1 at about three cents per thousand posts. Muse stays the
> investigator in every mode.

## 1:50–2:30 · Web app, images, evidence

**Screen:**

1. Open the public site. Click the example "可疑簡訊" (suspicious SMS). The report streams in.
2. Paste a screenshot-based post. The image step shows Muse reading the text inside the image.
3. Hover over an evidence card to show the title, date and snippet. Click it to open the fact-check article
   (the fact-check page, not the scam site).
4. Show the privacy page and the rate-limit message.

**Voice-over (≈90 words):**

> For people who don't use the extension, the same agent runs on the web. Paste a post, a text message or a
> link. Muse is multimodal, so a scam hidden in an image gets read too.
>
> Every card is real evidence the agent retrieved: a fact-check article, a known case, or a search result. Keys
> never leave our server. We don't store posts. And a rate limit and a daily budget keep the public site
> sustainable.

## 2:30–3:00 · Impact and links

**Screen:**

1. Results card: test-split stage-1 accuracy, recall and precision for the three providers, and claim-verdict
   accuracy. Use the numbers from `eval/results/meta.md`.
2. Built-during-hackathon summary: Chrome extension, web app, Muse agent, local student.
3. End card:
   - the GitHub repo URL;
   - the live site URL;
   - "LargitData 大數軟體 · Built with Meta Muse".

**Voice-over (≈70 words):**

> On held-out scams and tricky look-alikes, such as anti-fraud notices and real giveaway winners, FoundFact's
> local mode caught 9 of 11 scams with no false alarms. And when the evidence isn't there, the agent says so
> instead of guessing.
>
> We built it this week, on Meta Muse, for the place where scams actually spread. FoundFact: verify before you
> act. The code and the live demo are linked below.

---

## Shot list and assets

- [ ] Clean Chrome profile with the release extension loaded (`dist/foundfact.zip` built against the public URL).
- [ ] Find the FB scam post and the Threads fake-job post in the test account's feed beforehand, and check that
  the banners appear.
- [ ] Pre-warm the `/verify` cache for both demo posts. A cold check takes about 20 s (p50); a cached replay
  still animates the steps in a few seconds.
- [ ] Terminal recording for 1:10–1:50:
  - `curl` `/screen` with `provider=muse` and `provider=local` on the same post;
  - show `answered_by` and `ms`.
- [ ] Screen recording: 1920×1080, 30 fps, system font size up one step.
- [ ] Captions burned in, English.
- [ ] Final length ≤ 3:00. Upload as **public** (YouTube or Vimeo) before submitting.
