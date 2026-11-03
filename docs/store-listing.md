# Chrome Web Store listing: FoundFact 查證助手

✋ **Submit only after David confirms:**

- the developer account (LargitData's, US$5 one-time registration);
- the listing name;
- the public backend URL.

Review usually takes 1 to 7 days.

**Package:** `bash extension/build.sh --release https://foundfact.infominer.io` writes `dist/foundfact.zip`. The
release build does three things:

- sets the default backend to the public URL;
- drops the localhost host permissions;
- narrows `*.run.app` down to that one host.

## Listing text

**Name:** FoundFact 查證助手 — 動態牆詐騙查證

**Summary** (≤ 132 characters):

- zh: 滑 Facebook、Threads 時自動標示疑似詐騙貼文，點一下由 AI Agent 即時上網查證，給你附來源的報告。
- en: Flags likely scam posts in your Facebook and Threads feed; one click and an AI agent verifies them with
  sources.

**Category:** Productivity → Tools (alternative: Social & Communication)

**Language:** Chinese (Traditional), with English as a second listing.

**Description (zh):**

> 詐騙不只在電話裡，更多是在你的動態牆上：名人送書加 LINE、「在家兼職時薪 290、私訊我」、中獎要付運費……
>
> 查證助手會在你滑 Facebook 與 Threads 時，自動檢查畫面上的貼文，遇到疑似詐騙就在貼文上方加一條紅色提示。
> 點「看原因」，側邊欄會由 Meta Muse AI Agent 即時查證：
>
> • 抽出貼文中可查證的主張
> • 比對事實查核中心、MyGoPen 等已知詐騙案例
> • 讀取貼文圖片中的文字
> • 上網搜尋證據，逐條判斷「證據支持／證據反駁／證據不足」
> • 給你風險等級、詐騙類型與建議行動（含 165 反詐騙專線）
>
> 每一條結論都附上來源，找不到證據就老實說「證據不足」。
>
> 隱私：只讀取動態牆上公開貼文的文字、作者名稱、貼文中的連結與圖片網址；不讀私訊、不讀帳號資料、不儲存個資。
> 隱私權政策：https://foundfact.infominer.io/privacy
>
> 由大數軟體 LargitData 開發。

**Description (en):**

> Scams don't only arrive by phone. They show up in your feed: celebrities "giving away books" if you add a LINE
> account, "work from home, NT$290/hour, DM me", prizes that need a "small shipping fee"...
>
> FoundFact checks the posts on your screen as you scroll Facebook and Threads, and puts a red banner on likely
> scams. Click "Why?" and a Meta Muse AI agent verifies the post live in the side panel:
>
> • extracts the claims that can be checked
> • matches them against known scams from Taiwan's fact-checkers
> • reads text inside the post's images
> • searches the web and rules on each claim: supported, refuted, or insufficient evidence
> • gives a risk level, a scam type and what to do next
>
> Every conclusion cites its sources. If no evidence is found, it says so.
>
> Privacy: the extension reads only the visible text, author name, links and image URLs of public feed
> posts. It never reads messages or account data, and stores no personal data.

## Screenshots (1280×800, PNG, 5)

1. FB feed with a red banner on an investment-scam post.
2. Side panel mid-investigation, showing the agent steps.
3. Side panel with the final report: claims refuted, source cards.
4. Threads feed with a fake-job post flagged.
5. Options page: stage-1 model choice (Muse / Local / Jev), language, on/off.

Also needed: a 440×280 small promo tile and the 128×128 icon (`extension/icons/128.png`). Blur private
individuals' names and avatars, and show no political content.

## Privacy practices tab

**Single purpose:** Help users spot likely scam posts in their Facebook and Threads feeds and verify them with
sourced evidence.

**Permission justifications:**

| Permission | Why |
|---|---|
| Host `*://*.facebook.com/*`, `*://*.threads.com/*`, `*://*.threads.net/*` | Read the visible feed posts and add the warning banner. These are the only sites the content script runs on. |
| Host `https://foundfact.infominer.io/*` | Send post text to FoundFact's own backend for screening and verification. |
| `sidePanel` | Show the verification report next to the feed without leaving the page. |
| `storage` | Keep the user's settings (on/off, language, stage-1 model) and pass the clicked post to the side panel. |

**Remote code:** No. All JavaScript ships in the package; the backend returns JSON only.

**Data usage disclosures (tick):**

- Website content: yes. Post text and image URLs are sent for analysis.
- Personal communications, location, health, financial info, authentication, web history and user activity:
  none.

**Certify:**

- data is not sold to third parties;
- data is not used for purposes unrelated to the single purpose;
- data is not used for creditworthiness or lending.
