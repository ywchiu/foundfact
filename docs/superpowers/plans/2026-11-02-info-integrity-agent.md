# 查證助手 VeriFeed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做出一個 Chrome extension 和公開網頁版。extension 在 Facebook／Threads 動態牆上，用 System 1 判斷模型（hunch + EmbeddingGemma 2）標出疑似詐騙的貼文；使用者點擊後，由 Muse Agent 一步步查證，產出附證據的報告。

**Architecture:** 一個 FastAPI 後端，同時承擔三個角色：
- **hunch 的 teacher 端點**，背後由 Muse 回答
- **第一段 `/screen`**：每題分開呼叫 hunch proxy，再加上 kNN 比對已知案例
- **第二段 `/verify`**：以 SSE 串流 Agent 事件

extension 和網頁版共用同一個報告渲染器 `shared/report.js`。hunch proxy 是獨立的 process，使用自己的 SQLite store。

**Tech Stack:**
- Python 3.12、uv、FastAPI、httpx、sse-starlette、pytest、respx
- sentence-transformers，用 `google/embeddinggemma-2` 做 kNN 編碼
- hunch，從 GitHub 安裝 `undrgrnd-labs/hunch`
- Chrome MV3，純 JS、不打包，測試用 vitest + jsdom
- 網頁版是純 HTML/JS；部署用 Docker + Cloud Run

**Spec:** `docs/superpowers/specs/2026-11-02-info-integrity-agent-design.md`。實作前**必讀** §3、§6、§6.1、§6.2。

## Global Constraints

- **David 的決定（2026-11-02）：一律先用 Muse。**
  - 第一段的預設來源是 `muse`：`screen_post` 的預設值、extension 和網頁版的預設選項都是 muse
  - 執行順序調整成：Task 0–3 → **Task 5（先做 MuseStage1 和 FallbackStage1）** → 6 → 7 → 8 → 9 → 回頭做 Task 4（hunch / local） → JevStage1 → 10–13
  - Jev 等 `TYPESAFE_API_KEY` 到位後再接
- **執行方式：Native。** 由 Claude 在 session 中依序實作，最後交給 Fable 和 Codex 做整體 review。

- **Muse 連線**：
  - base URL：`https://api.meta.ai/v1`
  - model：`muse-spark-1.3`，**只用 Standard 版**，不得使用 `-contributor`
  - 金鑰：環境變數 `MUSE_API`，只能放在後端，不得出現在 extension 或網頁的程式碼裡
- **Meta 版只做防詐騙**：
  - repo 裡的 demo、範例、網頁範例按鈕、影片都**不得**出現政治或選舉內容
  - 選舉評測資料放在 `data/eval/election.jsonl`，加入 `.gitignore`，不進公開 repo
- **紅條文字**：
  - 中文：「⚠ 這篇貼文可能是{type}詐騙」，右側「by 查證助手 · 看原因 →」
  - 英文：「⚠ This post may be a {type} scam」，右側「by VeriFeed · Why? →」
- **四類判斷**：`supported` 證據支持、`refuted` 證據反駁、`insufficient` 證據不足、`needs_review` 需人工複核
- **沒有指向任何證據 ID 的判斷，一律改成 `insufficient`。**
- **第一段題目每題分開送出請求。** 題目 ID 固定為 `is_scam_like`（noul，one-sided）、`has_checkable_claim`（noul）、`pressure`（score，0–3）。
- **深查只在使用者點擊後執行**，不自動深查。
- **網域**：manifest 要涵蓋 `*://*.facebook.com/*`、`*://*.threads.com/*`、`*://*.threads.net/*`。
- **公開站限制**：
  - 深查：每個 IP 每小時 10 次
  - 輸入：最多 4,000 字
  - 每日 Muse 花費上限：US$15
  - 相同輸入在 24 小時內走快取
- **Teacher 標註預算上限 US$30**，由 `data/scripts/label_teacher.py` 強制執行。
- **Commit 訊息結尾要加：**
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  和 `Claude-Session: https://claude.ai/code/session_01UNLV4FDDS2uiEfVbsBDt3d`

## Review Focus

1. **Facebook 的虛擬捲動會回收貼文的 DOM 節點**：同一個節點可能被換成另一篇貼文。預期行為是紅條只跟著原本那篇走，不會殘留或重複。測試在 Task 9。
2. **Muse 回傳的證據 ID 不在證據清單裡，或沒有任何證據 ID**：預期該條判斷變成 `insufficient`，報告照常產出。測試在 Task 2 和 Task 6。
3. **Muse 在串流途中逾時、回 5xx，或 `web_search` 沒有真的去搜尋**：預期 SSE 送出 `step` 的 `status:"error"`，或「未找到網路來源」，接著送出部分報告和 `done`，不能讓連線一直掛著。測試在 Task 6。
4. **空字串、只有網址、超過 4,000 字、純英文或 emoji 的貼文**：預期 `/screen` 和 `/verify` 都會回應，超長的截斷，空字串回 422。測試在 Task 5 和 Task 7。
5. **hunch proxy 掛掉或還沒畢業**：預期 `/screen` 改走 kNN 加規則的保底路徑，並標示 `answered_by:"fallback"`，不能回 500。測試在 Task 5。

---

## File Structure

```
fraud_detection/
  .gitignore  .env(已存在，不進版控)  README.md
  backend/
    pyproject.toml
    app/
      config.py      設定：MUSE_API、HUNCH_URL、各種上限
      models.py      Pydantic：Post, Evidence, Claim, ClaimVerdict, Report, ScreenResult, StepEvent
      evidence.py    enforce_evidence()：判斷降級規則
      muse.py        MuseClient：chat_json()、search()、vision_describe()，並記錄花費
      teacher.py     hunch teacher 端點的實作
      cases.py       CaseStore：EmbeddingGemma 2 編碼、kNN
      screen.py      Stage1：HunchStage1、FallbackStage1、decide()
      agent.py       verify_stream()：async generator，產出 StepEvent 和 Report
      guard.py       RateLimiter、BudgetGuard、ResultCache、clip_text()
      api.py         FastAPI 路由
    tests/           每個模組各一個 test_*.py
  data/
    scripts/ build_cases.py  fetch_posts.py  label_teacher.py
    cases.jsonl  posts.jsonl  eval/scam.jsonl  eval/election.jsonl(gitignored)
  eval/ run_eval.py  compare_embeddings.py  results/
  shared/ report.js  i18n.js  report.css
  extension/ manifest.json  background.js  content/{scanner.js,fb.js,threads.js,banner.js}  sidepanel/{index.html,panel.js}  shared/(建置時從 /shared 複製)  tests/
  web/ index.html  app.js  (shared 由後端靜態提供)
  deploy/ Dockerfile  cloudrun.md
  docs/ notes/muse-api.md  video-script.md  submission.md
```

---

### Task 0: 專案骨架與 Muse API 實測

**Files:** 建立 `.gitignore`、`backend/pyproject.toml`、`backend/app/config.py`、`backend/scripts/probe_muse.py`、`docs/notes/muse-api.md`

**Interfaces:**
- Produces: `config.Settings`，欄位包括 `muse_api: str`、`muse_base: str = "https://api.meta.ai/v1"`、`muse_model: str = "muse-spark-1.3"`、`hunch_url: str = "http://127.0.0.1:8765"`、`daily_budget_usd: float = 15.0`、`max_chars: int = 4000`、`verify_per_ip_hour: int = 10`。讀取 `../.env`。

- [ ] **Step 1：初始化 repo**
  - 執行 `git init`
  - `.gitignore` 加入：`.env`、`.superpowers/`、`data/eval/election.jsonl`、`*.db`、`__pycache__/`、`.venv/`、`eval/results/raw/`
- [ ] **Step 2：建立 uv 專案**
  - 用 `uv init backend` 建立專案
  - 加入依賴：`fastapi uvicorn httpx sse-starlette pydantic-settings sentence-transformers numpy`
  - 加入開發依賴：`pytest pytest-asyncio respx`
- [ ] **Step 3：寫 `probe_muse.py`，實際打 4 次 API，把原始回應存到 `docs/notes/raw/*.json`**
  1. Chat Completions 加 `response_format` json_schema，要求回傳 `{p_yes}`
  2. Responses API 加 `tools:[{"type":"web_search"}]` 和 `include:["web_search_call.results"]`，問題是一則中文詐騙主張
  3. 同樣的 Responses 請求，加上 `stream:true`，記下所有事件的 `type` 名稱
  4. Responses API 加 `text.format` 結構化輸出（不帶 web_search）
  5. 另外附一張圖片 URL 做圖片理解，算第 5 次，可選
- [ ] **Step 4：把結果寫進 `docs/notes/muse-api.md`**
  - 每種呼叫的請求格式和回應的關鍵欄位路徑
  - 串流事件名稱
  - 每次的 `usage` token 數
  - 依 Standard 價格換算的費用：輸入 $1.25/M、輸出 $4.25/M、搜尋 $2.50/千次

  **後面的 Task 2、4、6 都以這份筆記為準。**
- [ ] **Step 5：Commit**：`chore: scaffold backend and record Muse API probe`

### Task 1: 資料模型

**Files:** 建立 `backend/app/models.py` 和 `backend/tests/test_models.py`

**Interfaces（Produces，後面所有任務都用這些型別）：**
```python
class Post(BaseModel): id: str; platform: Literal["facebook","threads","web"]; author: str = ""; text: str; link_domains: list[str] = []; image_urls: list[str] = []; is_sponsored: bool | None = None
class Evidence(BaseModel): id: str; source_type: Literal["web","local_case","blocklist","image"]; url: str | None; title: str; snippet: str; date: str | None = None
class Claim(BaseModel): id: str; text: str
Verdict = Literal["supported","refuted","insufficient","needs_review"]
class ClaimVerdict(BaseModel): claim_id: str; verdict: Verdict; evidence_ids: list[str]; rationale: str
class SimilarCase(BaseModel): case_id: str; title: str; scam_type: str; similarity: float; url: str | None
class ScreenResult(BaseModel): post_id: str; label: Literal["high","check","none"]; p_scam: float; p_claim: float; pressure: int | None; scam_type: str | None; similar: list[SimilarCase]; answered_by: Literal["proxy","backend","cache","fallback"]
class Report(BaseModel): post_id: str; risk: Literal["high","check","low"]; summary: str; claims: list[Claim]; verdicts: list[ClaimVerdict]; evidence: list[Evidence]; similar: list[SimilarCase]; pressure: int | None; actions: list[str]; lang: Literal["zh","en"]
class StepEvent(BaseModel): step: Literal["extract","local","search","image","judge","conclude"]; status: Literal["running","done","error"]; detail: str
```

- [ ] **Step 1：寫測試 `test_post_rejects_empty_text`**：`Post(id="1", platform="web", text="")` 應該拋出 ValidationError。另外用 `test_report_roundtrip` 驗證 `Report` 轉 JSON 再轉回來，內容不變。
- [ ] **Step 2：執行** `cd backend && uv run pytest tests/test_models.py -v`。預期 FAIL，因為還沒有 import 可用。
- [ ] **Step 3：實作 models.py**。`Post.text` 用 `min_length=1`。
- [ ] **Step 4：再執行一次**，預期 PASS。
- [ ] **Step 5：Commit**：`feat: core data models`

### Task 2: 判斷降級規則和 Muse client

**Files:** 建立 `backend/app/evidence.py`、`backend/app/muse.py`、`backend/tests/test_evidence.py`、`backend/tests/test_muse.py`

**Interfaces:**
- Produces:
  - `enforce_evidence(verdicts: list[ClaimVerdict], evidence: list[Evidence]) -> list[ClaimVerdict]`
  - `class MuseClient(settings)`，方法包括：
    - `async chat_json(system: str, user: str, schema: dict, name: str) -> dict`
    - `async search(query: str, lang: str) -> tuple[str, list[Evidence]]`：回傳答案文字，以及由 `web_search_call.results` 和 `url_citation` 合併、去重而成的證據。證據 id 依序為 `w1, w2…`
    - `async vision_describe(image_url: str, lang: str) -> str`
  - `spent_usd: float` 屬性，依照 usage 累計花費

- [ ] **Step 1：寫測試**
  ```python
  def test_unknown_evidence_ids_downgrade():
      ev=[Evidence(id="w1",source_type="web",url="u",title="t",snippet="s")]
      v=[ClaimVerdict(claim_id="c1",verdict="refuted",evidence_ids=["w9"],rationale="x"),
         ClaimVerdict(claim_id="c2",verdict="refuted",evidence_ids=[],rationale="x"),
         ClaimVerdict(claim_id="c3",verdict="refuted",evidence_ids=["w1","w9"],rationale="x")]
      out=enforce_evidence(v,ev)
      assert [o.verdict for o in out]==["insufficient","insufficient","refuted"]
      assert out[2].evidence_ids==["w1"]
  ```
  `test_muse.py` 用 respx mock 掉 `https://api.meta.ai/v1`，回應內容直接用 Task 0 存下的 raw JSON fixture。要驗證：
  - `search()` 解析出來的證據有正確的 url 和 title，而且已去重
  - `spent_usd > 0`
  - 回應 5xx 時重試 2 次後拋出 `MuseError`
- [ ] **Step 2：執行**，預期 FAIL。
- [ ] **Step 3：實作**
  - `needs_review` 只要有至少一個有效的證據 ID 就保留，否則降級
  - client 用 `httpx.AsyncClient`，timeout 60 秒
  - 解析的欄位路徑照 `docs/notes/muse-api.md`
- [ ] **Step 4：執行**，預期 PASS。
- [ ] **Step 5：Commit**：`feat: Muse client and evidence enforcement`

### Task 3: 已知案例資料庫與 kNN

**Files:** 建立 `data/scripts/build_cases.py`、`backend/app/cases.py`、`backend/tests/test_cases.py`；產出 `data/cases.jsonl`

**Interfaces:**
- Produces:
  - `cases.jsonl` 每一行是 `{"case_id","scam_type","claim_text","verdict_text","source","url","date"}`，其中 `scam_type` 必須是 `investment|impersonation|phishing|shopping|romance|other` 之一
  - `class CaseStore(path, encoder)`，方法有 `knn(text: str, k: int = 3) -> list[SimilarCase]` 和 `embed(texts) -> np.ndarray`
  - `Encoder` 是一個 protocol，提供 `encode(list[str]) -> np.ndarray`，向量需 L2 正規化
  - 正式版用 `GemmaEncoder("google/embeddinggemma-2")`，跑在 MPS 上，查詢加上前綴 `"task: search result | query: "`。這個前綴的正確寫法以 HF 模型卡為準，寫進註解。

- [ ] **Step 1：寫測試**
  - 用 `FakeEncoder` 把字元雜湊成向量
  - `test_knn_returns_sorted_top_k`：相似度要遞減，筆數等於 k
  - `test_knn_empty_store`：資料庫是空的時候回傳 `[]`
- [ ] **Step 2：執行**，預期 FAIL。
- [ ] **Step 3：實作 cases.py**。向量算一次後快取成 `data/cases.npy`，並把 `cases.jsonl` 的 mtime 存起來，jsonl 有變動時重算。
- [ ] **Step 4：寫 `build_cases.py`**
  - **輸入**：
    - `/Users/david/project/distributed_crawler/news/` 下 `mygopen.py`、`tfc.py`、`news_1658tw.py` 的輸出。先讀這幾個爬蟲找到輸出方式，用最小的方式抓近 6 個月的文章
    - Cofacts 資料集 `Cofacts/line-msg-fact-check-tw`。需要登入的話，跳出來請 David 執行 `! huggingface-cli login`
  - **處理**：
    - 每筆都要拆成「原始可疑訊息」`claim_text` 和「查核結論」`verdict_text`
    - 抓不出原始訊息的就丟掉，例如只有宣導內容的
    - `scam_type` 用 `MuseClient.chat_json` 分類
    - **排除政治和選舉類**：用 Muse 判斷 `is_political`，判定為政治類的不寫進 `cases.jsonl`
  - **目標數量**：200–500 筆
- [ ] **Step 5：檢查結果**
  - 執行 `uv run python data/scripts/build_cases.py`，然後 `wc -l data/cases.jsonl`，預期 ≥ 200
  - 隨機抽 10 筆印出來，人工確認 claim 和 verdict 有分開
- [ ] **Step 6：Commit**：`feat: known-case store with EmbeddingGemma 2 kNN`

### Task 4: hunch teacher 與 preflight（限 4 小時，超時就改走保底方案）

**Files:** 建立 `backend/app/teacher.py`、`backend/tests/test_teacher.py`、`data/scripts/fetch_posts.py`、`data/scripts/label_teacher.py`、`docs/notes/hunch-preflight.md`

**Interfaces:**
- Consumes：`MuseClient.chat_json`
- Produces：
  - `QUESTIONS: dict[str, dict]`，定義三個題目，內容如下（hunch 的題目格式）：
    - `is_scam_like`：noul，`instructions` 為 "Does this social media post show scam tactics: guaranteed returns, impersonating a celebrity/government/brand, pushing readers to LINE/private chat, suspicious links, or urgent pressure to pay/act? Judge only from the post itself."
    - `has_checkable_claim`：noul，`instructions` 為 "Does this post state a specific factual claim that could be checked against outside sources (who said/did what, official announcements, numbers, events)?"
    - `pressure`：score，criteria 四個等級：`["No pressure", "Mild promotional language", "Clear urgency or guaranteed gains", "Extreme pressure: deadlines, threats, or demands to pay/transfer now"]`
  - `async answer(payload: dict) -> dict`：實作 hunch 的 teacher 協定，輸入 `{"state","questions"}`，輸出 `{"answers"}`。noul 回 `{"type":"noul","noul":p}`，score 回 `{"type":"score","probabilities":{"0":..}}`
  - `api.py` 掛上 `POST /teacher/v1/answer`，只允許 127.0.0.1 呼叫

- [ ] **Step 1：寫測試**（mock 掉 `chat_json`）
  - noul 的答案要落在 [0, 1]
  - score 的機率加總要等於 1 ± 1e-6
  - 缺少題目時拋 400
- [ ] **Step 2：執行**，預期 FAIL。接著實作 `teacher.py`：prompt 和 schema 照 hunch 的 `examples/teacher_openrouter.py` 改寫，每題一次 `chat_json`，同一請求的多題以 `asyncio.gather` 並行。執行測試，預期 PASS。
- [ ] **Step 3：安裝 hunch**
  - `git clone https://github.com/undrgrnd-labs/hunch ~/project/hunch`
  - `cd ~/project/hunch && uv sync --all-packages`，需要 Rust ≥ 1.88
  - `cd examples && uv run download.py embeddinggemma-2 --yes`
  - 預期 `uv run --package hunch pytest -q hunch/tests` 通過
  - **如果 1 小時內裝不起來**：在 `docs/notes/hunch-preflight.md` 記下錯誤，跳過 Step 4–6，在 Task 5 只實作 `FallbackStage1`
- [ ] **Step 4：寫 `fetch_posts.py`**
  - 用 infominer-fetch skill 抓 InfoMiner 上 FB 和 Threads 的公開貼文文字，600 篇，關鍵字涵蓋投資、贈品、名人、優惠、一般生活
  - 把 `cases.jsonl` 的 `claim_text` 也包裝成 posts 加進去
  - 輸出 `data/posts.jsonl`，總共 ≥ 800 篇，格式是 `Post` 去掉 id 之外的欄位，再加上 `source`
- [ ] **Step 5：寫 `label_teacher.py` 並跑 preflight**
  - 啟動 `python -m hunch serve --db data/hunch.db --backend http://127.0.0.1:8000/teacher/v1/answer`，port 8765
  - 依序把 300 篇送到 `localhost:8765/v1/answer`，**每題一個請求**
  - 每 50 篇印一次累計花費，超過 US$30 就停
  - 查看每題 status 的畢業狀態
- [ ] **Step 6：判斷結果**
  - 在 `docs/notes/hunch-preflight.md` 記錄每題是否畢業、一致率，以及花費
  - `is_scam_like` 沒畢業：再送 500 篇，然後再判斷一次
  - 仍然沒畢業：標記這題走保底方案
- [ ] **Step 7：Commit**：`feat: Muse teacher for hunch and preflight labeling`

### Task 5: 第一段 `/screen`

**Files:** 建立 `backend/app/screen.py`、`backend/app/api.py`（建立 app 和 `/screen`、`/health`）、`backend/tests/test_screen.py`

**Interfaces:**
- Consumes：`CaseStore.knn`、`QUESTIONS`、`teacher.answer`、`Settings.hunch_url`、`Settings.typesafe_api_key`（Task 0 的 Settings 要加這個欄位，讀環境變數 `TYPESAFE_API_KEY`）
- Produces：
  - `decide(p_scam: float, p_claim: float, hi: float = 0.8, mid: float = 0.4, claim: float = 0.7) -> Literal["high","check","none"]`
  - `Provider = Literal["local","jev","muse"]`
  - 四個 Stage1 實作，都提供 `async screen(post: Post) -> ScreenResult`：
    - `HunchStage1`：`local`，打 `{hunch_url}/v1/answer`
    - `JevStage1`：打 `POST https://api.typesafe.ai/v1/systemone`，帶 `model:"jev-latest"`，題目用同一份 `QUESTIONS`
    - `MuseStage1`：直接呼叫 `teacher.answer`
    - `FallbackStage1`
  - `ScreenResult` 加一個欄位 `provider: Provider`；`answered_by` 的可能值擴充為 `"proxy"|"backend"|"cache"|"fallback"|"jev"|"muse"`。Task 1 的 models 要配合修改。
  - `async screen_post(post, provider: Provider = "local") -> ScreenResult`：選定的來源失敗或逾時就改用 fallback。逾時上限：local 300 ms，jev 和 muse 8 秒。
  - `GET /providers`：回傳 `{"local":bool,"jev":bool,"muse":bool}`，表示每種來源目前能不能用，例如沒設 key 的是 false
  - `POST /screen`：body 是 `{"posts": [Post], "provider": Provider}`，最多 20 篇；回應 `{"results":[ScreenResult]}`
  - `scam_type` 取 kNN 第一名的類型，而且只在相似度 ≥ 0.6 時填入，否則填 `None`

- [ ] **Step 1：寫測試**
  - `test_decide_thresholds`：
    - `decide(0.9,0)` 應為 `high`
    - `decide(0.5,0)` 應為 `check`
    - `decide(0.1,0.8)` 應為 `check`
    - `decide(0.1,0.1)` 應為 `none`
  - `test_screen_falls_back_when_hunch_down`：用 respx 讓 8765 回 connect error，預期 `answered_by=="fallback"`，HTTP 200
  - `test_fallback_rules`：
    - 「保證月報酬30% 加LINE」的 `p_scam` ≥ 0.8
    - 「今天去爬山」的 `p_scam` < 0.4
  - `test_screen_long_and_url_only`：
    - 5,000 字的貼文能回應，`ScreenResult` 正常產出，內部會截斷到 4,000 字
    - 只有 `"https://bit.ly/x"` 的貼文能回應
  - `test_screen_rejects_empty`：`text=""` 回 422
  - `test_jev_provider_maps_answers`：用 respx mock `api.typesafe.ai`，回應 `{"answers":{"is_scam_like":{"type":"noul","noul":0.9},...}}`，預期 `label=="high"` 且 `provider=="jev"`
  - `test_jev_without_key_falls_back`：沒有 `TYPESAFE_API_KEY` 時，`/providers` 的 jev 為 false，`/screen` 帶 `provider:"jev"` 仍然回 200，`answered_by=="fallback"`
- [ ] **Step 2：執行**，預期 FAIL。
- [ ] **Step 3：實作**
  - `FallbackStage1` 的 `p_scam` 計算：`max(kNN 第一名相似度, 規則分數)`
  - 規則分數的關鍵字表集中寫在 `screen.py` 的 `RULES`：保證獲利、加LINE、飆股、限時、免費領、帳戶異常、點此連結，以及常見的短網址網域
  - 命中 1 條得 0.5，命中 2 條以上得 0.85
  - `has_checkable_claim` 的保底值固定 0.5，`pressure` 的保底值為 None
- [ ] **Step 4：執行**，預期 PASS。另外跑一次冒煙測試：`uv run uvicorn app.api:app --port 8000`，再用 curl 打 `/screen`，送 2 篇範例。
- [ ] **Step 5：Commit**：`feat: stage-1 screening with hunch and fallback`

### Task 6: 第二段 Muse Agent，`/verify` SSE

**Files:** 建立 `backend/app/agent.py`、`backend/tests/test_agent.py`；修改 `backend/app/api.py`

**Interfaces:**
- Consumes：`MuseClient`、`CaseStore.knn`、`enforce_evidence`、`screen_post`
- Produces：
  - `async verify_stream(post: Post, lang: Literal["zh","en"]) -> AsyncIterator[tuple[str, dict]]`，產出的事件依序為 `("step", StepEvent)` 若干次、`("report", Report)` 一次、`("done", {})`
  - `POST /verify`：body 是 `{"post": Post, "lang": "zh"|"en"}`，回傳 SSE，事件名稱和上面一樣

- **流程**：依照 spec §3.2 的步驟，各步驟的 `step` 值如下：
  - `extract`：用 `chat_json` 抽出 1–3 條主張
  - `local`：kNN 加上 blocklist 比對。blocklist 檔案是 `data/blocklist.txt`，一行一個網域，取自數發部和 165 的名單。命中的轉成 `Evidence(source_type="blocklist"|"local_case", id="l1…")`
  - `image`：如果有 `image_urls`，用 `vision_describe` 讀第一張圖，轉成 `Evidence(source_type="image")`
  - `search`：每條主張呼叫一次 `search()`；如果找不到任何網路證據，`detail` 寫「未找到網路來源」或 "No web sources found"
  - `judge`：用 `chat_json` 產出 `ClaimVerdict[]`，prompt 裡只列出證據的 id、title、snippet，接著呼叫 `enforce_evidence`
  - `conclude`：產出 `risk`、`summary`、`actions`，語言依 `lang`。台灣情境的 actions 要包含「撥打 165」

- [ ] **Step 1：寫測試**（`MuseClient` 用假的物件替換）
  - `test_stream_order`：事件順序要是 `extract → local → search → judge → conclude`，接著是 `report`、`done`；每個 step 都要有 running 和 done 兩個狀態
  - `test_bad_evidence_ids_become_insufficient`：假的 judge 回傳不存在的證據 ID，report 裡該條判斷要是 `insufficient`
  - `test_search_failure_still_reports`：`search()` 拋出 `MuseError`，預期有一個 `status:"error"` 的 search step，之後照常出現 report 和 done
  - `test_no_web_results_message`：`search()` 回傳空的證據，預期 `detail` 含「未找到網路來源」
  - `test_image_step_only_with_images`：沒有圖片的貼文不會出現 `image` 這個 step
- [ ] **Step 2：執行**，預期 FAIL。
- [ ] **Step 3：實作**
  - 每個 step 前後都 yield 事件
  - 整個流程的總 timeout 是 90 秒，超時就以已經蒐集到的證據直接進入 judge
- [ ] **Step 4：執行**，預期 PASS。接著打真的 Muse 做一次冒煙測試：`curl -N -X POST localhost:8000/verify -d @data/samples/scam1.json`，確認事件真的有一個一個串流出來。
- [ ] **Step 5：Commit**：`feat: Muse verification agent with SSE steps`

### Task 7: 公開站防護

**Files:** 建立 `backend/app/guard.py`、`backend/tests/test_guard.py`；修改 `backend/app/api.py`

**Interfaces:**
- Produces：
  - `clip_text(s: str, n: int) -> str`
  - `RateLimiter(per_hour: int)`，方法 `.check(ip) -> bool`，在記憶體中以滑動視窗計算
  - `BudgetGuard(daily_usd)`，方法 `.allow(spent_today) -> bool`；日期以台北時區換日
  - `ResultCache(ttl_s=86400)`，方法 `.get(key)` 和 `.put(key, report)`；key 是 `sha256(text+lang)`

- **掛到 API**：
  - `/verify`：依序檢查 rate limit → budget → cache。快取命中時，照原順序快速重播 step 事件，然後送出快取的 report
  - 超過 rate limit 回 429，body 為 `{"error":"rate_limited"}`
  - 超過預算回 503，body 為 `{"error":"budget_exhausted"}`；此時 `/screen` 仍然可以使用
- [ ] **Step 1：寫測試**
  - rate limit：第 11 次回 429
  - 預算超過時 `/verify` 回 503，`/screen` 回 200
  - 同樣的輸入第二次不會呼叫 Muse，用 mock 的呼叫次數驗證
  - `clip_text("a"*5000, 4000)` 的長度是 4000
- [ ] **Step 2：執行**，預期 FAIL。接著實作，再執行，預期 PASS。
- [ ] **Step 3：Commit**：`feat: rate limit, budget, cache guards`

### Task 8: 共用報告渲染器與網頁版

**Files:** 建立 `shared/report.js`、`shared/i18n.js`、`shared/report.css`、`web/index.html`、`web/app.js`、`shared/tests/report.test.js`（用 vitest + jsdom）；修改 `api.py`，把 `/` 指向 `web/`、`/shared` 指向 `shared/` 做靜態服務

**Interfaces:**
- Produces（ES module）：
  - `renderSteps(container, stepEvents[], lang)`
  - `renderReport(container, report, lang)`
  - `streamVerify(baseUrl, post, lang, {onStep, onReport, onError})`：用 fetch 讀 SSE stream
  - `t(key, lang)`

- **畫面版型**：參考 `.superpowers/brainstorm/.../deep-report.html` 的 A 版，由上往下是：
  1. 結論卡
  2. 逐條主張，每條附四類標籤和可點的證據連結
  3. 第一段最像案例和相似度
  4. Agent 步驟清單（running 時顯示轉圈）
  5. 建議行動
- **網頁版**：參考「查詐一下」
  - 標題：「這是詐騙嗎？先查一下。」，英文版是 "Is this a scam? Check first."
  - 文字框加上字數計數 `/4000`
  - 3 個範例按鈕：可疑簡訊、投資邀請、假冒客服。**不放政治內容**
  - 個資提醒文字：「請先遮蔽個人資料；內容會送至 Meta Muse 分析」
  - 右上角放中文／英文切換
  - 「進階設定」可以選第一段的來源，選項有 Local EmbeddingGemma 2、Jev、Muse。報告的最像案例區塊要顯示這次用的是哪一個來源，以及延遲幾毫秒
- [ ] **Step 1：寫測試**
  - `renderReport` 遇到 `insufficient` 時顯示「證據不足」，英文是 "Insufficient evidence"
  - 證據連結要有 `target=_blank rel=noopener`
  - 貼文內容和證據 snippet 一律用 textContent 插入，不得用 innerHTML，用 `<img onerror>` 字串測試
- [ ] **Step 2：執行** `npx vitest run shared`，預期 FAIL。接著實作，再執行，預期 PASS。
- [ ] **Step 3：手動檢查**：開 `localhost:8000`，按範例按鈕，確認步驟會一個一個出現，最後出現報告。中英文都測一次。
- [ ] **Step 4：Commit**：`feat: shared report renderer and web app`

### Task 9: Chrome extension，Facebook

**Files:** 建立 `extension/manifest.json`、`background.js`、`content/scanner.js`、`content/fb.js`、`content/banner.js`、`sidepanel/index.html`、`sidepanel/panel.js`、`extension/tests/scanner.test.js`，以及 `extension/build.sh`（把 `/shared` 複製到 `extension/shared/`）

**Interfaces:**
- Produces：
  - `fb.js` 匯出 `findPosts(root): Element[]`：用 `[role="article"]` 找貼文，排除留言，留言是 article 底下的 article
  - `fb.js` 匯出 `extractPost(el): Post`：從貼文中抽出文字、作者、連結網域和圖片 URL。`id` 用 permalink 的 href，取不到時用文字的雜湊值
  - `scanner.js` 匯出 `createScanner(adapter, screenFn, render)`，回傳 `{start(), stop()}`
    - 用 MutationObserver 加 IntersectionObserver 偵測貼文
    - 依 post id 去重，每 400 ms 批次送一次，每批最多 20 篇
    - 在節點上記錄 `data-vf-id`；**節點被回收、id 改變時，必須先移除舊紅條再重新判斷**
  - `banner.js` 匯出 `mountBanner(el, result, lang, onWhy)`：用 Shadow DOM 加上紅條或琥珀色標示，文字照 Global Constraints
  - 訊息協定：content 送 `{type:"screen",posts}` 給 background，background 去打後端 `/screen`；content 送 `{type:"open_panel",post}`，background **在同一個事件處理函式裡同步呼叫** `chrome.sidePanel.open({tabId})`，然後把 post 存進 `chrome.storage.session`
  - panel 從 storage 讀出 post，再呼叫 `streamVerify`
  - 後端網址存在 `chrome.storage.local` 的 `backendUrl`。預設值是公開站網址，部署前先用 `http://127.0.0.1:8000`
  - `options/index.html` 設定頁可以設定三件事：後端網址、第一段來源（下拉選單，選項只列出 `/providers` 回傳 true 的）、語言。設定存在 `chrome.storage.local`，`provider` 會跟著每次 `/screen` 請求送出
  - manifest 的 `host_permissions` 包含三個站點網域、後端網址，以及 `http://127.0.0.1/*`

- [ ] **Step 1：寫測試**，用 jsdom 和 `extension/tests/fixtures/fb_feed.html`（從真實 FB 頁面存下、去掉個資的片段）
  - `findPosts` 回傳的數量要等於 fixture 裡的貼文數，留言不算
  - `extractPost` 要抓到 fixture 第 1 篇的文字和 `lin.ee` 網域
  - `test_recycled_node_rebanners`：把一個節點的內容換成另一篇貼文之後，舊紅條要被移除，並且用新的 id 重新呼叫 screenFn
  - `test_no_duplicate_banner`：同一篇貼文觸發兩次，只會出現一條紅條
- [ ] **Step 2：執行** `npx vitest run extension`，預期 FAIL。接著實作，再執行，預期 PASS。
- [ ] **Step 3：實機測試**
  - `bash extension/build.sh` 之後，在 Chrome 用「載入未封裝項目」載入 extension
  - 用 ego browser 裡的 FB 帳號滑動態牆，追蹤哪些詐騙粉專見 Task 12
  - 確認：有紅條，正常貼文不受影響；點「看原因」會開 Side Panel，並且一步步顯示查證過程
- [ ] **Step 4：Commit**：`feat: Chrome extension for Facebook feed`

### Task 10: Threads adapter，以及 extension 的雙語切換

**Files:** 建立 `extension/content/threads.js`、`extension/tests/fixtures/threads_feed.html`、`extension/tests/threads.test.js`；修改 `manifest.json` 和 `sidepanel/panel.js`

**Interfaces:**
- `threads.js` 提供和 `fb.js` 一樣的 `findPosts` 和 `extractPost`。content 依 `location.hostname` 選擇 adapter。
- popup 或 panel 上放語言切換開關，設定存在 `chrome.storage.local.lang`，紅條和報告都跟著這個設定。

- [ ] **Step 1：寫測試**：threads fixture 的貼文數要正確，並能抽出文字。
- [ ] **Step 2：執行**，預期 FAIL。接著實作，再執行，預期 PASS。
- [ ] **Step 3：實機測試** threads.com，然後 Commit：`feat: Threads adapter and language toggle`

如果時間來不及，依 spec §6.1 的順序降級：這個 task 是第一個被砍的。

### Task 11: 評測

**Files:** 建立 `data/eval/scam.jsonl`、`data/eval/election.jsonl`（gitignored）、`eval/run_eval.py`、`eval/compare_embeddings.py`；結果輸出到 `eval/results/*.json` 和 `*.md`

**Interfaces:**
- 評測資料每一行：`{"id","event_id","split":"tune"|"test","post":Post,"gold_label":"high"|"check"|"none","gold_claims":[{"text","verdict"}]}`
- `scam.jsonl` 共 30 筆：防詐 20 筆，加上難負例 10 筆（反詐宣導、正常促銷、正常客服公告）
- `split` 依 `event_id` 切分，tune 和 test 各約一半
- `run_eval.py --split test` 輸出以下指標：
  - 第一段：label 準確率、`p50/p99` 延遲、`answered_by` 的分布
  - 第二段：主張判斷的正確率、gold 為 `insufficient` 的那幾條中模型也答 `insufficient` 的比例（棄答率）、端到端延遲
  - 費用
  - student 和 teacher 的一致率，從 hunch 的 status 讀取
  - 加上 `--providers local,jev,muse` 參數：同一份 test 集對三種來源各跑一次，輸出比較表，欄位有準確率、p50 延遲、每千篇成本，以及和 muse 的一致率

- [ ] **Step 1：Claude 先標初稿**
  - 資料來源：`cases.jsonl` 以外的新案例，加上 InfoMiner 的難負例
  - 完成後交給 David 校對約 30 分鐘。**這一步要等 David 確認後才能跑 test**
- [ ] **Step 2：在 tune 集上調門檻**
  - 執行 `uv run python eval/run_eval.py --split tune --sweep`
  - 選出的 `hi/mid/claim` 寫回 `screen.decide` 的預設值
- [ ] **Step 3：跑 test 集**
  - 執行 `uv run python eval/run_eval.py --split test`
  - 產出 `eval/results/meta.md`，表格中要寫明樣本數
- [ ] **Step 4：Commit**：`feat: evaluation harness and results`

### Task 12: 部署、README、影片腳本、送件清單（Meta）

**Files:** 建立 `deploy/Dockerfile`、`deploy/cloudrun.md`、`README.md`、`docs/video-script.md`、`docs/submission.md`

- [ ] **Step 1：Dockerfile**
  - 從 python:3.12-slim 開始，裝 uv，把 EmbeddingGemma 2 的權重 bake 進 image
  - 用 supervisord 同時啟動 uvicorn 和 hunch serve，把 `data/hunch.db` 一起 COPY 進去，讓已畢業的 student 直接可以用
  - Cloud Run 設定：4 vCPU、8 GiB、最小 1 個 instance；`MUSE_API` 用 Secret Manager 注入
- [ ] **Step 2：部署前確認**
  - 部署會產生公開網址，開始燒 credits，**部署前先告訴 David**
  - 部署後，用公開網址跑網頁版的 3 個範例
  - 確認 429 和 503 都能觸發
- [ ] **Step 3：README（英文）**
  - 要清楚寫出 **「Built during the hackathon」和「Pre-existing」** 兩段
    - Pre-existing：InfoMiner 只當資料來源；`gemma-embed-peft` 是比賽前的研究成果，不包含在這次的 demo 裡
  - 架構圖
  - 如何執行
  - 評測結果：直接引用 `eval/results/meta.md`
  - 授權：MIT
- [ ] **Step 4：`docs/video-script.md`**，3 分鐘，英文旁白，分段如下：
  - 0:00–0:20 問題：台灣的投資詐騙
  - 0:20–1:10 實際操作：在 FB 動態牆上看到紅條，點開 Side Panel，Agent 一步步查證，最後產出報告
  - 1:10–1:50 Muse 當老師，把判斷能力蒸餾成 System 1：秀 `answered_by: proxy` 的 22 ms 對上 Muse 的數秒，以及一致率
  - 1:50–2:30 網頁版、圖片理解、報告附證據
  - 2:30–3:00 指標和影響力，最後秀 repo 和網址
  - **影片中不出現政治內容**
- [ ] **Step 5：`docs/submission.md`**，列出送件清單：
  - repo 已公開：**轉成公開前先問 David**
  - 影片連結可以公開觀看
  - Track 選 Startups，Problem statement 選 Build for Your World
  - 在 X 上發文並附上連結（Most Viral 獎）
  - 送件截止：11/4 21:00 ET
- [ ] **Step 6：準備 Chrome Web Store 上架**
  - 用 `extension/build.sh --release` 打包成 zip，預設後端改成公開站
  - 公開站加 `/privacy` 頁，中英各一份：說明只送公開貼文的文字和圖片網址到後端分析，不儲存個資，第一段可選 Jev 或 Muse 的外部服務
  - 在 `docs/store-listing.md` 準備上架資料：名稱、短說明、詳細說明、5 張 1280×800 截圖、各項權限的理由（facebook、threads 的 host 權限，sidePanel，storage）
  - **送審前要 David 確認**：開發者帳號、上架名稱
- [ ] **Step 7：Commit**：`docs: deploy, README, video script, submission checklist, store listing`

### Task 13（Meta 送件後，11/5–11/7）：算力選拔素材

**Files:** 建立 `eval/compare_embeddings.py` 的結果檔 `eval/results/embedding_compare.md`、`docs/compute-showcase.md`（簡報大綱）

- [ ] **Step 1：`compare_embeddings.py`**
  - 拿 `scam.jsonl` 每筆的 post 到 `cases.jsonl` 做檢索，算 hit@1 和 hit@3。正確答案是同一個 event_id 的案例；如果沒有，就用 Muse 判斷「同一種手法」的案例
  - 比較兩個模型：
    - `google/embeddinggemma-2`
    - `ywchiu/gemma-embed-peft`：base 用 `google/gemma-3-1b-pt` 加 LoRA，first-token pooling，輸出 1152 維向量，程式寫法照 spec §6
  - 另外量測吞吐量（每秒處理幾篇）
- [ ] **Step 2：跑 `run_eval.py --file data/eval/election.jsonl`**，這份結果只放進選拔簡報
- [ ] **Step 3：寫 `docs/compute-showcase.md`**
  - 簡報結構：公司和產品簡介 → 114 年算力成果（`gemma-embed-peft`）→ 產品化在 RAGi／InfoMiner → 新應用：VeriFeed 兩段式架構 → 實測數據 → Roadmap（包含場景 C 的 AI 生成偵測）
  - 送件格式：信件主旨【報名資料】115算力平台績優業者選拔：大數軟體有限公司，附上簡報和 logo，並填寫報名表單
  - **截止 11/8 23:59**
- [ ] **Step 4：Commit**：`docs: compute showcase materials`

---

## 時程（台灣時間）

| 時段 | Task |
|---|---|
| 11/2（一）下午到晚上 | 0、1、2、3 |
| 11/3（二）上午 | 4（限 4 小時）、5 |
| 11/3（二）下午到晚上 | 6、7、8 |
| 11/4（三）上午 | 9；同時請 David 用測試帳號追蹤詐騙粉專 |
| 11/4（三）下午 | 10、11（David 校對評測集） |
| 11/4（三）晚上 | 12，錄影片 |
| 11/5（四）10:00 前 | 送件（ET 時間 11/4 21:00） |
| 11/5–11/7 | 13；11/7 寄出選拔報名 |
