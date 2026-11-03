# FoundFact demo video: production brief

This brief is for the agent producing the hackathon demo video. It is self-contained: read it fully before
starting. It replaces the older `docs/video-script.md` (removed). The owner is David Chiu (LargitData). Ask David for any
decision this brief does not settle.

## 1. Goal and deadline

- **What:** one demo video, **3:00 or shorter**, for the Meta Global AI Developer Hackathon (Startups track,
  "Build for Your World").
- **Deadline:** the submission closes **Thu 2026-11-05 10:00 Taiwan time** (Wed 21:00 ET). David needs the
  finished MP4 by **2026-11-05 06:00 Taiwan time** to upload it and submit.
- **Why it matters:** the video is one of the main things judges score. Their rubric:
  - Impact (30%): real-world potential, who benefits.
  - Use of Meta AI tooling (25%): creative use of Meta's models, beyond a basic integration.
  - Technical depth (20%): sound, well-crafted engineering.
  - Demo (25%): a working, impressive demo that holds up live, and a video that is good to watch.

## 2. Audience and tone

- Write and cut for a **general audience**, not engineers. Lead with the person and the problem, then show the
  product working. Mention the technology only as what it does for the user.
- No API names, parameters or jargon on screen or in narration: no "json_schema", "Responses API", "SSE",
  "Stage 1/2", "p50", "EmbeddingGemma", "hunch".
- Narration in **English**. Burn in English captions. Where the UI is in Chinese, the captions carry the meaning.
- Calm and factual. No hype words ("revolutionary", "game-changing"), no fear-mongering.

## 3. Hard rules

Breaking any of these can disqualify the entry or cause harm.

1. **Only show what was built during the hackathon** (everything in the repo was). Never show InfoMiner or any
   other LargitData product.
2. **No political, election or war content** anywhere on screen, including the feed around a demo post,
   trending sidebars and browser tabs. Check every frame.
3. **Facebook test account only**, in the Chrome profile David provides. In that account:
   - do not click links inside scam posts, add LINE accounts, message, comment or react;
   - show FoundFact's report, never the scam site.
4. **Privacy:** blur the names and profile pictures of private individuals. Brand pages and well-known scam
   templates can be shown.
5. **Use the live site** `https://foundfact.infominer.io`, not localhost.
6. **Do not publish anything.** Do not upload the video, post on X, push to GitHub, deploy, or change product
   code. Deliver files to David.
7. **Say only what is true.** Use the approved facts in section 5. If you want to claim anything else, ask
   David first.

## 4. The product, in one paragraph

FoundFact (查證助手) puts a scam check where scams appear: the social feed. A Chrome extension marks posts on
Facebook and Threads that look like scams with a short warning banner. Clicking **Why? / 看原因** opens a side
panel where an AI agent powered by Meta's Muse investigates that post live. It reads the post's image, pulls out
the claims that can be checked, compares them with scams fact-checkers have already exposed, checks links
against a list built from Taiwan police data on fraud websites, and searches the web. Every step is shown as it
happens. The report gives a risk level, each claim with what the evidence shows and where it comes from, and
what to do next. A claim with no evidence is marked "insufficient", not true or false. The same agent runs on
the public website, where anyone can paste a post or drop in a screenshot, in English or Traditional Chinese.

## 5. Approved facts and numbers

Use these exactly as worded, or less strongly. Do not round up.

| Topic | What you may say |
|---|---|
| Speed of a full check | "about 20 seconds" (median in our tests; screenshots take a bit longer, about 40–50 s) |
| Speed of the feed warning | "about three seconds" (median in our test) |
| Cost | "an estimated three US cents of Muse usage per full check, in our tests" |
| Police list | "115,585 fraud websites from Taiwan police data" |
| Known-scam library | "137 scams already exposed by fact-checkers" |
| Test results | On 16 posts it had never seen (11 labelled high risk, 5 tricky look-alikes such as anti-fraud notices and real giveaways), the Muse first pass caught 9 of 11 and wrongly flagged 1 of 5. |
| Smaller model | "Muse also teaches a smaller, cheaper model; in our first test it cleared about 64% of examples on its own." Must add that it is **not switched on for the public site yet**. Optional; cut it if time is short. |
| Images | It reads the post's image or a screenshot, including web addresses written in it. Do not claim it reads QR codes or multiple images. |
| Evidence | Each verdict cites what the agent actually found; without evidence it says "insufficient". |
| Languages | English and Traditional Chinese. |
| Built by | LargitData 大數軟體, during the hackathon (Nov 2–4, 2026). |

**Do not say:** that it catches all scams; that it is "proven" or "guaranteed"; that the smaller model runs on
the live site; that it reads QR codes; that it is on the Chrome Web Store (it installs from the repo in
developer mode); that we used Muse Code; anything about how common scams are unless David gives a source.

## 6. Storyboard (target 2:50–3:00)

Word counts assume about 150 words per minute. Timings are targets; keep the total at or under 3:00.

### 0:00–0:20 · The problem (≈45 words)

- **Screen:** a Facebook feed scrolls. It stops on a "famous founder gives away free investing books, add
  LINE" ad. Quick cut to a Threads post: "remote part-time, NT$290/hour, no experience, DM me."
- **Narration:** "Scams don't wait for you to search. They show up in your feed: a famous founder giving away
  investing books, a remote job that pays too well. Fact-checkers expose these lures, but people meet them
  here, while they scroll."

### 0:20–1:05 · Live in the feed (≈110 words)

- **Screen:**
  1. Same feed with the extension on. The post now carries a red banner ("這篇貼文可能是投資詐騙"; caption:
     "This post may be an investment scam").
  2. Click **看原因 / Why?**. The side panel opens. Steps tick through live: reading the image, finding the
     claims, matching known scams, searching the web, weighing the evidence, conclusion.
  3. The report: **High risk**; a claim marked refuted, with a fact-check source under it; next steps including
     Taiwan's 165 anti-fraud hotline.
  4. Press the **EN** button in the side panel. The report switches to English.
  5. Two-second cut: the Threads job post also has a banner.
- **Narration:** "FoundFact is a Chrome extension. As you scroll Facebook or Threads, it marks posts that look
  like scams. Click Why, and an AI agent powered by Meta's Muse investigates the post for you. You watch every
  step: it reads the image, finds the claims that can be checked, compares them with scams fact-checkers have
  already exposed, and searches the web. In about twenty seconds you get a short report. Each claim shows what
  the evidence says and where it comes from, and you get clear next steps. It works in English and Traditional
  Chinese, and on Threads too."

### 1:05–1:45 · A screenshot is enough (≈80 words)

- **Screen:**
  1. Open `https://foundfact.infominer.io` (English by default).
  2. Drag `docs/video/demo-sms-en.png` (a fake USPS delivery text) onto the "Add a screenshot or image" area.
     Leave the text box empty. Click **Verify**.
  3. The first step, reading the image, shows Muse describing the screenshot. The report says **High risk** and
     names the fake web address from inside the image.
  4. Optional 3-second cut: switch to 中文, drop `docs/video/demo-sms-zh.png` (a fake Chunghwa Post text), and
     show its high-risk result.
- **Narration:** "Not everyone installs an extension, and many scams arrive as a text message. On our website you
  can simply drop in a screenshot. Muse reads the picture, including the web address hidden in it, and runs
  the same investigation. Here, a fake parcel notice: high risk, with the fake link called out and the reasons
  spelled out."

### 1:45–2:20 · Why people can trust it (≈85 words)

- **Screen:** simple motion graphics, one idea per card:
  1. "Every verdict shows its source": a report claim with its source link highlighted.
  2. "No evidence → it says so": a claim marked "insufficient".
  3. "115,585 fraud websites from Taiwan police data": a link flagged instantly.
  4. "About 3 US cents per check": supports a free public service.
- **Narration:** "We built FoundFact to be trusted, not just believed. Every verdict links to the evidence the
  agent actually found. When there is no evidence, it says so instead of guessing. In the feed, links are
  checked against more than a hundred thousand fraud websites from Taiwan police data before any AI runs. And a full check
  costs an estimated three cents of Muse usage, which is what lets us offer it free to anyone."

### 2:20–2:45 · Results (≈55 words)

- **Screen:** one clean results card: "On 16 posts it had never seen: caught 9 of 11 high-risk posts, wrongly
  flagged 1 of 5 look-alikes." Small footnote: "Small test set; indicative."
- **Narration:** "We tested it on posts it had never seen, including tricky look-alikes such as real anti-fraud
  notices and genuine giveaways. It caught nine of eleven high-risk posts and wrongly flagged one of five
  look-alikes. It is a small test, and we show it as one."

### 2:45–3:00 · Close (≈30 words)

- **Screen:** end card:
  - "Built during the Meta Global AI Developer Hackathon"
  - `foundfact.infominer.io`
  - `github.com/ywchiu/foundfact`
  - "LargitData 大數軟體 · Powered by Meta Muse"
- **Narration:** "FoundFact brings the check to where scams spread. Built this week with Meta's Muse. Try it at
  foundfact dot infominer dot io. The code is open on GitHub."

## 7. Production notes

- **Recording:** 1920×1080, 30 fps. Increase the browser zoom (about 125%) so the UI text is readable. Hide
  bookmarks, extensions other than FoundFact, and notifications.
- **Chrome profile:** David provides a Chrome profile that is already logged in to the Facebook test account,
  with the extension loaded from `dist/foundfact.zip` (it points at the live site). Do not log in to anything
  yourself.
- **Finding demo posts:** David or the test account's feed supplies the Facebook investment ad and the Threads
  job post. Check that the banner appears before recording. If the feed has no suitable scam post that day, stop
  and ask David; do not fake a feed.
- **Warm the cache:** run each demo input (both feed posts and both screenshots) through the live site once
  before recording. A repeat of identical content replays from a 24-hour cache, so the steps animate in a few
  seconds. Disclose nothing about the cache on screen; it is the real product's behaviour. If you show a cold
  run, speed up the waiting part and show a small "sped up" label.
- **Rate limit:** the public site allows 10 full checks per hour per IP. Plan takes accordingly.
- **Narration voice:** default to a natural English text-to-speech voice. If David wants to record it himself,
  he will say so; then deliver the script and timed captions for him.
- **Music:** optional, quiet, royalty-free, with the licence noted in the delivery notes.
- **Captions:** burned in, English, two lines at most, matched to the narration.
- **Tools:** any method works (screen recording plus editing, or Remotion with TTS). Keep the real product on
  screen for most of the runtime; judges score whether the product actually works.

## 8. Deliverables

Put everything in one folder and tell David where it is:

1. `foundfact-demo.mp4`: H.264, 1080p, 3:00 or shorter, under 500 MB.
2. `foundfact-demo.srt`: the captions as a separate file.
3. `script-final.md`: the narration as recorded, with timestamps.
4. `notes.md`: what was recorded and how, any sped-up segments, music licence, and anything you could not do.

## 9. Final checklist before handing over

- [ ] Length is 3:00 or shorter.
- [ ] Every claim matches section 5. No forbidden claims.
- [ ] No political, election or war content in any frame; private people blurred.
- [ ] No scam site, LINE add, comment or message shown or performed.
- [ ] Live site URL and GitHub URL on the end card are correct and readable.
- [ ] "Built during the hackathon" is stated.
- [ ] Audio levels are even; captions are in sync.
- [ ] Nothing was uploaded or published.

## 10. After delivery (David)

David uploads the MP4 as a **public** YouTube video, checks that it plays in a logged-out browser, and sends the
link back so it can be added to both READMEs and the submission form.
