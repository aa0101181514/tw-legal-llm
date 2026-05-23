# 常見問題

### 我需要付費的 Claude / Cursor 訂閱嗎?

你需要一份讓你的 AI 工具(Claude Desktop、Cursor 等)能呼叫 MCP 工具
的訂閱。TLR 本身不呼叫任何 LLM,生成的工作由你的 LLM 做。

### 能用 ChatGPT 嗎?

目前還不行。ChatGPT Plus 用戶將來可透過 Custom GPT Actions 整合,在
我們的開發路線上。現階段支援 Claude Desktop、Cursor、Cline 以及其他
相容 MCP 的用戶端。

### 為什麼搜尋結果沒有原始分數?

分數容易誤導且不易解讀。我們改回傳排名(rank)。

### 我可以不先搜尋就直接用 doc_id 取全文嗎?

不行。`get_judgment_fulltext` 必須帶上來自最近一次 `search_judgments`
回應的 `result_token`,這是為了防止大量抓取。

### 可以搜尋幾年以前的判決?

資料涵蓋臺灣司法判決多年累積。具體涵蓋範圍細節不對外公開。

### 資料是完整的嗎?

我們收錄公開可取得的臺灣司法判決。涵蓋範圍與更新時間不保證完整,已知
限制請參閱 [dr-lawbot.com](https://dr-lawbot.com)。

### AI 給我的答案在法律上正確嗎?

不一定。答案由你的 LLM 用戶端生成,不是由我們生成。我們保證引用正確,
但法律解讀仰賴你的 LLM(以及你自己)。重要引用請務必上 `dr-lawbot.com`
判決頁核對原文。

### 我收到 `quota_exceeded`,可以提高額度嗎?

可以,寄信給 `aa.0101181514@gmail.com`。

### 後端原始碼可以看嗎?

不可以。後端檢索流程閉源。本 repo 是用戶端開源,後端不開源。

### 可以自架嗎?

不可以。TLR 是雲端代管服務。本 repo 內的 MCP 用戶端只是把請求轉發到
`tlr.dr-lawbot.com`。
