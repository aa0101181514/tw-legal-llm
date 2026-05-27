"""faithful — zero-dependency pure functions used by the bundle-level citation check.

只用 re + unicodedata, 不碰 DB / 不碰任何外部服務。

- citation_utils: 引用字號的正規化與比對純函式 (citation/jcase 正規化, canonical key,
  court prefix→法院名)。
- section_segmenter: 文字正規化與段落角色工具 (供下列檢查內部使用)。
- verifier: citation 檢查純函式。本 CLI 只用其中兩個: wrong_doc_identity (字號身份是否
  對得上 bundle 內判決) 與 fake_quote (用於 bundle 層級的逐字引文存在性檢查 —— 只驗引文
  是否出現在 bundle 文字某處, 不證明出自所指那篇)。模組內另有 party_as_court /
  verdict_flip 等實驗性檢查, 本 CLI 不呼叫 (它們需要 evidence span / 語意判斷,
  不在 bundle-level best-effort 範圍)。
"""
