# Taiwan Legal RAG (`twlegalrag`)

> Open-source CLI for **semantic** Taiwan legal judgment retrieval, powered by
> Legal Detective's 22M-judgment retrieval infrastructure.

Taiwan Legal RAG CLI retrieves Taiwan court judgments from Legal Detective's
public TLR endpoint and packages them for use with your own AI tools. It does
**not** generate legal advice by default and does **not** guarantee semantic
faithfulness of third-party model outputs. Its built-in citation check only
verifies whether cited judgments belong to the retrieved bundle.

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
- 對開發者來說,它提供一個可直接接入自己 AI workflow 的台灣法律 RAG retrieval layer。

> Unlike keyword-only legal search tools, Taiwan Legal RAG CLI connects to a
> production semantic retrieval backend built on 22M+ Taiwan court judgments,
> enabling fuzzy concept-level search while keeping model weights, infrastructure,
> and private indexes server-side.

（措辭說明：開源的是 **CLI**,不是模型或向量庫;後端的檢索服務、模型權重、私有
索引都留在伺服器端,不隨本工具公開。）

## 它做什麼 / 不做什麼

**做**：用自然語言檢索判決 → 取得結構化清單、全文片段、引用連結 → 打包成 bundle
交給你自己的 AI,或對 AI 產生的答案做 bundle 層級的引用檢查。

**不做**：本工具預設**不生成**法律意見。即使用 `ask`(選用)生草稿,那是由**你
自己的 LLM 帳號**生成,**不由法律偵探背書或驗證**。

### 內建的 citation check 能檢查什麼

`check` 與 `ask` 結尾的引用檢查是 **bundle 層級、盡力而為**的字串檢查,只驗：

- 答案引用的判決字號**是否在 bundle 內**(抓「引用了沒檢索到的字號」= 疑似捏造);
- 是否引用 bundle 外、或不存在的判決;
- **窄義**逐字引文(答案宣稱「法院說……」的逐字句是否出現在判決全文)。

### 它**不能**檢查什麼（重要）

- 法院見解是否**讀對**;
- 是否把**當事人主張**(原告/被告/上訴人)當成**法院見解**;
- 是否把**附帶論述**當成判決**核心權威**;
- paraphrase(改寫)型的見解幻覺。

這些都需要閱讀判決全文才能判斷——這也是為什麼 bundle 內附上判決全文與
verification instructions,要求下游模型自行核對。**`pass` 只代表「引用的字號身份
對得上」,不代表「法律推論正確」。**

## 安裝

```bash
pip install twlegalrag            # 核心 (retrieval + bundle + citation check)
pip install 'twlegalrag[openai]'  # + OpenAI provider (ask 用)
pip install 'twlegalrag[anthropic]'
pip install 'twlegalrag[all]'
```

## 使用

```bash
# 1) 純檢索 — 列出符合的判決 (無 LLM,無成本)
twlegalrag search "勞資 加班費" -n 5 --read

# 2) 打包 — 產生可交給任何 AI 的 bundle (無 LLM,無成本) ★推薦主流程
twlegalrag pack "車禍對方全責,我可以求償什麼?" -o bundle.json
#   → 把 bundle.json 貼給 ChatGPT / Claude / Gemini,要求它只引用 bundle 內的判決

# 3) 引用檢查 — 對任何 AI 產生的答案做 bundle 層級檢查
twlegalrag check bundle.json answer.txt

# 服務是否正常
twlegalrag health

# (選用) BYO-LLM 草稿 — 用你自己的 LLM 生草稿,未經驗證/背書
twlegalrag ask "車禍對方全責,我可以求償什麼?"
```

`pack` 產生的 bundle 包含 `query`、每筆判決的 `citation_id`(J1, J2, ...)、
`citation_text`、`citation_url`、`doc_id`、Layer-1 listing、`fulltext_excerpt`、
`allowed_citations`,以及一段 `verification_instructions`,明確要求下游模型只引用
bundle 內判決、把不支持的命題標為 unverified。stdout/stderr 也會印一段 AI USE NOTICE。

## 設定你自己的 LLM（僅 `ask` 需要）

本工具**不內附任何金鑰**。`ask` 用你自己的帳號,你自己付 token：

```bash
export TWLEGALRAG_LLM_PROVIDER=openai          # openai | anthropic | openai-compat
export TWLEGALRAG_LLM_API_KEY=sk-...
export TWLEGALRAG_LLM_MODEL=gpt-4o             # 選用,各 provider 有合理預設
```

OpenAI 相容端點(如智譜 GLM、本地 vLLM/Ollama gateway)**必須**設 `base_url`,
否則直接報錯(不會靜默打到官方 OpenAI 花錯錢)：

```bash
export TWLEGALRAG_LLM_PROVIDER=openai-compat
export TWLEGALRAG_LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
export TWLEGALRAG_LLM_API_KEY=...
export TWLEGALRAG_LLM_MODEL=glm-4
```

或放在 `~/.twlegalrag/config.toml`(已 git-ignore,**切勿** commit)：

```toml
[llm]
provider = "openai"
model = "gpt-4o"
api_key = "sk-..."
```

## 隱私與資料流向

請務必理解這些網路傳輸：

- 你的**搜尋字詞 / 問題**會送到 TLR 檢索端點(`https://tlr.dr-lawbot.com`)以取得判決。
- 若使用 `ask`(或自行把 bundle 餵給 LLM),你的**問題與判決內容**會送到**你設定的
  LLM provider**(OpenAI / Anthropic / 你的相容端點)。
- 法律偵探**不使用 server-side LLM token**——`ask` 的生成完全在你自己的帳號發生。
- **API 金鑰請放環境變數**,不要 commit 設定檔(`config.toml`、`.env` 已被 git-ignore)。
- OpenAI 相容 provider **未設 `base_url` 會直接報錯**,避免誤打官方端點。
- 由外部 LLM 生成的法律分析,**不由法律偵探背書**。

## citation check 如何運作

`twlegalrag/faithful/` 是一組**零依賴純函式**(只用標準庫 `re` + `unicodedata`)。
給定答案文字與檢索到的判決全文,逐筆回 `pass` / `needs_review` / `fail`。設計上
保守:不確定時回 `needs_review` 而非 `fail`,以壓低誤報。它**不呼叫 LLM、不碰
資料庫**,是確定性的字串分析。詳見 `twlegalrag/faithful/VENDORED.md`。

## 架構

```
你的問題
   │
[檢索]  TLR /v1/search   ──►  Layer-1 listings + result_token
   │    TLR /v1/fulltext ──►  每篇判決理由全文
   │
[打包]  pack ──► bundle.json (citation_id / allowed_citations / verification rules)
   │            └─► 交給你自己的 AI 工具
   │
[檢查]  check ──► bundle 層級引用檢查 (在/不在 bundle + 窄義逐字引文)
```

判決庫、embedding、檢索邏輯都在伺服器端,**不在本 repo**。本 CLI 是開源客戶端
與引用檢查工具。

## 其他接法（同一個 TLR 後端）

這個 Python CLI 是接 TLR 檢索服務的方式之一。同一個後端 `tlr.dr-lawbot.com`
也支援把判決搜尋直接接進你的 AI 工具,不必裝 CLI：

**Claude Desktop（Remote MCP）**
1. Claude Desktop → **Customize** → **Connectors** → **Add custom connector**。
2. Remote MCP server URL 填 `https://tlr.dr-lawbot.com/mcp`(免 OAuth、免 API key)。
3. 直接在對話問「幫我搜尋離婚剩餘財產分配的判決並引用 3 個案號」。

**ChatGPT（Custom GPT Action）**
- 在 Custom GPT 的 Actions 匯入 OpenAPI schema:`https://tlr.dr-lawbot.com/openapi.yaml`
- Action 認證選 **None**(本服務免認證)。

不論走 CLI、MCP 還是 ChatGPT Action,答案都由**你自己的 AI**生成,本服務只提供
判決內容與可驗證的引用連結。

## 免責

本工具是分析輔助,不是法律意見,也不是律師。務必自行閱讀引用的判決全文。
透過 API 取得的判決為台灣公開裁判資料,你需為自己的使用負責。

## License

MIT.
