# Muse API 實測筆記（2026-11-02，muse-spark-1.3 Standard）

原始回應放在 `docs/notes/raw/`，測試腳本是 `backend/scripts/probe_muse.py`。

## 1. Chat Completions + json_schema（給 teacher 和第一段 `muse` provider 用）
- `POST /chat/completions`，帶 `response_format: {type: json_schema, json_schema: {name, strict, schema}}`
- 輸出位置：`choices[0].message.content`，內容是 JSON 字串，例如 `{"p_yes":0.99}`
- **一定要設 `reasoning_effort`。** 不設的話，一題會用掉約 1,300 個 reasoning token、耗時 9.5 秒。
  - 可用的值：`minimal | low | medium | high | xhigh | max`，不支援 `none`
  - `minimal`：174 個 output token，2.0 秒，約 US$0.0008／題
  - `low`：377 個 output token，2.4 秒
  - **第一段和 teacher 都用 `minimal`**
- usage 欄位：`usage.prompt_tokens` 和 `usage.completion_tokens`

## 2. Responses + web_search（給 Agent 的搜尋步驟用）
- `POST /responses`，帶 `tools:[{type:web_search}]` 和 `include:["web_search_call.results"]`
- **Muse 自己就是一個會多輪搜尋的 Agent。** 一次呼叫就跑了 7 次 `web_search_call`，output 依序交錯出現：
  - `reasoning`
  - `message`：帶 `phase:"commentary"`，例如「正在幫你查證…」「已找到初步線索…」
  - `web_search_call`：
    - `action.type`：`search` 時帶 `query`，`open_page` 時帶 `url`
    - `status`：`completed` 或 `failed`
    - `results[]`：每筆是 `{type:"text_result", title, url, snippet}`，**`snippet` 常常是空字串**
  - 最後一個 `message`：沒有 `phase`，是最終答案。`content[0].text` 加上 `annotations[]`，每個 annotation 是 `{type:"url_citation", url, title, start_index, end_index}`
- 證據片段：snippet 是空的，所以改用 `text[start_index:end_index]` 當作該來源的佐證片段
- 費用：一次約 62k input token（有 15.5k cached）加 3.7k output token，大約 US$0.08，再加上搜尋費 7 × $0.0025，**每條主張約 US$0.10，耗時約 33 秒**
- 這次查到的來源是台灣事實查核中心、警政署、證交所，**繁中的覆蓋率不錯**

## 3. 串流（stream:true）
事件 type 依序有：
- `response.created`、`response.in_progress`
- `response.output_item.added` / `.done`：`item` 可能是 reasoning、message 或 web_search_call
- `response.content_part.added`、`response.output_text.delta` / `.done`
- `response.web_search_call.in_progress` / `.searching` / `.completed`
- `response.output_text.annotation.added`
- `response.completed`

**用法：** Agent 的 search 步驟改成串流。commentary 的 message 和每一次 `web_search_call`（search 的 query、open_page 的 url）都轉成 `StepEvent` 的 `detail`，讓 Side Panel 即時顯示 Muse 實際做了哪些事。

## 4. Responses + text.format（結構化輸出）
- `text: {format: {type: json_schema, name, strict, schema}}` 可以正常使用
- 輸出位置：`output[]` 裡 `type=="message"` 的那一項的 `content[0].text`，內容是 JSON 字串

## 5. 圖片理解
- `image_url` 如果是外部網址，Muse 會自己去下載，結果失敗了，錯誤是 `media_url_origin_error`
- **做法：** 後端自己下載圖片，轉成 `data:image/...;base64,` 再送給 Muse。這個方式實測可以，HTTP 200，約 3.7 秒
