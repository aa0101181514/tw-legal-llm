# 常見問題

### 要付費嗎?需要 API key 嗎?

判決檢索服務本身免費、免註冊、不需 API key。你只需要一個能連線到本服務的
AI 工具(Claude、ChatGPT 等),最終答案由你的 AI 生成,我們不收 AI 使用費。

### 怎麼在 Claude Desktop 用?

Customize → Connectors → **+** → Add custom connector,URL 填
`https://tlr.dr-lawbot.com/mcp`,OAuth 欄位留空。詳見 [README](../README.md)。

### 怎麼在 ChatGPT 用?

透過「法律偵探」自訂 GPT(上架審核中)。進階使用者可自建 Custom GPT,
在 Actions 匯入 `https://tlr.dr-lawbot.com/openapi.yaml`,認證選 None。

### 我可以不先搜尋就直接用 doc_id 取全文嗎?

不行。讀取判決內文必須帶上來自最近一次搜尋回應的 `result_token`。

### 可以搜尋幾年以前的判決?

資料涵蓋臺灣司法判決多年累積。具體涵蓋範圍細節不對外公開。

### 資料是完整的嗎?

我們收錄公開可取得的臺灣司法判決。涵蓋範圍與更新時間不保證完整,已知限制
請參閱 [dr-lawbot.com](https://dr-lawbot.com)。

### AI 給我的答案在法律上正確嗎?

不一定。答案由你的 AI 生成,不是由我們生成。我們保證引用正確,但法律解讀
仰賴你的 AI(以及你自己)。重要引用請務必上 `dr-lawbot.com` 判決頁核對原文。

### 服務會不會突然不能用?

本服務為免費公開服務,可能因維護或流量保護而暫時限流,稍後重試即可。

### 後端原始碼可以看嗎?

不可以。後端檢索流程閉源,價值在判決資料的品質與整理。本 repo 只公開
使用說明、介面契約與 OpenAPI schema。

### 可以自架嗎?

不可以。TLR 是雲端代管服務,連線到 `tlr.dr-lawbot.com`。
