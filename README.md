# TW Legal RAG (TLR)

> 把臺灣判決搜尋接進你的 AI 工具。免費、附引用、用你自己的 LLM 訂閱。

`tw-legal-rag` 是一個 MCP(Model Context Protocol)用戶端,讓 Claude
Desktop、Cursor 與其他相容 MCP 的 AI 工具能搜尋並讀取臺灣司法判決。答案
由你自己的 AI(你的 Claude / Cursor 訂閱)生成,我們只負責提供判決內容
和引用。

- ✅ **無平臺綁定** — 支援 Claude、Cursor、Cline 或任何 MCP 用戶端。
- ✅ **自帶 LLM** — 使用你自己的 Claude Pro / Cursor 等訂閱,我們不收 LLM 費用。
- ✅ **引用可驗證** — 每筆結果包含完整法院案號與 dr-lawbot.com 判決連結。
- ✅ **存取稽核** — 後端遵循 ISO 42001 規範記錄存取日誌。
- ✅ **Apache 2.0** — 用戶端開源,安裝簡單。

## 申請存取(Closed Beta)

目前 TLR 處於 Closed Beta 階段,沒有自助註冊頁面。請寄信申請早期試用 API key:

📧 **aa.0101181514@gmail.com**

信件請附:
- 你的姓名 / 律所或單位
- 用途簡述(例如:律師日常判決查詢、法律研究、學術)
- 你會用哪個 AI 工具(Claude Desktop / Cursor / Cline / 其他)

申請通常 1-3 個工作天內回覆並提供 API key。

## 安裝(Claude Desktop)

把下面這段貼進你的 `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tw-legal-rag": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/aa0101181514/tw-legal-rag",
        "tw-legal-rag"
      ],
      "env": {
        "TLR_API_KEY": "tlr_<請貼上你拿到的 API key>"
      }
    }
  }
}
```

設定檔位置:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

貼完後**完整關閉再重新啟動 Claude Desktop**(不是只關視窗,Mac 要按 `Cmd+Q`)。
Claude 會看到兩個工具:`search_judgments`、`get_judgment_fulltext`。

## 安裝(Cursor)

Cursor 設定檔 `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tw-legal-rag": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/aa0101181514/tw-legal-rag",
        "tw-legal-rag"
      ],
      "env": {
        "TLR_API_KEY": "tlr_<請貼上你拿到的 API key>"
      }
    }
  }
}
```

## 試用第一句指令

打開 Claude Desktop,問:

> 幫我搜尋離婚剩餘財產分配的相關判決,並引用 3 個案號。

Claude 會自動呼叫 `search_judgments`,回給你判決清單與引用連結。

## 工具能做什麼

完整介面請看 [`docs/tools-reference.md`](docs/tools-reference.md)。

簡單說:

- **`search_judgments`** — 用法律議題、關鍵字、案號、法院名稱或法條
  搜尋臺灣判決,回傳排序後的判決資訊與簡短摘錄。
- **`get_judgment_fulltext`** — 取得指定判決的可用內文,用於需要深入
  閱讀理由時。

## 運作方式

這個套件是一個輕量級的 MCP 用戶端。實際的檢索流程跑在
`tlr.dr-lawbot.com` 伺服器上。後端不開源,因為價值在於資料品質與整理,
不在演算法本身。

**我們公開的**:

- 這個 MCP 用戶端。
- 工具介面契約(輸入、輸出、錯誤代碼)。
- 使用說明與設定範例。

**我們不公開的**:

- 後端檢索程式、排序方式、prompt 或門檻值。
- 額度與濫用偵測規則。
- 內部技術堆疊。

## 常見問題與排錯

### 問題:Claude Desktop 看不到 TLR 工具

依序檢查:

1. **設定檔路徑對嗎?**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - 用 `cat` / 記事本打開確認檔案內容真的有 `tw-legal-rag` 區塊。

2. **JSON 語法錯了嗎?**
   - 逗號 / 引號 / 大括號漏掉是最常見錯誤。
   - 用 https://jsonlint.com 貼進去檢查。

3. **完整重啟 Claude Desktop 了嗎?**
   - Mac: 直接關閉視窗**不夠**,要 `Cmd+Q` 或從選單列「Claude → 結束」。
   - Windows: 從系統匣右鍵 Claude → Quit。

4. **uvx 裝好了嗎?**
   - 開 terminal 輸入 `uvx --version`。
   - 如果沒有: `curl -LsSf https://astral.sh/uv/install.sh | sh`(macOS/Linux)
     或 `winget install astral-sh.uv`(Windows)。

5. **看 Claude Desktop 內部日誌**
   - macOS: `~/Library/Logs/Claude/mcp*.log`
   - 搜尋關鍵字 `tw-legal-rag` 看 stderr 訊息。

### 錯誤:`unauthorized`

- API key 沒貼對。檢查 `env.TLR_API_KEY` 是否完整(包含 `tlr_` 前綴)。
- 你的 key 已被撤銷,寫信給我們(aa.0101181514@gmail.com)申請新的。

### 錯誤:`quota_exceeded`

- 你今天的免費額度已用完,明天 0 點(臺北時間)重置。
- 需要更高額度,寫信申請。

### 錯誤:`fulltext_not_available`

- 取全文必須先 `search_judgments`,再用搜尋結果裡的 `result_token` 呼叫
  `get_judgment_fulltext`。
- Token 短效(15 分鐘),過久就要重新搜尋。
- 如果 Claude 跳過搜尋直接想取全文,試著明確告訴它「請先搜尋再讀全文」。

### 錯誤:`tw-legal-rag: TLR_API_KEY is not set`

- 設定檔的 `env` 區塊忘了寫 `TLR_API_KEY`,或字串輸錯。

### 其他問題

- GitHub Issues: https://github.com/aa0101181514/tw-legal-rag/issues
- Email: `aa.0101181514@gmail.com`

## 限制說明

- 免費額度每日有上限,超過時會收到不透明的「額度已達上限」訊息。
- 部分判決可能沒有完整內文可讀取。
- 最終回答由 LLM(Claude、Cursor 等)生成。我們保證引用正確性,答案
  品質取決於你用的 LLM。

## 隱私

你的查詢內容會以 SHA-256 雜湊形式記錄在我們的後端供稽核與濫用偵測使用,
**不會記錄原文**。詳見 [`docs/privacy.md`](docs/privacy.md)。

## 授權

Apache 2.0。請見 [LICENSE](LICENSE)。

## 聯絡方式

- GitHub Issues:https://github.com/aa0101181514/tw-legal-rag/issues
- Email(API key 申請、合作洽詢):`aa.0101181514@gmail.com`
