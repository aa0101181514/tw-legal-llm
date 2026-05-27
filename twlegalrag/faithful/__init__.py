"""faithful — citation 驗證的純函式模組。

零外部依賴 (只用 re + unicodedata), 不碰 DB / 不碰任何外部服務。
- citation_utils: 引用字號的正規化與比對純函式 (citation/jcase 正規化, canonical key, court prefix→法院名)。
- section_segmenter: 把判決全文切成段落並標註角色 (法院論理 vs 當事人主張) 的兩層切段器。
- verifier: citation 檢查的純函式 (wrong_doc_identity 字號身份 / fake_quote bundle 內逐字引文 等)。
"""
