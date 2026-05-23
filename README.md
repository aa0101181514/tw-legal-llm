# TW Legal LLM (TLL)

> 把臺灣判決搜尋接進你的 AI 工具。免費、附引用、用你自己的 LLM 訂閱。

`tw-legal-llm` 是一個 MCP(Model Context Protocol)用戶端,讓 Claude
Desktop、Cursor 與其他相容 MCP 的 AI 工具能搜尋並讀取臺灣司法判決。答案
由你自己的 AI(你的 Claude / Cursor 訂閱)生成,我們只負責提供判決內容
和引用。

- ✅ **無平臺綁定** — 支援 Claude、Cursor、Cline 或任何 MCP 用戶端。
- ✅ **自帶 LLM** — 使用你自己的 Claude Pro / Cursor 等訂閱,我們不收 LLM 費用。
- ✅ **引用可驗證** — 每筆結果包含完整法院案號與 dr-lawbot.com 判決連結。
- ✅ **存取稽核** — 後端遵循 ISO 42001 規範記錄存取日誌。
- ✅ **Apache 2.0** — 用戶端開源,安裝簡單。

## 安裝(Claude Desktop)

把下面這段貼進你的 `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tw-legal-llm": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/aa0101181514/tw-legal-llm",
        "tw-legal-llm"
      ],
      "env": {
        "TLL_API_KEY": "tll_xxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

重新啟動 Claude Desktop,Claude 就會看到兩個工具:
`search_judgments`、`get_judgment_fulltext`。

> 還沒有 API key?寄信給 Aaron `aa.0101181514@gmail.com`(早期試用階段
> 人工發放,還沒做註冊頁面)。

## 安裝(Cursor)

```json
{
  "mcpServers": {
    "tw-legal-llm": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/aa0101181514/tw-legal-llm",
        "tw-legal-llm"
      ],
      "env": {
        "TLL_API_KEY": "tll_xxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

## 工具能做什麼

完整介面請看 [`docs/tools-reference.md`](docs/tools-reference.md)。

簡單說:

- **`search_judgments`** — 用法律議題、關鍵字、案號、法院名稱或法條
  搜尋臺灣判決,回傳排序後的判決資訊與簡短摘錄。
- **`get_judgment_fulltext`** — 取得指定判決的可用內文,用於需要深入
  閱讀理由時。

## 運作方式

這個套件是一個輕量級的 MCP 用戶端。實際的檢索流程跑在
`tll.dr-lawbot.com` 伺服器上。後端不開源,因為價值在於資料品質與整理,
不在演算法本身。

**我們公開的**:

- 這個 MCP 用戶端。
- 工具介面契約(輸入、輸出、錯誤代碼)。
- 使用說明與設定範例。

**我們不公開的**:

- 後端檢索程式、排序方式、prompt 或門檻值。
- 額度與濫用偵測規則。
- 內部技術堆疊。

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

- GitHub Issues:https://github.com/aa0101181514/tw-legal-llm/issues
- Email(API key 申請、合作洽詢):`aa.0101181514@gmail.com`
