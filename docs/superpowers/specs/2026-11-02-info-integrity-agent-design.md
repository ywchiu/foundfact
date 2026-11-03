# AI Information Integrity Agent — 設計文件

日期：2026-11-02 · 作者：David Chiu（大數軟體 LargitData）· 狀態：已確認（2026-11-02）

## 1. 目的與動機

本週有兩項交付共用同一套系統，不分開開發：

| 交付 | 截止 | 這套系統在其中的角色 |
|---|---|---|
| Meta Global AI Developer Hackathon | **2026-11-05（四）10:00 台灣時間**（11/4 21:00 EST） | 主作品（Startup 組）：公開 repo、公開網頁版、3 分鐘英文影片。**只做防詐騙**，不放政治和選舉內容。 |
| 115 年數發部算力平台績優業者選拔 | **2026-11-08（日）23:59** | 中文成果簡報裡的「應用案例」，加上實測數據 |

產品定位：這不是假新聞分類器，而是一個**會自己調查網路訊息的 AI Agent**。使用者照常滑 Facebook 或 Threads，系統在背景把有問題的貼文標出來。點下去之後，Agent 會自己找證據，產出可以追溯來源的報告。

核心原則（來自 David）：
- 判斷的是**具體、可查證的事實主張**。選舉類訊息不對候選人、政黨或立場打分數。
- **「AI 生成」不等於「不實」**。如果有偵測結果，要分開顯示。
- 證據不足時要明確說「證據不足」，不能硬下結論。

## 2. 使用者體驗

### 2.1 Chrome Extension（主要入口）
1. 使用者在 facebook.com 或 threads.com 滑動態牆，extension 在背景讀取捲進畫面的每一篇貼文：內文、連結網域、作者或粉專名稱、是否為贊助貼文。
2. **第一段（System 1）快篩**，每篇數十毫秒。結果分三種：
   - **高風險** → 貼文上方加紅色橫條和左側紅線，文字是「⚠ 這篇貼文可能是〈類型〉詐騙　by 查證助手 · 看原因 →」
   - **待查證**（不確定，或含可查證主張）→ 比較弱的琥珀色標示
   - **正常** → 完全不動
3. 點「看原因」→ 開啟 **Chrome Side Panel**。第二段（Muse Agent）深查時，查證步驟要**一步一步即時顯示**，這是 Meta demo 的重點畫面。
4. 報告由上往下：
   1. 結論
   2. 逐條主張，每條標上四類之一：證據支持、證據反駁、證據不足、需人工複核，並附可點的引用來源
   3. 第一段比對到最像的已知案例，和相似度
   4. Agent 查證過程
   5. 建議行動，例如「不要加入，打 165 檢舉」
5. 紅條上一定要寫明「by 查證助手」，避免被誤認為 Facebook 官方的標示。

參考：草圖在 `.superpowers/brainstorm/` 下的 `feed-marking.html`（選 B）和 `deep-report.html`（選 A）。

### 2.2 網頁版（第二入口）
參考「查詐一下」（anti-scam-jev.philqq100.chatgpt.site）：貼上文字或網址 → 一樣即時顯示查證步驟 → 產出和 Side Panel 相同的報告。附範例按鈕和個資提醒。給評審和沒裝 extension 的人用。

### 2.3 語言
介面可以切換中文和英文，報告語言跟著介面。案例原文保留中文，英文模式下附翻譯摘要。

## 3. 架構

```
Chrome Extension（content script + side panel）  網頁版
          │                                        │
          └──────────────► 後端 API（本機 Python）◄─┘
                              │
              ┌───────────────┴────────────────┐
     第一段 System 1                     第二段 System 2
     hunch proxy                         Muse Verification Agent
     EmbeddingGemma 2 + 每題 student      muse-spark-1.3（Standard）
     ＋ kNN 已知案例比對                  web_search、url_citation
              │  不確定 / 新穎 / 畢業前          │
              └──────────► Muse teacher ◄──────┘
```

### 3.1 第一段：System 1 判斷模型（hunch）
- 使用 [undrgrnd-labs/hunch](https://github.com/undrgrnd-labs/hunch)（Apache-2.0 / MIT）。底層是 EmbeddingGemma 2，以 eg2cpu 在 CPU 上執行。官方數據：Apple M5 Pro 上 p50 約 22 ms。
- **Teacher = Muse。** 我們自己寫一個 teacher 端點，照 hunch 的 `examples/teacher_openrouter.py` 改：輸入 `{"state","questions"}`，回傳 `{"answers"}`，以 structured output 要求 Muse 回傳機率。
- **Student**：每題一個，由 hunch 自動訓練。通過交叉驗證後「畢業」接手回答，畢業後抽 10% 送 teacher 稽核。遇到新穎的輸入會退回 teacher。
- **State**（每篇貼文）：`{platform, author, text, link_domains, is_sponsored?}`。`is_sponsored` 只盡力抓取：Facebook 故意混淆「贊助」字樣，不能當可靠特徵。
- **第一段判斷的是「從貼文本身看得出來的可疑話術」，不判斷真偽。** 真偽交給第二段，因為 hunch 的 student 只能學到從輸入文字看得出來的事。（審查後的決定）
- **題目**：每題**分開送出請求**。hunch 只要同一請求裡有一題沒畢業，整包都會送給 teacher。（審查後的決定）
  - `is_scam_like`（noul，one-sided 模式）：**主路由題**。這篇是否呈現詐騙手法（保證獲利、冒名、導流私訊或 LINE、可疑連結、限時施壓）？
  - `has_checkable_claim`（noul）：是否含可以查證的具體事實主張，用來決定是否標「待查證」
  - `pressure`（score，0–3）：施壓話術的程度，顯示在報告裡，不參與路由
  - **詐騙類型**不另開題目：取 kNN 最像案例的類型，深查時再由 Muse 確認。原本 7 選 1 的 choice 中，稀有類別不可能畢業。
- **kNN 已知案例比對**：用 EmbeddingGemma 2 的向量，比對已知案例資料庫，取最像的前 3 筆，在報告中顯示為「最像案例」。
- **決策規則**（寫在程式裡，門檻在 tune 集上調整）：
  - `is_scam_like` ≥ 高門檻 → 高風險紅條
  - `is_scam_like` 落在中間，或 `has_checkable_claim` 偏高 → 待查證標示
  - 其他 → 不標示
  - **深查只在使用者點擊後執行**，不自動深查，避免把整個動態牆的內容送到 Meta。（審查後的決定）
- **保底方案**：hunch 限半天驗證可行性。如果編譯或畢業不成功，第一段改用「EmbeddingGemma 2 kNN 相似度＋規則」，例如命中保證獲利、LINE 導流、可疑網域等，題目介面維持不變。

### 3.2 第二段：Muse Verification Agent
- `https://api.meta.ai/v1`，Responses API，`muse-spark-1.3`（Standard 版，資料不會拿去訓練模型）。金鑰放在 `.env` 的 `MUSE_API`，只存在後端，不放進 extension。
- 由後端自己編排流程，每一步都是一個真實事件，以 SSE 推給 Side Panel。不能依賴模型自動吐出步驟。
  1. **抽出主張**：結構化輸出，每篇最多 3 條
  2. **查本地資料**：已知案例 kNN，加上 165 和數發部的高風險網域、粉專名單。本地優先，因為 `web_search` 對繁中和台灣來源的覆蓋度未知。
  3. **網路搜尋**：每條主張呼叫一次 Responses API，帶 `web_search`，加上 `include: ["web_search_call.results"]`。
  4. **整理判斷**：另外一次呼叫，用 `text.format` 結構化輸出。文件沒有保證 structured output 能和 `web_search` 在同一個請求裡使用，所以拆成兩次。輸入是前面蒐集到的證據片段，輸出四類判斷，每條判斷都要指向證據 ID。
  5. **結論與建議行動**
- 證據統一存成 `{id, source_type: web|local_case|blocklist, url, title, snippet, date}`。本地證據有自己的來源 ID，不用 `url_citation`。
- **沒有指向任何證據 ID 的判斷，一律降成「證據不足」。** 有引用也不代表來源支持結論，所以報告要顯示證據片段，讓人自己看。
- `web_search` 不保證每次都會真的去搜尋。如果沒搜到，就照實顯示「未找到網路來源」。

### 3.3 資料
- **已知案例資料庫**（200–500 筆）：每筆都要把「原始可疑訊息」和「查核結論、日期」分開存。官方宣導文是在提醒民眾，本身不是詐騙貼文，不能直接當正例。
  - 現成爬蟲：`/Users/david/project/distributed_crawler/news/` 下的 `mygopen.py`、`tfc.py`、`news_1658tw.py`
  - Cofacts：HF 資料集 `Cofacts/line-msg-fact-check-tw`，需登入並同意條款
  - 中選會：沒有現成爬蟲，手動整理 10–20 筆
- **Teacher 標註語料**（1,000–2,000 篇）：InfoMiner 的 FB 和 Threads 貼文，加上已知案例中的原始訊息。用 `infominer-fetch` skill 抓取。**標籤一律由 Muse teacher 打**，不能把「一般貼文」直接當負例。只送公開貼文的文字，不送圖片。
  - 先跑 150–300 篇做 preflight，確認哪些題目學得起來，再決定要不要擴大
  - Teacher 要做去重、限制併發、設預算上限（標註階段上限 $30）
- **評測集**：防詐 20 筆、選舉事實主張 10 筆，**再加難負例 10 筆**，例如反詐宣導、正常促銷、正確的選舉資訊。
  - 依事件切成 tune 和 test 兩組，同一則謠言的不同改寫不能跨組
  - 門檻只在 tune 集上調，對外報告的數字只用 test 集
  - 這組資料只算冒煙測試，簡報要寫明樣本數

## 4. 指標（兩項交付共用）
- 第一段：student 與 Muse 的一致率、畢業題數、p50/p99 延遲、吞吐量，以及成本對比（student 對上每篇都跑 Muse）
- 檢索命中率：EmbeddingGemma 2 對比 `ywchiu/gemma-embed-peft`（114 年算力成果），在已知案例比對上的表現
- 第二段：主張判斷正確率、證據不足時的棄答率、端到端查證延遲
- 這些數字同時用在 Meta 影片和算力簡報

## 5. 目標 / 非目標 / 反目標
**目標**：
- extension 在 FB 和 Threads 標紅條，點開 Side Panel 即時深查
- 網頁版
- 兩段式架構可以運作
- 一套評測數據
- 2–3 分鐘英文 demo 影片

**非目標**：
- 場景 C 的 AI 生成偵測（放在 Roadmap）
- 手機版
- 正式的雲端維運：只部署 demo 用的公開網頁版，不做 SLA 或自動擴展
- 帳號系統

**反目標**（就算功能能跑，也算失敗的情況）：
- 對政治人物或政黨打可信度分數
- 沒有引用就下「不實」結論
- 把 AI 生成直接當成不實
- 紅條被誤認為 Facebook 官方標示
- 把 Muse 金鑰放進 extension

## 6. 限制
- 時程：Meta 版必須在 11/4（三）晚上送出
- Muse 預算：hackathon 的 $150 credits，已申請並套用到 `.env` 中 `MUSE_API` 對應的帳號
- 執行環境：開發和 extension 展示都在 David 的 Mac 上，網頁版另外部署一份公開站
- 執行環境的硬體是 Apple M5 Max、64 GB，有 SME，可以對齊 hunch 的效能數據
- Facebook 和 Threads 的 DOM 會變動。實作上的做法：
  - Threads 已經轉址到 threads.com，所以 manifest 要涵蓋 `*.threads.com` 和 `*.threads.net`
  - 用語意選擇器（`role=article` 等）加上 MutationObserver 抓貼文
  - 標示的 UI 放在 Shadow DOM 裡，避免被網站的 CSS 蓋掉
  - 開 Side Panel 時，`chrome.sidePanel.open()` 必須在使用者點擊的手勢內同步呼叫
  - 對 localhost 的請求一律從 extension 自己的頁面或背景程式發出，不從 content script 發
- 第一段的延遲：22 ms 是 hunch 在單題、student 已畢業時的 p50，不是端到端的承諾。實際數字以量測為準。
- 給 `gemma-embed-peft` 的對比用：base 是 `google/gemma-3-1b-pt` 加 LoRA，取第一個 token 做 pooling，輸出 1152 維向量，推論程式可以照 HF 卡片修正後的版本寫

## 6.1 David 的決定（2026-11-02）
- **Demo 素材**：用測試帳號追蹤已知的詐騙粉專，讓真實的詐騙貼文出現在動態牆上。測試帳號只追蹤和瀏覽，不點貼文裡的連結、不加 LINE、不留言。粉專名單從 165 和數發部的高風險粉專名單挑選，錄影前一天先確認貼文確實會出現。
- **範圍**：設計裡的項目全部都要做，包括 FB 和 Threads、網頁版、中英介面切換、評測、兩個模型的比較。萬一來不及，在 11/4 晚上依序降級：Threads → 介面雙語 → 網頁版。
- **組別**：Startup 組，以大數軟體（LargitData）名義參賽。
- **評審**：會看 3 分鐘影片、公開 repo，以及**公開的網頁版**。
  - 網頁版和後端要部署成公開網址，Chrome extension 仍然在本機錄影展示。
  - 部署位置交給實作者決定，可選 GCP VM 或 Cloud Run。EmbeddingGemma 2 和 hunch 都跑在 CPU 上。
  - 公開站一定要加防護，避免把 Muse credits 燒光：
    - 每個 IP 限速，例如每小時 10 次深查
    - 每天的花費設上限
    - 單次輸入的字數設上限
    - 相同輸入的結果做快取
    - 頁面上要放個資提醒
- **評測集**：Claude 先標初稿，David 用約 30 分鐘校對。

## 6.2 Meta Hackathon 規則（2026-11-02 讀自 CV 參賽指南）
- **截止時間**：11/4 21:00 ET，在 CV 平台送出。需要附上**公開的 repo**，以及**長度 3 分鐘的 demo 影片**。評審的依據是影片、程式碼和實際產品。
- **評分標準**：
  - Impact 30%
  - Use of Meta AI Tooling 25%：重點是有沒有超出基本整合
  - Technical Depth 20%
  - Demo 25%
  - 另有加分獎項：Best Agentic Use-Case $5K、Most Viral（在 X 上的互動數）
- **只能展示比賽期間新做的東西**，而且要讓評審清楚看出哪些是新做的，否則可能被取消資格。Startup 組可以沿用既有產品，但必須標明新舊。所以 README 和影片要明確寫出：InfoMiner 只提供資料來源，`gemma-embed-peft` 是比賽前的既有成果，Agent、extension 和 hunch 整合都是這次新做的。
- **明文禁止的題目類型**包括「Anything political or involving war」和「Basic RAG Applications」。因此：
  - **Meta 版本完全不放選舉和政治內容**：評測集、demo 和影片都不放。題目定位為防詐騙，Problem statement 選「Build for Your World」。
  - 選舉事實主張的評測只用在算力選拔，那 10 筆評測集保留給選拔使用。
  - 包裝上強調 Agent 和蒸餾架構，避免被看成基本的 RAG。
- **加強「Meta 工具使用」這一項**：
  - Muse 同時擔任 teacher 和 Agent，把能力蒸餾成 System 1
  - 用 Muse Spark 的圖片理解功能讀詐騙貼文裡的圖片和截圖。這是低成本的加分項目，放進第二段深查。

## 6.3 David 追加的需求（2026-11-02）
- **第一段的判斷來源可以切換**，在 extension 的設定頁和網頁版的「進階設定」裡選擇。三種來源用同一套題目和回應格式：
  - `local`（預設）：hunch proxy，跑本地的 EmbeddingGemma 2 student
  - `jev`：直接呼叫 TypeSafe System One API
    - 端點：`POST https://api.typesafe.ai/v1/systemone`，model 用 `jev-latest`
    - 題目格式和 hunch 相同，都是 noul、choice、score
    - 金鑰放在後端的 `TYPESAFE_API_KEY`
  - `muse`：直接用 Muse 回答題目，也就是 teacher 的邏輯，不經過 student
- **所有金鑰都留在後端。** 使用者只選要用哪一種來源，不需要輸入任何金鑰。
- 三種來源同時當作評測比較組，比較延遲、成本，以及和 Muse 的一致率。這組數據兩項交付都用得到。
- Jev 也可以當 hunch 的 teacher。hunch 原本就是設計來代理 `/v1/systemone`。這點留給實作者在 preflight 時試，看哪一個 teacher 的一致率比較好。
- **上架 Chrome Web Store**（原本列在非目標，改成目標）：
  - extension 預設的後端網址改成公開站
  - 隱私權政策頁放在公開站的 `/privacy`
  - 上架資料：說明文字、截圖、權限理由
  - 審核可能要好幾天，所以不影響 Meta 送件。影片裡用本機載入的版本錄
  - 開發者帳號和實際送審要由 David 確認後才執行

## 7. 留給實作者決定的部分
- 後端框架、extension 打包方式、前端樣式細節
- 各門檻的實際數值（用評測集調整）
- Muse teacher 的 prompt 寫法
- 萬一 hunch 無法在本機安裝，退回簡化版：EmbeddingGemma 2 加上 logistic regression 分類頭，維持同樣的題目介面
