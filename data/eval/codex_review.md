# Gold label 獨立校對

依 `scam.jsonl` 全文與 note 審閱全部 30 列、20 個 claims，並核對 `REVIEW.md` 的 id、split、kind、label、verdict，兩檔一致。只使用提供的文字與備註，未開啟來源網站、未執行評測；以下信心指本列建議的信心，並非來源帳號真實性的認證。

12 個 known_case 的 `refuted` 均與 note 所述查核結論一致，可依這次提供的證據保留；這不代表已獨立重查那些查核來源。`case-tfc-377312f6-a6f` 的疑義在分類輸入與產品範圍，不在 claim 的真假。

8 個 th-job 的 `insufficient` 作為「該職缺確實存在、實際會按所述條件給薪」的預期結果合理；無具名雇主與可核對職缺，note 也未提供個案反證，因此不應改成 `refuted`。但現有共用 claim 是徵才特徵摘要，應明確按上述實質招募承諾解讀，不能把「貼文確實寫了某待遇」與「待遇真實」混為一談；未做搜尋，也不能保證網路一定找不到正反證據。

除下表的 job14 邊界外，job34、job45、job54、job55、job64、job67、job92 的 `high` 均符合題定的風險標準：簡單居家工作、誘人的待遇或福利、私訊／LINE 招募，且缺乏可識別雇主與完整工作地址。這是 scam-like 的產品分類，不能據此宣稱七個職缺已被證實為詐騙。各列不必同時具備所有特徵；例如 job54、job55、job92 未明寫免經驗，不能把共用 note 當成額外貼文證據。

| id | current label/verdict | your suggestion | one-line reason | confidence |
|---|---|---|---|---|
| case-tfc-377312f6-a6f | high / refuted | 以現有 post 建議 none / refuted；若要保留 high，應另補能顯示詐騙招攬的原始輸入 | post 只有銀行提告與名人致富的新聞式敘述，未呈現 note 才有的假新聞網站或投資入口，依「貼文本身顯示詐術、新聞不在範圍」的規則有標籤與輸入不一致風險。 | low |
| th-job14 | high / insufficient | high 暫列人工重審邊界；insufficient 保留，但 claim 應改述實際掛播職務與給薪承諾 | 每月 10 小時給 3,000 元，工作與時數具體；低門檻及私訊可疑但不足單獨坐實假職缺，且 post 未明言遠端／居家，共用 claim 與 note 加入了未明示條件。 | low |
| neg-promo0 | none / 無 claims | 暫留 none / 無 claims；作為確定負例前需有來源與 LINE 帳號歸屬的確認 | 指定中獎編號、遮罩姓名與品牌實物獎品支持正常活動解讀，但簡訊導向 LINE 加資料流程仍有仿冒可能，note 只是稱它為品牌活動，未提供身分確認。 | low |
| neg-cs1 | none / 無 claims | 暫留 none / 無 claims；保留粉專身分尚未獨立核實的限制 | 具名得獎者、原粉專私訊與會員點數兌獎相符，姓名／會員卡號及期限本身不足判 high，但帳號名稱和 note 不能單獨證明官方身分。 | low |
| neg-job51 | none / 無 claims | 保留 none / 無 claims；note 的「具地址的正當」宜改成「有路段、現場工時與工作內容，未見明確詐術」 | 8 小時乘時薪 230 元與最高日薪 1,840 元相符、現場盤點具體；但只列路段而無門牌或雇主名稱，不能把它描述成已確認正當的完整地址職缺。 | high |

## Split leakage

- 共 14 列 tune、16 列 test；沒有相同 `event_id` 跨 split，也沒有原文或經大小寫、數字、空白及標點正規化後的完全重複貼文。逐對比較並人工檢視，未發現可確認的跨 split 近重複或同一文案模板；這個結論限於本次 30 列。
- **job34／job45 共用 `job-dual-template` 正確（high confidence）**：相同雙職位標題、欄位順序、隨機核薪及常見薪額寫法、居家兼職、現金給薪、鄰居同事與一對一教學，只替換行業、地點和數字；兩列都在 test，沒有跨 split 洩漏，但不是兩個獨立模板，宜補看按 event 計分的結果，避免重複加權。此分組只代表同模板，不證明同一雇主或同一詐騙集團。
- **有跨 split 的語意家族重疊，但不足認定同模板**：test 的 job64 與 tune 的 job54／job55／job67／job92 都是居家訂單／客服加私訊招募；test 的 job34／job45 也含此類兼職誘因。test 的 `case-mygopen-855dee8d` 與 tune 的 `case-mygopen-afd1d03b`、`case-tfc-c3ea1c20-1ab` 共用異常／停用威脅加 LINE 假客服套路，但不同事件和句型。若測試目標是未見過的詐術家族，現有切分不足；若只是未見過的事件，不能僅因套路相同判定洩漏。
- 8 個 th-job 共用完全相同的 gold claim 文字，且跨 tune／test；這是標註模板重用，不能直接當作 post 洩漏，但若 tune 曾用來調 claim 擷取規則，test 的 claim 分數不代表對新主張形式的泛化。`REVIEW.md` 已記載 tune 用過，若後續要改成按家族分組，應補充未參與調整的新 test 事件，不應將已用過的 tune 列移入 test 當作未見資料。

All other rows: agree
