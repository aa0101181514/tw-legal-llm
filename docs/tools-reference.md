# 工具介面參考

TLR MCP 用戶端公開兩個工具,以下是公開介面契約,不含實作細節,也不對外
保證任何實作層 API。

## `search_judgments`

用法律議題、關鍵字、案號、法院名稱或法條搜尋臺灣判決,回傳排序後的判決
資訊與簡短摘錄。

**不可引用本工具沒回傳的判決。**

### 輸入

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `query` | string | 是 | 繁體中文搜尋字串。 |
| `search_type` | enum [`hybrid`, `keyword`, `phrase`] | 否 | 預設 `hybrid`。 |
| `max_results` | integer (1-20) | 否 | 預設 10。 |

### 輸出

```json
{
  "results": [
    {
      "rank": 1,
      "doc_id": "TPHV,106,家抗,96,20171024,1",
      "citation_text": "臺灣高等法院 106 年度家抗字第 96 號",
      "court_name": "臺灣高等法院",
      "jdate": "2017-10-24",
      "case_category": "民事",
      "snippet": "...",
      "citation_url": "https://dr-lawbot.com/fullview/TPHV,106,家抗,96,20171024,1",
      "result_token": "<短效驗證碼>"
    }
  ]
}
```

注意事項:

- 呼叫 `get_judgment_fulltext` 時必須帶上 `result_token`,此 token
  有時效性,請勿長期保存。
- 不回傳原始排序分數。
- 摘錄是供引用識別用,不是完整閱讀內容。

### 錯誤

| 錯誤代碼 | 意義 |
|---|---|
| `unauthorized` | API key 缺少或無效。 |
| `quota_exceeded` | 當日搜尋額度已達上限。 |
| `invalid_request` | 請求格式不符。 |
| `internal_error` | 後端錯誤,請稍後重試。 |

---

## `get_judgment_fulltext`

取得指定判決的可用內文,僅在搜尋結果摘錄不足以做法律分析時使用。

**引用文字必須與 `search_judgments` 回傳的 `citation_text` 完全一致。**

### 輸入

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `doc_id` | string | 是 | 來自最近一次 `search_judgments` 回傳的 doc_id。 |
| `result_token` | string | 是 | 來自包含此 doc_id 的 search 回應。 |

### 輸出

```json
{
  "doc_id": "TPHV,106,家抗,96,20171024,1",
  "citation_text": "臺灣高等法院 106 年度家抗字第 96 號",
  "court_name": "臺灣高等法院",
  "jdate": "2017-10-24",
  "text_excerpt": "...",
  "cited_articles": ["民法第 1030-1 條"],
  "citation_url": "https://dr-lawbot.com/fullview/TPHV,106,家抗,96,20171024,1"
}
```

注意事項:

- 內文有可用節錄上限,不一定是完整判決原文。
- `cited_articles` 是該判決引用的法條列表(可萃取者)。

### 錯誤

| 錯誤代碼 | 意義 |
|---|---|
| `unauthorized` | API key 缺少或無效。 |
| `fulltext_not_available` | 請先執行 `search_judgments`,並沿用其 `result_token`。 |
| `token_expired` | `result_token` 已過期,請重新搜尋。 |
| `quota_exceeded` | 當日全文讀取額度已達上限。 |
| `internal_error` | 後端錯誤,請稍後重試。 |

---

## 給 AI 用戶端的使用指引

不論你用的是 Claude、Cursor 或其他 MCP 工具,請遵守以下原則:

1. **回答前一定先呼叫 `search_judgments`**。如果結果為空,請明說沒有找
   到,不可虛構引用。
2. **引用要用 `citation_text` 原文**。不可改寫法院名稱或案號。
3. **只在搜尋摘錄不足以滿足使用者要求時**才呼叫
   `get_judgment_fulltext`。
4. **答案中要清楚區分「搜尋結果摘要」與「全文理由分析」**。
5. **不可發明案號、法院名稱或法條** — 凡是工具回傳沒出現過的東西,都不
   可寫入答案。
