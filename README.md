# TW Legal RAG (TLR)

> 把臺灣判決搜尋接進你的 AI 工具。免費、附引用、用你自己的 AI。

TLR 是「法律偵探」(dr-lawbot.com)提供的判決檢索服務,讓 Claude、ChatGPT
與其他相容工具能搜尋並引用臺灣司法判決。答案由你自己的 AI 生成,我們只負責
提供判決內容與可驗證的引用連結。

- ✅ **免費、免註冊** — 不需申請、不需 API key,貼一個網址就能用。
- ✅ **自帶 AI** — 用你自己的 Claude / ChatGPT,我們不收 AI 使用費。
- ✅ **引用可驗證** — 每筆結果都附完整法院案號與 dr-lawbot.com 判決連結。
- ✅ **存取稽核** — 後端遵循 ISO 42001 規範記錄存取日誌。

服務網址(Remote MCP / API):

```
https://tlr.dr-lawbot.com
```

---

## 安裝(Claude Desktop)

1. 打開 Claude Desktop → 左上選單 **Customize** → **Connectors**。
2. 點右上角 **+** → **Add custom connector**。
3. 填入:
   - **Name**:`法律偵探`(或任何你喜歡的名稱)
   - **Remote MCP server URL**:`https://tlr.dr-lawbot.com/mcp`
4. 按 **Add**。完成,不需要填 OAuth、不需要 API key。

之後在對話框問:

> 幫我搜尋離婚剩餘財產分配的相關判決,並引用 3 個案號。

Claude 會自動呼叫判決搜尋,回給你判決清單與引用連結。

---

## 安裝(ChatGPT)

ChatGPT 端透過「法律偵探」自訂 GPT 使用,搜尋即可:

> 在 ChatGPT 的「探索 GPT」搜尋「法律偵探」

(GPT 上架審核中;上架後此處補連結。)

進階使用者也可自行建立 Custom GPT,在 Actions 匯入下方 OpenAPI schema:

```
https://tlr.dr-lawbot.com/openapi.yaml
```

Action 認證選 **None**(本服務免認證)。公開 GPT 需設定 Privacy Policy
URL,可直接填:`https://dr-lawbot.com/tlr-privacy`。

---

## 能做什麼

- **搜尋判決** — 用法律議題、關鍵字、案號、法院名稱或法條搜尋臺灣判決,
  回傳判決資訊與簡短摘錄。
- **讀取判決內文** — 取得指定判決的可用內文,用於需要深入閱讀理由時。

完整介面契約請看 [`docs/tools-reference.md`](docs/tools-reference.md)。

---

## 試用第一句指令

> 幫我找近年酒駕公共危險罪的量刑判決,列出 3 個案號和判決連結。

---

## 運作方式

實際的檢索流程跑在 `tlr.dr-lawbot.com` 伺服器上。後端不開源,因為價值在於
判決資料的品質與整理,不在演算法本身。

**我們公開的**:

- 工具介面契約(輸入、輸出、錯誤代碼)。
- OpenAPI schema(供 ChatGPT Action 使用)。
- 使用說明與設定範例。

**我們不公開的**:

- 後端檢索程式、排序方式與內部技術堆疊。

---

## 常見問題與排錯

### Claude Desktop 看不到工具

- 確認 URL 填的是 `https://tlr.dr-lawbot.com/mcp`(結尾有 `/mcp`)。
- 確認 OAuth 欄位**留空**(本服務免認證)。
- 完整重啟 Claude Desktop:Mac 按 `Cmd+Q`,Windows 從系統匣 Quit。

### 搜尋沒有結果

- 換個說法或關鍵字再試。
- 我們的判決庫持續擴充,部分冷門領域資料可能尚未涵蓋。

### 服務暫時無法使用

- 後端可能正在維護或限流,稍後重試。

### 其他問題

- GitHub Issues:https://github.com/aa0101181514/tw-legal-rag/issues
- Email:`aa.0101181514@gmail.com`

---

## 限制說明

- 部分判決可能沒有完整內文可讀取。
- 最終回答由你的 AI(Claude、ChatGPT 等)生成;我們保證引用正確性,
  答案品質取決於你用的 AI。
- 本服務為免費公開服務,可能因維護或流量保護而暫時限流。

---

## 隱私

為持續改善判決檢索品質,本服務會記錄查詢內容,**不含可識別個人身分的資訊,
且不會用於訓練生成式 AI 模型**。詳見 [`docs/privacy.md`](docs/privacy.md)。

---

## 授權

文件與介面契約以 Apache 2.0 釋出。請見 [LICENSE](LICENSE)。

## 聯絡方式

- GitHub Issues:https://github.com/aa0101181514/tw-legal-rag/issues
- Email(合作洽詢):`aa.0101181514@gmail.com`
