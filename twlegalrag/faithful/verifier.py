"""verifier — citation 檢查的純函式。

4 個 check: wrong_doc_identity (字號身份) / fake_quote (bundle 內逐字引文) /
party_as_court (當事人主張被當成法院見解) / verdict_flip (結果講反)。

純函式: fulltext / verdict_outcome / candidate 由呼叫方傳入, 不碰 DB/外部服務。
import 自家 citation_utils + section_segmenter。

設計原則:
- verdict_flip 只標 risk 不視為錯誤, 因粗粒度結果易誤判。
- 不用 reverse_lookup 結果當「身份一致」證明 — wrong_doc 是判 AI citation 身份 == selected_doc_id。

每個 check 回 dict: {status: pass|fail|needs_review, reason, detail}。
"""
from __future__ import annotations
import re

from . import citation_utils as CU
from . import section_segmenter as SEG

# 法院地名 token (同城不同庭 = 名稱精確度爭議, 非引錯案)。
_PLACE_TOKENS = ("臺北", "新北", "士林", "桃園", "新竹", "苗栗", "臺中", "彰化", "南投",
                 "雲林", "嘉義", "臺南", "高雄", "屏東", "臺東", "花蓮", "宜蘭", "基隆",
                 "澎湖", "金門", "連江", "橋頭")


def _place_token(court: str) -> str | None:
    """從法院名/簡稱抽地名 token (臺北/高雄...), 台→臺正規化。用於同城不同庭比對。"""
    if not court:
        return None
    s = court.replace("台", "臺")
    for p in _PLACE_TOKENS:
        if p in s:
            return p
    return None

# ── verdict 詞典 (verdict_flip 用) ──
_WIN_OUTCOME = {"full_win", "partial_win", "granted", "guilty", "settled", "guilty_mitigated"}
_LOSE_OUTCOME = {"full_loss", "dismissed", "not_entertain", "not_guilty", "withdrawn", "not_guilty_part"}
# other/transferred/空 = 中性, 不判 flip (避免誤殺)
_WIN_WORDS = re.compile(r"成功(聲請|請求)|獲准|准許|勝訴|聲請有理|核准|准予|聲請成功|判准")
_LOSE_WORDS = re.compile(r"駁回|敗訴|不受理|聲請無理|不予准許|遭駁")


def check_wrong_doc_identity(ai_citation: str, selected_doc_id: str,
                             candidate_doc_ids: list[str] | None = None) -> dict:
    """規則1: AI citation 的 法院/年/字別/號 是否 == selected_doc_id 的身份。
    純比 key + 法院身份, 不反查 DB。
    - AI citation 解不出 key → needs_review
    - selected_doc_id 為空 (ambiguous/not_found) → needs_review (沒鎖定, 非 fail)
    - key 不一致 (年/字別/號) → fail
    - key 一致但法院名不符 (同字號跨法院抓錯庭) → fail (wrong_court_identity)
    - key+法院都一致 → pass
    """
    ck = CU.canonical_citation_key(ai_citation)
    if not ck:
        return {"status": "needs_review", "reason": "ai_citation_unparseable",
                "detail": {"ai_citation": ai_citation}}
    if not selected_doc_id:
        return {"status": "needs_review", "reason": "no_selected_doc", "detail": {"ai_key": ck}}
    dk = CU.doc_id_citation_key(selected_doc_id)
    if not dk:
        return {"status": "needs_review", "reason": "selected_doc_id_unparseable",
                "detail": {"selected_doc_id": selected_doc_id}}
    if ck != dk:
        return {"status": "fail", "reason": "wrong_doc_identity_key_mismatch",
                "detail": {"ai_key": ck, "selected_key": dk}}
    same_key_candidates = [
        d for d in (candidate_doc_ids or [])
        if CU.doc_id_citation_key(d) == ck
    ]
    multi_cand = len(set(same_key_candidates)) >= 2
    ai_court = CU.parse_court_mention(ai_citation)
    if multi_cand and not ai_court:
        return {"status": "needs_review", "reason": "same_number_multi_candidate_no_court_in_citation",
                "detail": {"ai_key": ck, "n_candidates": len(set(same_key_candidates)),
                           "note": "同字號多候選但 AI citation 未指明法院, 無法確定指哪份"}}
    # 法院身份比對. resolver 解不出 → 不放過, 改 needs_review (None 不視為一致)
    sel_court = CU.court_name_from_doc_id(selected_doc_id)
    sel_aliases = CU.court_aliases_from_doc_id(selected_doc_id)
    if not sel_court or not sel_aliases:
        return {"status": "needs_review", "reason": "selected_court_unresolved",
                "detail": {"selected_doc_id": selected_doc_id,
                           "note": "無法解析 selected doc 的法院, 交人工複核不直接判錯"}}
    if ai_court:
        if ai_court not in sel_aliases:
            # doc_id 2字母 fallback 對簡易庭/地行訴訟庭不可靠, 易誤判。
            # 用 jcase 案類所在地當第三方信號: 若 AI 法院 與 jcase hint 一致 (AI 跟案類信號相符),
            # 則衝突源自 doc_id prefix resolution → needs_review(metadata_court_conflict) 不 fail。
            jhint = CU.jcase_place_hint(ck[1]) if ck else None
            ai_tok = ai_court
            if jhint and CU._court_token(jhint) in ai_tok:
                return {"status": "needs_review", "reason": "metadata_court_conflict",
                        "detail": {"ai_citation": ai_citation, "selected_court": sel_court,
                                   "ai_court": ai_court, "jcase_place_hint": jhint,
                                   "note": "AI 法院 與 jcase 案類所在地一致, 但 doc_id prefix 解出不同法院 "
                                           "= metadata/prefix 衝突, 交人工複核, 不判錯"}}
            # selected 法院若只來自【推測性 2 字母 fallback】(非精確表), 解析不可信
            # (例如橋頭 CTD 被誤判為臺中, 員林簡 OL / 新竹簡 CP / 新市簡 SS / 斗六簡 TL 等都屬此類) →
            # 不 fail, 降 needs_review(court_name_imprecise)。只有 exact 解析才可 fail wrong_court。
            conf = CU.court_resolution_confidence(selected_doc_id)
            if conf != "exact":
                return {"status": "needs_review", "reason": "court_name_imprecise",
                        "detail": {"ai_citation": ai_citation, "selected_court": sel_court,
                                   "ai_court": ai_court, "resolution_confidence": conf,
                                   "note": "selected doc 法院只由推測性 2 字母 fallback 解出 (非精確表), "
                                           "解析不可信, 交人工複核, 不判錯"}}
            # 同城不同專業法庭 (AI 寫「臺北地院」但 selected 是「臺北高等行政法院地方行政
            # 訴訟庭」/「高雄少年及家事法院」) = 法院【名稱精確度】爭議, 非引錯案 (AI 引對那篇) → 降 needs_review。
            # 判準: AI 法院的地名 token 被 selected 法院全名包含。
            ai_place = _place_token(ai_court)
            if ai_place and ai_place in (sel_court or ""):
                return {"status": "needs_review", "reason": "court_name_imprecise",
                        "detail": {"ai_citation": ai_citation, "selected_court": sel_court,
                                   "ai_court": ai_court, "ai_place": ai_place,
                                   "note": "同城不同專業法庭 (地院 vs 高行政訴訟庭/少家法院), AI 名稱不精確但引對那篇, 交人工複核, 不判錯"}}
            return {"status": "fail", "reason": "wrong_court_identity",
                    "detail": {"ai_citation": ai_citation, "selected_court": sel_court,
                               "ai_court": ai_court, "selected_aliases": sorted(sel_aliases),
                               "jcase_place_hint": jhint, "resolution_confidence": conf,
                               "note": "key 相同但 AI 寫的法院 ≠ selected doc 法院, 且 selected 法院由精確表解出 (真跨法院抓錯庭)"}}
        return {"status": "pass", "reason": "doc_identity_match",
                "detail": {"key": ck, "court": sel_court, "ai_court": ai_court}}
    # AI citation 短形沒寫法院 + 單一候選 → key 已一致可放行
    return {"status": "pass", "reason": "doc_identity_match_short_form",
            "detail": {"key": ck, "court": sel_court}}


_QUOTE_RE = re.compile(r'[「『]([^」』]{6,})[」』]')

# ── fake_quote 縮回「明確逐字判決引文」捏造型 ──
# 設計: fake_quote 只能 fail「AI 明確宣稱逐字判決原文」且 selected_doc fulltext 找不到。
# 釋義式引號 / party 引語 / 跨案援引要旨 → 不得 fail (pass / needs_review)。
# 不做語義容忍 (那是另一層判斷, 不塞進這個 pure check)。

# 逐字原文歸屬語: 只有這些才把引號當「court_verbatim_quote」驗逐字。
# 不因附近只有「法院/判決/認為/指出」就啟動 (那會把釋義也誤升)。
_VERBATIM_MARKER_RE = re.compile(
    r'(判決原文|判決明載|判決載明|判決稱|原判決記載|裁定載明|裁定明載|'
    r'法院明確指出|最高法院明確指出|高等法院明確指出|原文記載|逐字記載|明文記載)')
# party 引語歸屬語: 最近歸屬是當事人 → party_quote, 優先於 court attribution。
_PARTY_ATTR_RE = re.compile(
    r'(原告主張|被告抗辯|被告答辯|被告辯稱|上訴人主張|被上訴人抗辯|被上訴人答辯|'
    r'聲請人主張|相對人抗辯|抗告人主張|當事人(?:稱|辯稱|主張)|辯稱|抗辯|答辯)')
# 另一案 citation (用於 cross-case 偵測)
_OTHER_CITATION_RE = re.compile(r'\d{2,3}\s*年度?\s*\S{1,10}?\s*字第\s*\d+\s*號')


def classify_quote_context(answer_text: str, q_start: int, q_end: int,
                           selected_doc_id: str | None) -> tuple[str, str]:
    """分類單個引號的脈絡。回 (kind, reason)。
    kind: court_verbatim_quote | party_quote | cross_case_quote | paraphrase_or_general_quote
    優先序: party > cross_case > court_verbatim (收窄) > paraphrase。
    """
    pre = answer_text[max(0, q_start - 30):q_start]
    post = answer_text[q_end:q_end + 30]
    window = pre + post
    # party 引語優先: 最近歸屬是當事人 → 不驗逐字
    if _PARTY_ATTR_RE.search(pre) or _PARTY_ATTR_RE.search(post):
        return ("party_quote", "nearest_attribution_is_party")
    # cross-case: 引號附近另有 citation 且 canonical key != selected_doc key → 不拿 selected fulltext 硬驗
    if selected_doc_id:
        sel_key = CU.doc_id_citation_key(selected_doc_id)
        for m in _OTHER_CITATION_RE.finditer(window):
            ck = CU.canonical_citation_key(m.group(0))
            if ck and sel_key and ck != sel_key:
                return ("cross_case_quote", "quote_attributed_to_other_citation")
    # court_verbatim: 只有明確逐字原文歸屬語才啟動
    if _VERBATIM_MARKER_RE.search(pre) or _VERBATIM_MARKER_RE.search(post):
        return ("court_verbatim_quote", "verbatim_origin_marker")
    # 其餘 (含「法院/判決/認為/指出」泛歸屬) = 釋義/泛引號, 不得 fail
    return ("paraphrase_or_general_quote", "no_verbatim_origin_marker")


# 逐字整串找不到時, 用「最長連續片段」分辨「真片段+框架」vs「純捏造」。
# normalize 後連續 >=8 字命中全文 = 視為含真原文片段 (非純捏造)。
# 校準: 含真片段的引文最長連續 8-9 字; 純捏造最長僅 3-6 字 → 8 為乾淨分界。
_PARTIAL_FRAGMENT_MIN = 8


def _longest_fragment_in(needle: str, haystack: str) -> int:
    """needle 中最長的連續子串長度 (出現在 haystack 內)。
    只需判斷是否 >= 門檻, 故由【門檻長度】起逐窗檢查: 任一 _PARTIAL_FRAGMENT_MIN 長窗命中即達標。"""
    n = len(needle)
    if n < _PARTIAL_FRAGMENT_MIN or not haystack:
        return n if needle and needle in haystack else 0
    for i in range(0, n - _PARTIAL_FRAGMENT_MIN + 1):
        if needle[i:i + _PARTIAL_FRAGMENT_MIN] in haystack:
            return _PARTIAL_FRAGMENT_MIN   # 達標即可 (不需精確最長)
    return 0


def check_fake_quote(answer_text: str, fulltext: str,
                     selected_doc_id: str | None = None) -> dict:
    """規則2: 只 fail「明確逐字判決引文 + selected_doc 全文找不到」。
    - party 引語 / 釋義引號 → pass (不驗逐字)
    - 跨案援引要旨 → needs_review (不拿 selected fulltext 硬驗)
    - court_verbatim 且全文有 → pass; 全文無 → fail (真捏造型)
    不確定寧可 needs_review, 不可 fail。
    """
    if not answer_text:
        return {"status": "pass", "reason": "no_answer", "detail": {}}
    verbatim_quotes = []      # 要驗逐字的 (court_verbatim)
    cross_case = []           # needs_review
    skipped = {"party_quote": 0, "paraphrase_or_general_quote": 0}
    for m in _QUOTE_RE.finditer(answer_text):
        q = m.group(1).strip()
        if len(q) < 8:
            continue
        kind, _ = classify_quote_context(answer_text, m.start(), m.end(), selected_doc_id)
        if kind == "court_verbatim_quote":
            verbatim_quotes.append(q)
        elif kind == "cross_case_quote":
            cross_case.append(q[:50])
        else:
            skipped[kind] = skipped.get(kind, 0) + 1
    if not verbatim_quotes:
        # 沒有任何「明確逐字判決引文」宣稱 → 不 fail
        if cross_case:
            return {"status": "needs_review", "reason": "cross_case_quote_not_verified",
                    "detail": {"cross_case_quotes": cross_case, "skipped": skipped}}
        return {"status": "pass", "reason": "no_verbatim_quote_claim",
                "detail": {"skipped": skipped}}
    if not fulltext:
        return {"status": "needs_review", "reason": "no_fulltext_to_verify",
                "detail": {"verbatim_quote_count": len(verbatim_quotes)}}
    ft_norm = SEG._normalize(fulltext)
    fakes = []          # 全文完全找不到實質片段 = 真捏造
    partials = []       # 有實質連續片段在全文 (AI 真片段+自己框架) → 不 fail, 降 needs_review
    for q in verbatim_quotes:
        if q in fulltext or SEG._normalize(q) in ft_norm:
            continue
        # 逐字整串找不到, 但若有【實質連續片段】在全文 = AI 把真原文片段嵌進自己措辭,
        # 非純捏造 → 不 fail。只有完全沒有實質片段才 fail (真捏造)。
        if _longest_fragment_in(SEG._normalize(q), ft_norm) >= _PARTIAL_FRAGMENT_MIN:
            partials.append(q[:50])
        else:
            fakes.append(q[:50])
    if fakes:
        return {"status": "fail", "reason": "fake_quote",
                "detail": {"fake_quotes": fakes, "partial_quotes": partials,
                           "verbatim_quotes": len(verbatim_quotes),
                           "cross_case_quotes": cross_case, "skipped": skipped,
                           "note": "全文無實質連續片段 = 真捏造逐字引文"}}
    if partials:
        return {"status": "needs_review", "reason": "quote_partial_fragment_in_fulltext",
                "detail": {"partial_quotes": partials, "verbatim_quotes": len(verbatim_quotes),
                           "note": "逐字整串不在全文但有實質連續片段 = 真片段嵌進自己措辭, 交人工複核, 不判錯"}}
    return {"status": "pass", "reason": "all_verbatim_quotes_present",
            "detail": {"verified_quotes": len(verbatim_quotes), "skipped": skipped}}


_COURT_CLAIM_RE = re.compile(r"法院(認為|指出|表示|認定|揭示|闡釋)|判決(指出|認為|揭示|表示)|實務見解|實務上認為")


def check_party_as_court(claim_text: str, evidence_span: str, fulltext: str,
                         claim_kind: str = "case_holding") -> dict:
    """規則3: AI 寫「法院認為/判決指出」但 evidence span role 是 party_claim/defense → fail。
    複用 section_segmenter role gate。
    - AI 沒宣稱法院見解 (claim_kind=party_position 且無「法院認為」措辭) → pass (誠實轉述)
    - AI 宣稱法院見解但 evidence role 是 party → fail
    - span 定位不到/role 判不出 → needs_review
    """
    claims_court = bool(_COURT_CLAIM_RE.search(claim_text or "")) or claim_kind == "case_holding"
    if not claims_court:
        return {"status": "pass", "reason": "not_claimed_as_court_holding",
                "detail": {"claim_kind": claim_kind}}
    if not evidence_span or not fulltext:
        return {"status": "needs_review", "reason": "no_span_or_fulltext", "detail": {}}
    r = SEG.role_of_span(fulltext, evidence_span)
    l2 = r.get("l2_role"); l1 = r.get("l1_role")
    if r.get("match_mode") in ("not_located", "ambiguous_span"):
        return {"status": "needs_review", "reason": f"span_{r.get('match_mode')}",
                "detail": {"l1": l1, "l2": l2}}
    if l2 == "party_embedded_claim" or l1 in ("原告主張", "被告抗辯"):
        return {"status": "fail", "reason": "party_as_court",
                "detail": {"l1_role": l1, "l2_role": l2,
                           "note": "AI 宣稱法院見解但 evidence 落在當事人主張/抗辯段"}}
    return {"status": "pass", "reason": f"evidence_role_ok:{l2}",
            "detail": {"l1_role": l1, "l2_role": l2}}


def check_verdict_flip(claim_text: str, verdict_outcome: str | None) -> dict:
    """規則4: AI 說准許/成立 但判決駁回 (反向)。
    verdict_outcome 粗粒度 → 只標 risk, 不視為錯誤。
    - 空/other/transferred → needs_review (中性, 不誤殺)
    - partial_win → needs_review (partial win 易誤殺, 不單獨判)
    - AI win 詞 + verdict LOSE / AI lose 詞 + verdict WIN → risk flip
    """
    vo = (verdict_outcome or "").strip()
    if not vo or vo in ("other", "transferred"):
        return {"status": "needs_review", "reason": "verdict_neutral_or_unknown",
                "detail": {"verdict_outcome": vo or None}}
    if vo == "partial_win":
        return {"status": "needs_review", "reason": "partial_win_too_coarse_to_judge",
                "detail": {"verdict_outcome": vo}}
    win_t = bool(_WIN_WORDS.search(claim_text or ""))
    lose_t = bool(_LOSE_WORDS.search(claim_text or ""))
    if win_t and vo in _LOSE_OUTCOME:
        return {"status": "risk", "blocking": False, "reason": "risk_verdict_flip_win_but_lose",
                "detail": {"verdict_outcome": vo, "note": "啟發式提示, 僅標 risk 不算入 fail"}}
    if lose_t and vo in _WIN_OUTCOME:
        return {"status": "risk", "blocking": False, "reason": "risk_verdict_flip_lose_but_win",
                "detail": {"verdict_outcome": vo, "note": "啟發式提示, 僅標 risk 不算入 fail"}}
    return {"status": "pass", "reason": "verdict_consistent_or_no_signal",
            "detail": {"verdict_outcome": vo, "win_word": win_t, "lose_word": lose_t}}


def run_all_checks(*, ai_citation: str, selected_doc_id: str, candidate_doc_ids: list[str] | None,
                   answer_text: str, claim_text: str, evidence_span: str, fulltext: str,
                   claim_kind: str, verdict_outcome: str | None) -> dict:
    """跑四 check, 彙總。wrong_doc/fake_quote/party_as_court 可 fail;
    verdict_flip 只標 risk (進 shadow_fail_reasons, 不算入 fail)。"""
    c1 = check_wrong_doc_identity(ai_citation, selected_doc_id, candidate_doc_ids)
    c2 = check_fake_quote(answer_text, fulltext, selected_doc_id)
    c3 = check_party_as_court(claim_text, evidence_span, fulltext, claim_kind)
    c4 = check_verdict_flip(claim_text, verdict_outcome)
    blocking = (c1, c2, c3)
    blocking_fails = [c["reason"] for c in blocking if c["status"] == "fail"]
    blocking_nr = [c["reason"] for c in blocking if c["status"] == "needs_review"]
    shadow_fails = [c4["reason"]] if c4.get("status") == "risk" else []
    if blocking_fails:
        status = "fail"
    elif blocking_nr:
        status = "needs_review"
    else:
        status = "pass"
    needs_review = blocking_nr + ([c4["reason"]] if c4.get("status") == "needs_review" else [])
    return {
        "verifier_status": status,
        "fail_reasons": blocking_fails,
        "shadow_fail_reasons": shadow_fails,
        "needs_review_reasons": needs_review,
        "checks": {"wrong_doc": c1, "fake_quote": c2, "party_as_court": c3, "verdict_flip": c4},
    }
