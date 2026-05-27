# Taiwan Legal RAG (`twlegalrag`)

> Open-source CLI for **semantic** Taiwan legal judgment retrieval, powered by
> Legal Detective's 22M-judgment retrieval infrastructure.

Taiwan Legal RAG CLI retrieves Taiwan court judgments from Legal Detective's
public TLR endpoint and packages them for use with **your own AI tools**. It
does **not** generate legal advice, does **not** call any LLM, and does **not**
guarantee semantic faithfulness of third-party model outputs. Its built-in
citation check only verifies whether cited judgments belong to the retrieved
bundle.

繁中：Taiwan Legal RAG CLI 是一個開源命令列工具,連接法律偵探建置的 2,200 萬筆
台灣裁判語義檢索服務,讓你能用自然語言搜尋判決,並將檢索結果帶入自己的 AI 工具使用。

## 為什麼不一樣

這不是一般關鍵字判決搜尋工具。背後連到的是法律偵探長期建置的 TLR 檢索服務：

- 約 **2,200 萬筆**台灣裁判資料,經過結構化處理與向量化。
- 經過上千小時的 retrieval pipeline optimization。
- 支援**語義模糊搜尋**——不是只靠案號、法院、關鍵字,能用自然語言查找
  「概念相近但用詞不同」的判決。
- 開源 CLI 本身**不內建判決庫**,也不暴露後端模型權重或向量索引;它是連接公開
  TLR retrieval endpoint 的工具。

> Unlike keyword-only legal search tools, Taiwan Legal RAG CLI connects to a
> production semantic retrieval backend built on 22M+ Taiwan court judgments,
> enabling fuzzy concept-level search while keeping model weights, infrastructure,
> and private indexes server-side.

（措辭說明：開源的是 **CLI**,不是模型或向量庫;後端的檢索服務、模型權重、私有
索引都留在伺服器端,不隨本工具公開。）

## 它做什麼 / 不做什麼

**做**：用自然語言檢索判決 → 取得結構化清單、判決全文片段(excerpt)、引用連結 →
打包成 bundle 交給你自己的 AI;並可對 AI 產生的答案做 bundle 層級的引用檢查。

**不做**：本工具**不呼叫任何 LLM、不生成法律意見、不背書**任何模型輸出。答案要由
你自己選的 AI(ChatGPT / Claude / Gemini / 本地模型)生成。

### 內建的 citation check 能檢查什麼

`check` 是 **bundle 層級、盡力而為**的字串檢查,只驗：

- 答案引用的判決字號**是否在 bundle 內**(抓「引用了不在 bundle 的字號」= 疑似捏造);
- 是否引用 bundle 外、或不存在的判決;
- **引文存在性(bundle 層級)**:答案宣稱「法院說……」的逐字句,是否出現在 bundle
  文字的**某處**。

### 它**不能**檢查什麼（重要）

- 引文是否出自**答案所指的那一篇**判決(存在性檢查只看「整個 bundle 裡有沒有這句」,
  不綁定到特定判決);
- 法院見解是否**讀對**;
- 是否把**當事人主張**(原告/被告/上訴人)當成**法院見解**;
- 是否把**附帶論述**當成判決**核心權威**;
- paraphrase(改寫)型的見解幻覺。

這些都需要閱讀判決全文才能判斷——這也是為什麼 bundle 內附上判決全文片段與
verification instructions,要求下游模型自行核對。**`pass` 只代表「引用的字號身份對得上
bundle」,不代表「法律推論正確」或「引文確實出自那篇」。** 另外,`check` 只比對
**bundle 內的內容**,不是整個法律偵探資料庫——若你事後自己開判決全文再改寫答案,
`check` 仍只看 bundle 當初打包的片段。

## 安裝

```bash
pip install twlegalrag
```

只依賴 `httpx` / `typer` / `rich`。不需要任何 LLM 套件或金鑰——本工具不呼叫 LLM。

## 使用

```bash
# 1) 純檢索 — 列出符合的判決
twlegalrag search "勞資 加班費" -n 5 --read

# 2) 打包 — 產生可交給任何 AI 的 bundle ★主流程
twlegalrag pack "車禍對方全責,我可以求償什麼?" -o bundle.json
#   → 把 bundle.json 貼給 ChatGPT / Claude / Gemini,要求它只引用 bundle 內的判決

# 3) 引用檢查 — 對任何 AI 產生的答案做 bundle 層級檢查
twlegalrag check bundle.json answer.txt

# 服務是否正常
twlegalrag health
```

`pack` 產生的 bundle 包含 `query`、每筆判決的 `citation_id`(J1, J2, ...)、
`citation_text`、`citation_url`、`doc_id`、Layer-1 listing、`fulltext_excerpt`
(判決理由的擷取片段,有長度上限)、`allowed_citations`,以及一段
`verification_instructions`,明確要求下游模型只引用 bundle 內判決、把不支持的命題標為
unverified。stderr 也會印一段 AI USE NOTICE。

## 設定(選用)

預設打公開端點 `https://tlr.dr-lawbot.com`,免金鑰即可使用。若服務方發給你 API key,
可放環境變數或 `~/.twlegalrag/config.toml`(已 git-ignore,**切勿** commit)：

```bash
export TWLEGALRAG_TLR_BASE_URL=https://tlr.dr-lawbot.com   # 預設
export TWLEGALRAG_TLR_API_KEY=...                          # 選用
```

```toml
[tlr]
# base_url = "https://tlr.dr-lawbot.com"
# api_key  = "..."
```

## 隱私與資料流向

請務必理解這些網路傳輸：

- 你的**搜尋字詞 / 問題**會送到 TLR 檢索端點(`https://tlr.dr-lawbot.com`)以取得判決。
- **TLR may log your query text, timestamp, IP-derived metadata, and result
  counts for retrieval-quality analysis. Do not submit personal secrets or
  confidential facts. Queries are not used to train generative models.**
  (TLR 後端可能以**明文**記錄你的查詢字串、時間、由 IP 推得的中介資料與結果筆數,
  供檢索品質分析之用。請勿送出個人機密或保密事實。查詢不會用於訓練生成模型。)
- 本工具**不呼叫 LLM、不使用 server-side token**;若你自行把 bundle 餵給某個 AI,
  那段傳輸與費用發生在**你與你選的 AI provider 之間**,與本工具無關。
- 端點 API 金鑰(若有)請放環境變數,不要 commit 設定檔。

## citation check 如何運作

`twlegalrag/faithful/` 是一組**零依賴純函式**(只用標準庫 `re` + `unicodedata`)。
給定答案文字與 bundle 內判決片段,回 `pass` / `needs_review` / `fail`。設計上保守:
不確定時回 `needs_review` 而非 `fail`,以壓低誤報。它**不呼叫 LLM、不碰資料庫**,是
確定性的字串分析。詳見 `twlegalrag/faithful/VENDORED.md`。

## 其他接法（同一個 TLR 後端）

這個 CLI 是接 TLR 檢索服務的方式之一。同一個後端 `tlr.dr-lawbot.com` 也支援把判決
搜尋直接接進你的 AI 工具：

- **Claude Desktop（Remote MCP）**：Connectors → Add custom connector → URL 填
  `https://tlr.dr-lawbot.com/mcp`(免 OAuth、免 API key)。
- **ChatGPT（Custom GPT Action）**：在 Actions 匯入 `https://tlr.dr-lawbot.com/openapi.yaml`,
  認證選 None。

不論走 CLI、MCP 還是 ChatGPT Action,答案都由**你自己的 AI** 生成,本服務只提供判決
內容與可驗證的引用連結。

## 架構

```
你的問題
   │
[檢索]  TLR /v1/search   ──►  Layer-1 listings + result_token
   │    TLR /v1/fulltext ──►  每篇判決理由全文片段 (excerpt, 有上限)
   │
[打包]  pack ──► bundle.json (citation_id / allowed_citations / verification rules)
   │            └─► 交給你自己的 AI 工具
   │
[檢查]  check ──► bundle 層級引用檢查 (在/不在 bundle + bundle 內引文存在性)
```

判決庫、embedding、檢索邏輯都在伺服器端,**不在本 repo**。本 CLI 是開源客戶端
與引用檢查工具。

## 免責

本工具是分析輔助,不是法律意見,也不是律師。務必自行閱讀引用的判決全文。
透過 API 取得的判決為台灣公開裁判資料,你需為自己的使用負責。

## License

MIT.
