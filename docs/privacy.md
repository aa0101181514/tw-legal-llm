# 隱私說明

## 我們記錄什麼

當你使用 `tw-legal-rag` 時,後端會記錄以下資料:

- API key 的 id(不是 key 本身)。
- 呼叫的工具名稱(`search_judgments` / `get_judgment_fulltext`)。
- 你查詢字串的 **SHA-256 雜湊值**(不會記錄查詢原文)。
- 全文讀取請求的 `doc_id`。
- 回應狀態、延遲與結果數量。
- 時間戳記。

這些資料用於存取稽核、濫用偵測,以及符合 ISO 42001 的存取控管。

## 我們不記錄什麼

- 查詢字串原文。
- 你 AI 工具裡的 prompt、對話內容、AI 生成的答案。
- 任何 LLM(Claude / Cursor 等)回給你的內容。

LLM 端的對話只在你和你的 LLM 服務之間,我們完全看不到。

## 引用連結

`citation_url` 指向 `dr-lawbot.com/fullview/<doc_id>`,該頁公開渲染
判決原文。這也是我們發布到 SEO / GEO 表面上,讓 Google / ChatGPT /
Perplexity 收錄的同一個 URL。

## 資料保存

API 請求日誌會保留供營運使用。我們不販售、不分享、不重新用途化日誌。

## 聯絡

隱私問題、或需刪除你 API key 相關日誌,請寄信
`aa.0101181514@gmail.com`。
