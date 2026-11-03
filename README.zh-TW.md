# FoundFact 查證助手

[English](README.md) · **繁體中文**

**把詐騙查證放進你的動態牆。** FoundFact 是一個 Chrome 擴充功能和網頁工具。你在 Facebook、Threads 滑動態時，它會替可能是詐騙的貼文加上提醒。點「看原因」，Meta Muse 驅動的 AI Agent 會當場查證這篇貼文：上網搜尋、比對已知詐騙案例、讀貼文裡的圖片，最後給你一份簡短的報告，每個判斷都附上證據來源。

由 [大數軟體 LargitData](https://www.largitdata.com) 為 Meta Global AI Developer Hackathon 開發（Startups 組 · Build for Your World）。

- 線上試用：**https://foundfact.infominer.io**（可以貼文字，也可以直接貼截圖）
- 示範影片（3 分鐘）：_待補_

## 要解決的問題

在台灣，很多詐騙是從社群動態開始的。常見的手法像是：

- 冒用名人的投資群組，例如「知名企業家免費送書，加 LINE 領取」；
- 「在家工作，時薪新臺幣 290 元，私訊我」的徵才貼文；
- 中獎通知，要你先付「一點運費」。

台灣事實查核中心、MyGoPen 這些查核單位每週都在破解這類手法。可是大家是在動態牆上遇到詐騙，不是在查核網站上；往往還沒想到要查，就已經上鉤了。

FoundFact 把查證帶到大家遇到詐騙的地方，而且會讓你看到來源，不只丟給你一個結論。

## 怎麼運作

```
 Facebook / Threads 動態牆                          FoundFact 後端（FastAPI，單一容器）
┌──────────────────────────┐   畫面上的貼文（批次）    ┌───────────────────────────────────────────┐
│ content script            │ ─────────────────────────▶ │ /screen  — 第一段快篩「System 1」         │
│  各平台轉接（FB、Threads） │                            │   可選 local | jev | muse                   │
│  Shadow DOM 紅色提醒條     │ ◀───────────────────────── │   local：hunch + EmbeddingGemma 2 學生模型  │
└────────────┬─────────────┘   標記 high / none          │          （有把握的「不是」→ 不呼叫 LLM）   │
             │ 點「看原因」                              │          其他 → 交給 Muse 老師              │
┌────────────▼─────────────┐                            │   jev：  TypeSafe Jev 1.14（OpenRouter）    │
│ Chrome 側邊欄              │   SSE：Agent 每一步        │   muse： Muse，json_schema，minimal effort │
│  即時顯示查證步驟          │ ◀───────────────────────── │                                             │
│  附來源的報告              │ ─────────────────────────▶ │ /verify  — 第二段查證「System 2」（Muse）  │
└──────────────────────────┘   貼文文字 + 圖片網址       │   1 讀圖，抄下圖上文字（視覺）             │
                                                         │   2 抽出可查證的主張                       │
 網頁版（/）— 貼上貼文或截圖，                            │   3 比對 137 個已知案例；檢查連結          │
 得到同樣的報告                                          │   4 Muse web_search 逐條搜尋              │
                                                         │   5 依證據判斷每條主張                     │
                                                         │   6 結論：風險、詐騙類型、建議行動         │
                                                         └───────────────────────────────────────────┘
```

- **已知的詐騙連結最先處理。**
  - 短網址（reurl.cc、bit.ly、lihi 等）由伺服器用 HEAD 請求追到最終網址，3 秒逾時，不會開啟頁面內容。
  - 最終網域會拿去比對內政部警政署因涉及詐騙而停止解析的 115,585 個網域。
  - 命中時不需呼叫任何模型，1 毫秒內標紅，提醒條上會寫出是哪個網域。
  - 名單來自政府資料開放平臺資料集 [176455](https://data.gov.tw/dataset/176455) 與
    [160055](https://data.gov.tw/dataset/160055)（政府資料開放授權條款第 1 版），由
    `data/scripts/build_blocklist.py` 重建。
  - 免費架站服務上的個別網站（例如 `shopeetw88.github.io`）會被比對到，但 `github.io`、`google.com`
    這類平台本身不會。
- **第一段每篇貼文都要跑，所以必須便宜。** 在擴充功能的設定裡可以選：
  - **local**：透過 [hunch](https://github.com/undrgrnd-labs/hunch) 代理層使用 Google EmbeddingGemma 2 學生模型。
    Muse 當老師教它；當它在「這篇貼文有沒有詐騙手法？」這題上學到跟 Muse 判斷一致，就開始自己回答。
    有把握的「不是」（日常貼文約 64%）不用呼叫 LLM，其餘交給 Muse 回答，同時繼續教學生。
  - **jev**：TypeSafe 的 Jev 1.14 System One 模型，約 0.5 秒回傳結構化的機率判斷。
  - **muse**：直接問 Muse。
- **第二段只在使用者要求時才跑。**
  - Muse Agent 把每一步即時串流到側邊欄。
  - 有圖片時先讀圖。Muse 會把圖上的文字抄下來，所以一張簡訊截圖會跟貼上的文字一樣被查證，
    裡面的網址也會被檢查。貼文自己的圖片不會被當成支持它自身主張的證據。
  - 報告裡每條主張都必須引用 Agent 真的找到的證據。沒有證據的主張只會標成「證據不足」，不會標成「被反駁」。
  - 結果快取 24 小時。公開站以每個 IP 的頻率限制和每日金額上限保護。
- **範圍：** 這個版本只看詐騙，不判斷政治或新聞內容。

### Muse 用在哪裡

| 用途 | 使用的 API 功能 |
|---|---|
| 第一段快篩 | Chat Completions，`response_format: json_schema`，`reasoning_effort: minimal` |
| 當本機學生模型的老師 | 同樣的 schema，由 hunch 透過 `/teacher/v1/answer` 呼叫（僅限本機） |
| 讀圖片和截圖 | 多模態 `image_url` 輸入；抄下圖上文字，包含網址 |
| 即時查證 | Responses API 搭配 `web_search` 工具，串流輸出 |
| 建立已知案例庫 | 把事實查核文章整理成簡短的「主張／查核結果」案例 |

## 實測結果

**評測集：** `data/eval/scam.jsonl` 共 30 篇，依事件分成 **tune** 和 **test** 兩組。

- **詐騙**：
  - 12 個已知案例，不放進案例庫，也不放進學生模型的訓練資料。
  - 8 篇 Threads 上具詐騙特徵的徵才貼文（標為高風險，但未證實是詐騙，見 `data/eval/codex_review.md`）。
- **容易誤判的正常貼文**（10 篇）：
  - 銀行和品牌的防詐宣導；
  - 真的抽獎得主公告，寫著「私訊我們領獎」；
  - 附有地址的正當兼職。

第一段在 **tune** 組的結果（n = 14；門檻是在這組上調的，數字僅供參考）：

| provider | 準確率 | 詐騙召回率 | 精確率 | p50 延遲 | 每千篇成本 |
|---|---|---|---|---|---|
| Muse | 0.93 | 0.89 | 1.00 | 2.6 s | $5.08 |
| local（hunch 學生 → Muse） | 0.93 | 0.89 | 1.00 | 1.8 s† | ~$1.9† |
| Jev 1.14 | 0.79 | 0.89 | 0.80 | 0.53 s | $0.03 |

第一段在保留的 **test** 組的結果（n = 16：11 篇詐騙、5 篇容易誤判的正常貼文；單次執行，
[`eval/results/meta.md`](eval/results/meta.md)；另一次設有搜尋限制的執行中，Muse 為 0.75，差一篇）：

| provider | 準確率 | 詐騙召回率 | 精確率 | p50 延遲 | 每千篇成本 |
|---|---|---|---|---|---|
| Muse | 0.81 | 0.82 | 0.90 | 2.7 s | $4.93 |
| local（hunch 學生 → Muse） | 0.88 | 0.82 | 1.00 | 4.7 s* | ~$3.7 |
| Jev 1.14 | 0.69 | 0.73 | 0.80 | 0.56 s | $0.03 |

† tune 組 14 篇中有 11 篇是 hunch 快取重播，延遲和成本數字因此顯得比較理想；不用快取重跑是 4.2 秒、每千篇 $2.80（[`eval/results/tune.md`](eval/results/tune.md)）。

\* 在沒看過的貼文上，16 篇裡有 12 篇交給老師（Muse），所以 local 模式要花 Muse 的回應時間，再加上代理轉送的時間。
學生模型自己回答了 4 篇。它的速度優勢要在一般動態流量上才看得出來，因為那裡大多是有把握的「不是」。

**第二段**（Muse Agent，11 篇 test 詐騙；[`eval/results/meta_fastsearch.md`](eval/results/meta_fastsearch.md)）：

- 網路搜尋用 low reasoning effort，提示詞要求最多搜尋 3 次、不開影片頁、在文中附引用。
  搜尋次數上限只是提示詞裡的要求，程式沒有強制。
- 限制前後比較：

  | | 不限制 | 限制後 |
  |---|---|---|
  | p50 延遲 | 57 s | **20 s** |
  | 每篇成本 | $0.19 | **$0.03** |
  | 主張判斷準確率 | 73% | 64% |

- 主張判斷準確率是判斷結果與標準答案一致的比例（共 11 條主張，一條約 9 個百分點）。
- 不論是否限制，82% 的報告判為「高風險」。
- 標準答案是「證據不足」時，Agent 100% 選擇不下結論，而不是亂猜。

難的案例是假新聞包裝的誘餌（某名人「官司」故事），以及一個看起來像普通教學的假 LINE 登入頁。
三種 provider 都沒抓到那個假 LINE 登入頁。

**學生模型預檢：** 在 821 筆由 Muse 標註的公開貼文上執行（總共 US$3.24）。`is_scam_like` 這題在
EmbeddingGemma 2 第 12 層達到可以自行回答「不是」的門檻（16 毫秒）：

- 約 64% 的貼文由本機模型回答「不是」。
- Muse 判為「是」的 102 筆中漏掉 4 筆。

另外兩題（貼文有沒有可查證的主張、施壓程度多高）沒有達到可以自行回答的門檻，仍交給 Muse。
細節見 [`docs/notes/hunch-preflight.md`](docs/notes/hunch-preflight.md)。

## 黑客松期間新做的 vs. 原本就有的

**黑客松期間新做的**（2026 年 11 月 2 日至 4 日，在 10 月 27 日至 11 月 4 日的開發期內；本 repo 的全部內容）：

- 兩段式架構。
- 後端：
  - Muse client 和查證 Agent；
  - 第一段的各個 provider，以及 Jev／OpenRouter 串接；
  - 頻率限制、金額上限和快取保護。
- Chrome 擴充功能（MV3），包含 Facebook、Threads 轉接、Shadow DOM 提醒條和側邊欄。
- 已知詐騙連結檢查：短網址展開加上警政署涉詐網域名單。
- 網頁版（可輸入文字或截圖，支援英文和繁體中文）與共用的報告呈現元件。
- 137 個案例的已知詐騙案例庫，以及 hunch 的 Muse 老師串接。
- 預檢標註、評測集與評測程式、部署檔。

**原本就有、當作工具或資料來源使用的：**

- **InfoMiner**（大數軟體的社群輿情平台）：只用來抓取公開粉專和 Threads 貼文做標註與評測，以及蒐集事實查核文章。
  本 repo 不含任何 InfoMiner 程式碼。
- **第三方開源專案與模型**：
  - [hunch](https://github.com/undrgrnd-labs/hunch) 和 eg2cpu（MIT／Apache-2.0）；
  - Google EmbeddingGemma 2（Apache-2.0）；
  - TypeSafe Jev，透過 OpenRouter 使用。
- **`ywchiu/gemma-embed-peft`**：大數軟體先前的 embedding 研究，這個 demo **沒有**用到。

## 自己跑起來

需要 Python 3.12 加 [uv](https://docs.astral.sh/uv/)、Node 20 以上，以及 Chrome。

```bash
cp .env.example .env            # MUSE_API=...（OPENROUTER_KEY=... 選填，用於 Jev）
cd backend && uv sync && uv run uvicorn app.api:app --port 8000
# 開啟 http://127.0.0.1:8000 — 網頁版
```

**選用：本機第一段學生模型。**

```bash
git clone https://github.com/undrgrnd-labs/hunch ~/hunch && cd ~/hunch && uv sync --all-packages
uv run python -m hunch serve --db /path/to/fraud_detection/data/hunch.db \
  --backend http://127.0.0.1:8000/teacher/v1/answer --port 8765 --layer 12
# 先用老師的標註初始化一次：  uv run python data/scripts/seed_hunch.py --exclude-eval
```

**安裝擴充功能：**

1. 執行 `bash extension/build.sh`。
2. 開啟 `chrome://extensions`，打開「開發人員模式」，點「載入未封裝項目」，選擇 `extension/`。
3. 打開 Facebook 或 Threads。

**跑測試：**

```bash
(cd backend && uv run pytest -q)   # 106 個測試
npm install && npm test            # 32 個測試（擴充功能轉接、掃描器、報告呈現）
```

**部署：** 線上站跑在一台小型 VM 上，前面是 nginx 和 Cloudflare，見 [`deploy/vm.md`](deploy/vm.md)。
那台伺服器的已知案例比對用 Jev（`CASE_MATCHER=jev`），不用 EmbeddingGemma 2。
[`deploy/cloudrun.md`](deploy/cloudrun.md) 是另一種部署方式，尚未實測。

## 隱私與安全

- API 金鑰只放在伺服器上，擴充功能和網頁版都拿不到。
- 擴充功能只讀動態牆上貼文的可見文字、作者、連結和圖片網址，不會讀私訊或帳號資料。
- 除了 24 小時的結果快取，什麼都不保存。見 [`/privacy`](web/privacy.html)。
- 不碰政治內容：Meta 版本只篩詐騙。

## 專案結構

```
backend/    FastAPI app：快篩、Muse Agent、各種保護（app/），tests/
extension/  Chrome MV3 擴充功能：content scripts、側邊欄、設定頁
web/        公開網頁版與隱私權頁
shared/     網頁版和擴充功能共用的報告呈現、多語系、樣式
data/       已知詐騙案例、評測集、預檢報告、資料腳本
eval/       評測程式與結果
deploy/     VM 部署說明（nginx、systemd）、Dockerfile 和 Cloud Run 說明
docs/       設計規格、實作計畫、筆記、影片腳本、提交清單
```

## 授權

MIT © 2026 LargitData。見 [LICENSE](LICENSE)。
