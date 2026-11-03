# 評測集校對表（data/eval/scam.jsonl，30 筆）

請改 `gold_label`（high / check / none）或 gold claim 的 verdict（refuted / supported / insufficient），直接在 jsonl 改或在這裡標註都可以。
split 依 event 切：tune 已用來調門檻，**test 要等你確認後才跑**。

| # | id | split | 來源類型 | gold | 內容（前 90 字） | gold 主張 → verdict | 備註 |
|---|---|---|---|---|---|---|---|
| 1 | case-mygopen-d6803af8 | test | known_case:investment | **high** | 張忠謀、黃仁勳免費贈書，掃碼加LINE好友即可免費領取限量好書。 | 張忠謀、黃仁勳免費贈書，掃碼加LINE好友即可免費領取限量好 → refuted | 查證確認這是詐騙集團冒用名人免費贈書廣告誘使民眾加LINE，再引導進入假投資群組騙取金錢。 |
| 2 | case-mygopen-007a9738 | test | known_case:investment | **high** | 聯電創辦人曹興誠近期拍攝影片宣傳扶曦計畫、天籟投資等新投資計畫，Yahoo新聞也有相關報導。 | 聯電創辦人曹興誠近期拍攝影片宣傳扶曦計畫、天籟投資等新投資計 → refuted | 該報導是網址為yalhooo.co的假冒Yahoo新聞一頁式詐騙網站，影片則是以深偽換臉及AI語音合成的假影片。 |
| 3 | case-tfc-377312f6-a6f | test | known_case:investment | **high** | 台灣銀行起訴蔡康永在電視直播節目中的言論，稱他在理科太太直播節目中表示自己透過加密貨幣致富。 | 台灣銀行起訴蔡康永在電視直播節目中的言論，稱他在理科太太直播 → refuted | 查核中心證實該頁面是假冒《聯合新聞網》的詐騙網站，所用擷圖出自2022年理科太太採訪蔡康永談幽默的影片，內容從未提及加密 |
| 4 | case-mygopen-383fb05d | test | known_case:impersonation | **high** | 你在IG抽獎活動中獲獎了，請先小額捐款給公益團體，並匯款支付額外費用或提供提款卡、銀行帳戶資料才能領獎。 | 你在IG抽獎活動中獲獎了，請先小額捐款給公益團體，並匯款支付 → refuted | 查核指出這是詐騙集團冒用社福團體在IG散布假抽獎訊息，藉中獎通知騙取匯款及個資。 |
| 5 | case-tfc-eda5cc83-253 | test | known_case:impersonation | **high** | 專業律師團、反詐騙組織幫你找回被詐騙的錢，協助追討受騙款項，請點進Messenger聊天室填寫表單諮詢。 | 專業律師團、反詐騙組織幫你找回被詐騙的錢，協助追討受騙款項， → refuted | 查核確認臉書上宣稱可幫忙討回詐騙款項的律師團、反詐組織廣告是二次詐騙，因其冒用合法律師事務所名義並藉機索取服務費與個資。 |
| 6 | case-mygopen-8e0a8811 | test | known_case:phishing | **high** | 在Google搜尋LINE，第一筆官方網站提供LINE網頁版登入，請掃描QRcode授權登入帳號。 | 在Google搜尋LINE，第一筆官方網站提供LINE網頁版 → refuted | 查核確認Google搜尋第一筆是詐騙集團投放關鍵字廣告的山寨LINE官網，會誘騙掃碼授權以盜用帳號。 |
| 7 | case-mygopen-855dee8d | test | known_case:phishing | **high** | 您使用先買後付購買了iPad mini即將扣款，您的在線商品訂單出現異常，請加入LINE客服處理，否則遲繳將上報聯徵中心。 | 您使用先買後付購買了iPad mini即將扣款，您的在線商品 → refuted | 查核指出該郵件是假冒Payoneer的釣魚詐騙，利用個資與扣款恐懼誘導加入假LINE客服以騙取轉帳。 |
| 8 | case-mygopen-afd1d03b | tune | known_case:phishing | **high** | 收到7-11賣貨便先收款後配送的實名認證網址，因沒有實名認證帳戶被凍結，請加入LINE客服帳號處理。 | 收到7-11賣貨便先收款後配送的實名認證網址，因沒有實名認證 → refuted | 查證確認網傳賣貨便連結與LINE客服均為假冒，係假客服釣魚詐騙手法，切勿填寫資料。 |
| 9 | case-tfc-87a729a1-78a | tune | known_case:shopping | **high** | 2024年新款智慧變焦老花眼鏡，100度-700度自動調節，不挑度數，不用驗光配度數均可配戴使用。 | 2024年新款智慧變焦老花眼鏡，100度-700度自動調節， → refuted | 事實查核中心認定為購物詐騙，因市面上並無可自動變焦的眼鏡且每人度數不同不可能共用，加上該網頁具一頁式詐騙特徵。 |
| 10 | case-tfc-f5d4f15c-131 | test | known_case:other | **high** | 求婚成功！只要在留言區送上祝福，就可以拿到668現金紅包，請私訊我的Instagram帳號領取。 | 求婚成功！只要在留言區送上祝福，就可以拿到668現金紅包，請 → refuted | 事實查核中心證實該貼文為詐騙，因其盜用圖庫求婚照片，並會引導用戶註冊、提供銀行帳戶及儲值才能領回雙倍金額。 |
| 11 | case-tfc-c3ea1c20-1ab | tune | known_case:impersonation | **high** | 健保卡使用異常通知，即將暫停所有健保服務，請加入健保署LINE客服進行諮詢。 | 健保卡使用異常通知，即將暫停所有健保服務，請加入健保署LIN → refuted | 查核確認此為假冒健保署的詐騙訊息，因健保署強調健保卡異常只會以書信公文通知，絕不會用LINE、電話或簡訊通知。 |
| 12 | case-mygopen-19fff196 | tune | known_case:shopping | **high** | 在Facebook上看到便宜掃地機，只要先匯200元運費，並到物流網站填寫資料、加入LINE物流客服簽署金流協議即可出貨。 | 在Facebook上看到便宜掃地機，只要先匯200元運費，並 → refuted | 查證確認此為典型的Facebook假買賣結合假物流網站詐騙，目的是騙取轉帳匯款，呼籲勿在社群平台交易並立即向165或警方 |
| 13 | th-job14 | tune | in_the_wild:fake_job | **high** | 🔥徵台灣掛播主播｜輕鬆兼職 ✅工作內容：僅需人在鏡頭內，直播時可以吃飯、追劇、看電視，偶爾互動 ✅時數要求：一個月累計滿5天，每天2小時即可，一共10小時，時段自由安排，不用固定排 | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 14 | th-job34 | test | in_the_wild:fake_job | **high** | 【雙崗位誠徵 正職+遠端兼職】 ✅ 正職月薪：37000-47900隨機核定，常見39100、39750水準，絕不事後砍薪 ✅ 正職工作內容：協助新北蘆洲傳統油飯店幫忙包裝剛蒸好的 | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 15 | th-job45 | test | in_the_wild:fake_job | **high** | 【雙崗位誠徵 正職+遠端兼職】 ✅ 正職月薪：37100-48200隨機核定，常見39300、39900水準，絕不事後砍薪 ✅ 正職工作內容：協助古早味純手工麵線廠幫忙擺放麵線風乾 | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 16 | th-job54 | tune | in_the_wild:fake_job | **high** | 😤 騎機車買泡麵回來，邊回訂單邊煮 回完訊息回頭看，泡麵直接煮成鍋巴粘在鍋底 我氣到差點把泡麵往機車籃子裡丟，趕快徵小幫手！ 客服小幫手 正職42200+提成 兼職282/時+提成 | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 17 | th-job55 | tune | in_the_wild:fake_job | **high** | 現在後台的訊息量多到滑三頁都滑不完🙂
 我們全體同事開會討論半小時，決定趕緊補新的遠端人力
 工作就回覆加購合併出貨的問題，超輕鬆
 正職38650/月，兼職一小時290，全程不用 | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 18 | th-job64 | test | in_the_wild:fake_job | **high** | ��不好意思打擾一下🙏 缺人比缺錢還嚴重，真心想找一個能一起打拼的你。 【職缺名稱】：線上訂單協助員  【工作內容】：接單 操作訂單 完成訂單 長輩也能輕鬆操作  【兼職薪資】：2 | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 19 | th-job67 | tune | in_the_wild:fake_job | **high** | 我自己本身也做過行政工作，同時也是個愛到處走走的人，超懂很多人想找一份時間彈性、能好好兼顧生活的工作，這份崗位完全踩中所有需求點✨ 📌 崗位：日韓行政 📝 工作內容：回覆客戶訊息、 | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 20 | th-job92 | tune | in_the_wild:fake_job | **high** | 現在徵人真的難到離譜，明明遠端上班、福利給滿，還是遲遲等不到合拍的新夥伴🥺 ✨ 職缺：訂單管理 ✨ 工作內容：把每一筆訂單從下單到出貨全流程追好、及時回覆客戶訊息，全程不用跑外勤， | 遠端/居家兼職，高時薪、私訊即可應徵（未具名公司） → insufficient | Threads 假求職範本（高薪、免經驗、居家、私訊、無公司名）. src https://www.threads.co |
| 21 | neg-neg16515 | test | hard_negative | **none** | 🚨【防詐重要提醒】 近期詐騙手法持續翻新，不肖人士可能透過簡訊、Email、社群訊息或不明網頁連結，誘導民眾下載「惡意軟體」，並藉此竊取帳號密碼、OTP 驗證碼或其他重要資訊，進而 | — | 街口支付防詐提醒. src https://www.facebook.com/100064570364735/posts |
| 22 | neg-neg16516 | tune | hard_negative | **none** | 【Q寶反詐騙】只是想算個命，也有詐騙？ 「大師，我最近運勢好差……」 「施主小心！你卡到冤親債主，不處理恐有大劫！」😱 算命本想求心安 小心！心還沒安到，存款先被清空！ 快來看看「 | — | 中華電信反詐宣導. src https://www.facebook.com/100064603817373/posts |
| 23 | neg-neg1656 | test | hard_negative | **none** | 【 西堤牛排貼心小叮嚀 💬 】 為了讓大家每次的相聚都安心又愉快， 請跟我們一起留意幾個重點，共同守護您的消費安全： ⚠️ 要小心｜ 勿向社群平台或來路不明的賣家購買餐券 ❌ 不提 | — | 西堤牛排防詐小叮嚀. src https://www.facebook.com/100068115459465/post |
| 24 | neg-promo0 | test | hard_negative | **none** | 🔰2026年週年慶【滿額加碼登記抽精美好禮】｜中獎通知 狂賀🎉🎉 【TM261005WA015F 陳X宏】 恭喜得獎者可以獲得精美好禮 阿媽牌獨家夢幻逸品🎊堅持鐵鏟🎊 阿媽將會發簡 | — | 品牌週年慶中獎通知（含加LINE）— 最難負例. src https://www.facebook.com/100064 |
| 25 | neg-cs1 | tune | hard_negative | **none** | #得獎名單公布 【森友總動員-抽萬元寵點數】幸運得主出爐🎉 🎊 恭喜以下得獎者： 鬱璇 黃凡甄 ⚠️ 兌獎重要事項（請注意期限）： 請在 2026/11/8 以前私訊粉專提供以下資 | — | 東森寵物得獎名單（私訊粉專領獎）— 難負例. src https://www.facebook.com/10005746 |
| 26 | neg-promo5 | test | hard_negative | **none** | 🔥【雙11醫美保養限時優惠】✨ 💖 指定醫美滿 $999 折 $100！ 🎁 滿 $1,200 再送拭拭樂酒精擦拭巾 10 抽 × 3 包！ 📅 活動期間：11/1-11/10 🛍 | — | 藥局雙11優惠. src https://www.facebook.com/100064536708077/posts/ |
| 27 | neg-cs9 | tune | hard_negative | **none** | 【新店開幕】11/07林口文化二店 林口文化二店即將在11/07(六) 10:00盛大開幕囉！ ✦開幕期間好康大放送✦ 【11/07 (六)11：00】 消費滿額發票加$50現金抽 | — | 寶雅新店開幕抽獎. src https://www.facebook.com/100064445239922/posts |
| 28 | neg-job51 | test | hard_negative | **none** | 📢 【桃園楊梅｜單日高薪兼職🔥】徵 5 名！ 💰 時薪 $220～230｜當日最高 $1,840！ 🍱 免費提供午餐｜工作簡單易上手 想找短期打工、不想被長期排班綁住嗎？ 只要一天 | — | 有路段、現場工時與工作內容的短期打工，未見明確詐術. src https://www.threads.com/@j.s.3_11/post/DfB5Z |
| 29 | neg-job70 | tune | hard_negative | **none** | 🌟景美藥局徵求工讀生🌟 ​📍景文街125號 近世新大學 & 景美夜市，交通方便  ​📝 工作內容：  ​協助整理藥品、貨架管理、行政作業、顧客服務等  ​輕鬆的工作環境，適合學生兼 | — | 景美藥局徵工讀生. src https://www.threads.com/@wvvc.c/post/DeW445Ums |
| 30 | neg-job11 | tune | hard_negative | **none** | 「Threads看到便宜貨、追星小物或高薪徵才，先別急著心動！詐騙最愛用誘餌騙你上鉤，記得先查證、別匯款、別亂點連結！」 #臺北市政府警察局關心您 #臺北市政府勞動局協助宣導 | — | 北市勞動局防詐宣導. src https://www.facebook.com/100064902151937/post |


## 校對紀錄

2026-11-02 由 Codex（gpt-6-astra）獨立校對，報告見 `codex_review.md`。採納：th-job14 的 gold claim 改寫成貼文實際承諾；neg-job51 備註改成不過度斷言。維持原標：case-tfc-377312f6-a6f 維持 high（假新聞式名人加密貨幣致富是投資詐騙的典型誘餌；Codex 信心 low）；th-job14 維持 high（掛播兼職、私訊、無公司名是已知範本）；neg-promo0、neg-cs1 維持 none。job34/job45 同模板同在 test，結果另列按 event 去重的數字。
