"""台灣判決全文兩層切段器。

把判決全文切成段落並標註角色 (法院論理 vs 當事人主張):
Layer 1 依標題粗切大區塊, Layer 2 對 span 所在的局部句段判子角色。

核心原則: 不重切全文成碎片。保留 Layer 1 大段, 只對 span 所在局部句段加 role。

用法:
  from section_segmenter import segment, role_of_span
  segs = segment(fulltext)          # Layer1 大區塊 list
  role = role_of_span(fulltext, span_text)  # 給一段 evidence_span, 回它所在的 section_role
"""
import re

# ---- Layer 1: 標題粗切 (容忍全形/多半形空白) ----
def _sp(s):  # 標題字間可有空白
    return r'\s*'.join(list(s))

# 真標題錨點: 行首 + 標題字(字間可空白) + 緊接 行尾/換行/全半形冒號. 排除「事實上/理由不」正文詞.
def _title(s):
    return re.compile(r'(?:^|\n)\s*' + r'\s*'.join(list(s)) + r'\s*(?:[：:]|$|\n|，)', re.M)
L1_ANCHORS = [
    ('主文',      _title('主文')),
    ('事實及理由',_title('事實及理由')),
    # 簡易判決常見「事實及理由要領」, 行首+標題字+接 行尾/冒號/編號 (要領後常接「一、」)
    ('事實及理由', re.compile(r'(?:^|\n)\s*' + r'\s*'.join(list('事實及理由要領')) + r'\s*(?:[：:]|$|\n|一|㈠)', re.M)),
    ('事實',      _title('事實')),
    ('理由',      _title('理由')),
]

# ---- Layer 2: 理由段內句首信號 → 子角色 ----
# 當事人角色 × 主張動詞 (組合偵測, 比窮舉穩). 限句首/近句首 (head) 才算, 防法院段誤判.
_PARTY_ROLES = ['原告','被告','上訴人','被上訴人','抗告人','再抗告人','相對人','聲請人','檢察官','辯護人','告訴人','自訴人','參加人']
_PARTY_VERBS = ['主張','抗辯','辯稱','則辯','爭執','指摘','陳述','陳稱','起訴主張','復主張','另主張','前開抗辯','所辯','所稱','前揭主張']
import re as _re
PARTY_RE = _re.compile(
    '(?:' + '|'.join(_PARTY_ROLES) + ')'      # 角色
    + '(?:[等則復又另])?'                       # 連接字
    + '(?:前開|前揭|所)?'                        # 修飾
    + '(?:' + '|'.join(_PARTY_VERBS) + ')')
# 保留舊 list 供回看 (look_back) 用
PARTY_SIGNALS = [r+v for r in _PARTY_ROLES for v in ['主張','抗辯','辯稱']]
# 法院論述信號 (可作 supported evidence). 含慰撫金裁量/論理連接句首.
COURT_SIGNALS = ['經查','本院認為','本院判斷','本院審酌','本院之判斷','本院查','查本件','本院斟酌','本院以為','是以本院',
                 '本院綜合審酌','本院綜合','復參以','惟查','復查','據此','是以','本院認','本院認定']

# 法院裁量/認定/結論 cue — 補召回 (例如「應以…為適當」型)。
# ⚠️ 這層只在【非 party】句才放行 (party guard 先跑), 且需句中有本案指向詞 (CASE_REFS) 才升,
#    避免抽象法律規則 recitation / 純套話誤升。歸 court_application_reasoning (本案適用結論)。
# 句尾判斷詞: 法院終局裁斷, 常落句尾 → 掃整句 (party 已先 return, 不誤升)。
COURT_VERDICT_FINAL = ['為有理由','為無理由','應予准許','應予駁回','不應准許','為適當',
                       '洵屬有據','尚屬有據']
# 句首/前段 cue: 限前 35 字, 避免抓中段抽象論述。
COURT_CONCLUSION = ['應以','應認','應屬','自屬','核屬','依上開說明','依前揭說明','揆諸前揭說明']

# 法院本案適用/推論結論信號 (獨立子角色 court_application_reasoning, 護欄嚴格)
# 強信號: 句首即可 (本身已含法院推論語氣). 復按/次按 不在此, 在 LEGAL_RULE (見下).
APPLY_STRONG = ['由是可知','是以本件','從而本件','故本件','準此','從而','惟因']
# 弱信號: 太寬, 只在同句有本案指向詞才放行
APPLY_WEAK = ['足見','可知','堪認']
# 本案指向詞 (護欄: 推論句必須指向本案, 否則可能是抽象論述/法條 recitation)
CASE_REFS = ['本件','系爭','原告','被告','上訴人','被上訴人','相對人','聲請人','該案','本案']
# 事實認定信號 (只支撐事實 claim 不支撐法律見解)
FACT_SIGNALS = ['不爭執事項','兩造不爭執','下列事實','堪信為真','堪認','足認','認定事實']
# 程序套話
PROC_SIGNALS = ['程序方面','本案經','言詞辯論終結','合法通知','一造辯論','傳喚未到']

# 法院駁斥當事人主張的結論 cue: 含 party signal + 此 cue 的整句 = 法院駁斥
# 詞根 regex (採/取 一字之差穷舉易漏). ⚠️只收明確駁斥詞根, 不收裸「無理由」(太寬會誤放).
import re as _re0
REJECTION_RE = _re0.compile(
    r'(無足[採取]信?'           # 無足採/無足取/無足採信
    r'|不足[採取]信?'           # 不足採/不足取
    r'|無可[採取]信?'           # 無可採/委無可採/均無可採/尚無可採
    r'|[洵核要]無足[採取]'       # 洵無足採/核無足取/要無足採
    r'|難認可[採取]'             # 難認可採
    r'|尚非可[採取]'             # 尚非可採
    r'|不可[採取]信?'           # 不可採
    r'|洵屬無據|核屬無據|顯屬無據'  # 無據型
    r'|[為核]無理由)')           # 為無理由/核無理由 (限這兩個明確型, 不收裸無理由)
# 保留 list 形式給其它地方參考
REJECTION_CUES = ['無足採信','無足取','無足採','不足採','委無可採','不可採','洵無足取','洵無足採','要無可採','為無理由','尚非可採','核無足取','難認可採','洵屬無據']

# 法條/見解引述 (「按+法條」不直接 court_reasoning, 是抽象法律規則陳述)
# 「按/復按/次按/又按」開頭 + 法條 → legal_rule (復按/次按 進此非 court_reasoning;
# 後接本案適用語才在 _sentence_role 升 court_application)
LEGAL_RULE_INLINE = re.compile(r'^(按|依|又按|查按|復按|次按|末按|另按).{0,40}(規定|定有明文|第.{0,8}條|釋字|準則|條例|意旨)')
# 近鄰「適用句」信號: legal_rule 後若同句/近鄰出現這些, 才可升級 court_reasoning
APPLY_SIGNALS = ['經查','本件','本院認為','是以','準此','查本件','本案','揆諸','從而','據此']

# 「查…主張」型: 句中含「主張」且開頭是查 → 仍歸 party
PARTY_INLINE = re.compile(r'^查.{0,30}(主張|辯稱|抗辯)')

# 護欄: 主文段內「理由訊號」— 有這些才進 Layer2, 否則是純 disposition 結果句
_ReasoningInMainText = re.compile(
    r'(本院審酌|本院綜合審酌|本院認為|經查|準此|從而|揆諸|按[^，。]{0,30}(規定|條|明文)'
    r'|[一二三四五六七八九][、．]|㈠|㈡|㈢|⒈|⒉|⒊|復按|次按|惟查)')

# normalize: 只限空白/換行/全半形/零寬/常見標點差異 (只定位不改寫原文)
_ZW = '​‌‍﻿'
def _normalize(s):
    if not s:
        return ''
    s = ''.join(ch for ch in s if ch not in _ZW)
    s = s.replace('　', '')  # 全形空白
    s = re.sub(r'\s+', '', s)    # 所有空白/換行
    # 全形→半形標點常見差異 (不改中文字/數字)
    trans = str.maketrans('，。：；！？（）「」、', ',.:;!?()"",')
    s = s.translate(trans)
    return s

def segment(fulltext):
    """Layer 1: 回大區塊 [{role, start, end, text}]. role ∈ 主文|事實|理由|原告主張|被告抗辯|前言."""
    if not fulltext:
        return []
    marks = []
    for role, pat in L1_ANCHORS:
        for m in pat.finditer(fulltext):
            marks.append((m.start(), role))
    marks.sort()
    # 去重: 同一 role 只取第一個主要出現 (理由/事實可能重複, 取最早當段界)
    segs = []
    used_role = {}
    bounds = []
    for pos, role in marks:
        bounds.append((pos, role))
    if not bounds:
        return [{'role':'unknown_section','start':0,'end':len(fulltext),'text':fulltext}]
    # 以所有錨點為界切段, 每段 role = 該段起始錨點 role
    bounds.sort()
    # 前言 (第一個錨點前)
    if bounds[0][0] > 0:
        segs.append({'role':'前言','start':0,'end':bounds[0][0],'text':fulltext[:bounds[0][0]]})
    for i,(pos,role) in enumerate(bounds):
        end = bounds[i+1][0] if i+1 < len(bounds) else len(fulltext)
        if end <= pos:
            continue
        segs.append({'role':role,'start':pos,'end':end,'text':fulltext[pos:end]})
    return segs

def _sentence_role(sent, tail=''):
    """Layer 2: 給理由段內一句 (+近鄰 tail), 判子角色.
    優先序: party+rejection_cue → court_rejection_of_party_argument;
    只 party → party_embedded_claim; court → court_reasoning; legal_rule(+近鄰升級); fact; proc; unknown.
    ⚠️ rejection 必須看整句 (含主張內容+駁斥 cue); 只截到「上訴人抗辯…」沒駁斥 cue → 仍 party。"""
    s = sent.strip()
    if not s:
        return 'unknown_section'
    # 剝句首子項編號 (㈠㈡/⒈⒉/一、/7. 等) + 收掉內部換行/縮排空白 — 編號與排版空白
    # 都會擋住句首信號 (例如「⒊復按…\n  法律強制規定」: 編號擋句首 + 空白把「規定」推出 40 字窗)。
    # 只供 signal 比對, 不改輸出語意; 原 s 仍用於整句 rejection/quote。
    s_probe = _re.sub(r'[\s　]+', '', s)
    s_probe = _re.sub(r'^(?:[㈠-㈩]|[⒈-⒛]|[（(]?[一二三四五六七八九十]+[）)]?[、.．]|\d{1,2}[、.．])', '', s_probe)
    head = s_probe[:25]
    # 句首「是/查」等法院引述起手 + 角色 也算 party context (法院「是上訴人抗辯…」)
    head_probe = _re.sub(r'^[是查惟按又況]', '', head)
    has_party = bool(PARTY_RE.search(head)) or bool(PARTY_RE.search(head_probe)) or bool(PARTY_INLINE.match(s_probe))
    # 駁斥 cue 看整句 (不只 head) — 法院引述當事人後在句尾駁斥
    has_rejection = bool(REJECTION_RE.search(s))
    # party signal + rejection cue → 整句是法院駁斥 (可撐 rejection_holding 不撐 party_position)
    if has_party and has_rejection:
        return 'court_rejection_of_party_argument'
    if has_party:
        # 護欄 c: party-only 結構 (無 rejection) → party, 不升 application
        return 'party_embedded_claim'
    for sig in COURT_SIGNALS:
        if sig in head:
            return 'court_reasoning'
    # court_application_reasoning (護欄): 本案適用/推論結論
    # 強信號在句首/前20字 + 句中有本案指向詞; 弱信號(足見/可知/堪認)必須同句有本案指向詞
    has_caseref = any(ref in s for ref in CASE_REFS)
    for sig in APPLY_STRONG:
        if sig in head and has_caseref:
            return 'court_application_reasoning'
    if has_caseref:
        for sig in APPLY_WEAK:
            if sig in head:
                return 'court_application_reasoning'
    # 法院裁量/認定/結論 cue (護欄: 已過 party guard, 此句非當事人主張; 需本案指向詞).
    # 句尾判斷詞 (為有理由/為無理由/應予准許/應予駁回/不應准許/為適當) 可落句尾 → 掃整句;
    # 其餘 cue (應以/應認/應屬/依上開說明...) 限前 35 字, 避免抓到中段抽象論述。
    # party 句已在上面 return, 故此處掃整句不會誤升當事人主張。
    if has_caseref:
        for sig in COURT_VERDICT_FINAL:
            if sig in s_probe:
                return 'court_application_reasoning'
        probe_head = s_probe[:35]
        for sig in COURT_CONCLUSION:
            if sig in probe_head:
                return 'court_application_reasoning'
    # 按+法條 = 抽象法律規則陳述 (不直接 court). 但若同句/近鄰有適用句信號 → 升 court_reasoning
    if LEGAL_RULE_INLINE.match(s_probe):
        ctx = s + tail
        for ap in APPLY_SIGNALS:
            if ap in ctx:
                return 'court_reasoning'
        return 'legal_rule_recitation'
    for sig in FACT_SIGNALS:
        if sig in head:
            return 'fact_finding'
    for sig in PROC_SIGNALS:
        if sig in head:
            return 'procedural_background'
    return 'unknown_section'

def locate_span(fulltext, span_text):
    """exact-first 定位, 不准 substring 猜.
    回 dict {match_mode, span_start, span_end, located_span_text}.
    match_mode: exact | normalized | not_located | ambiguous_span.
    - 第一層 exact: fulltext 原文找 span_text. 命中須唯一, 多處=ambiguous_span.
    - 第二層 normalized: 兩邊 normalize 後找; 命中須唯一, 多處=ambiguous_span.
    - normalize 只定位, located_span_text 一律回傳【原文】片段 (不回傳 normalize 後的).
    """
    if not fulltext or not span_text:
        return {'match_mode':'not_located','span_start':None,'span_end':None,'located_span_text':None}
    sp = span_text.strip()
    # 第一層 exact (命中須唯一, 多處=ambiguous_span, 不靜默取第一處)
    e_hits = []
    st = 0
    while True:
        i = fulltext.find(sp, st)
        if i < 0: break
        e_hits.append(i); st = i+1
        if len(e_hits) > 1: break
    if len(e_hits) == 1:
        i = e_hits[0]
        return {'match_mode':'exact','span_start':i,'span_end':i+len(sp),'located_span_text':fulltext[i:i+len(sp)]}
    if len(e_hits) > 1:
        return {'match_mode':'ambiguous_span','span_start':None,'span_end':None,'located_span_text':None}
    # 第二層 normalized (建 normalize→原文 offset 映射)
    norm_chars = []   # normalize 後每個字元
    orig_idx = []     # 對應原文 index
    for oi, ch in enumerate(fulltext):
        n = _normalize(ch)
        for nc in n:
            norm_chars.append(nc); orig_idx.append(oi)
    norm_ft = ''.join(norm_chars)
    norm_sp = _normalize(sp)
    if not norm_sp:
        return {'match_mode':'not_located','span_start':None,'span_end':None,'located_span_text':None}
    # 找所有命中
    hits = []
    start = 0
    while True:
        j = norm_ft.find(norm_sp, start)
        if j < 0: break
        hits.append(j); start = j+1
    if len(hits) == 0:
        return {'match_mode':'not_located','span_start':None,'span_end':None,'located_span_text':None}
    if len(hits) > 1:
        return {'match_mode':'ambiguous_span','span_start':None,'span_end':None,'located_span_text':None}
    j = hits[0]
    o_start = orig_idx[j]
    o_end = orig_idx[min(j+len(norm_sp)-1, len(orig_idx)-1)] + 1
    return {'match_mode':'normalized','span_start':o_start,'span_end':o_end,'located_span_text':fulltext[o_start:o_end]}

def role_of_span(fulltext, span_text):
    """給 evidence_span, 回 dict {match_mode, span_start, span_end, located_span_text, l1_role, l2_role}.
    定位用 exact-first (locate_span); 定位失敗則 role=not_located/ambiguous_span, 不猜位置.
    """
    loc = locate_span(fulltext, span_text)
    if loc['match_mode'] in ('not_located','ambiguous_span'):
        return {**loc, 'l1_role':loc['match_mode'], 'l2_role':loc['match_mode']}
    idx = loc['span_start']
    segs = segment(fulltext)
    l1 = 'unknown_section'
    for sg in segs:
        if sg['start'] <= idx < sg['end']:
            l1 = sg['role']; break
    # 獨立的 原告主張/被告抗辯 段 → 直接回 (不進 Layer2)
    if l1 in ('原告主張', '被告抗辯'):
        return {**loc, 'l1_role':l1, 'l2_role':l1}
    # 理由/事實/事實及理由/主文 段 → 取 span 所在【完整句】
    # 完整句很重要: 法院駁斥句「上訴人抗辯…云云, 無足採信」前半在 span 前、駁斥 cue 在 span 後
    sstart = idx
    while sstart > 0 and fulltext[sstart-1] not in '。！？\n':
        sstart -= 1
    send = loc['span_end']
    steps = 0
    while send < len(fulltext) and fulltext[send] not in '。！？\n' and steps < 200:
        send += 1; steps += 1
    sent = fulltext[sstart:send+1]   # 完整句, 涵蓋 span 前的主張 + span 後的駁斥 cue
    tail = fulltext[idx:idx+120]   # 近鄰窗供 legal_rule→court 升級
    # 護欄: 主文段只在 span 句有理由訊號才進 Layer2; 純主文結果句 = disposition (只撐判決結果)
    if l1 == '主文':
        if _ReasoningInMainText.search(sent):
            sub = _sentence_role(sent, tail)
            if sub == 'unknown_section':
                sub = 'court_reasoning'  # 主文段內有理由訊號但細判不出 → 視為法院論理 (簡易判決常態)
        else:
            return {**loc, 'l1_role':l1, 'l2_role':'disposition'}  # 純主文結果句
        return {**loc, 'l1_role':l1, 'l2_role':sub}
    sub = _sentence_role(sent, tail)
    if sub == 'unknown_section':
        # 回看 ~80 字找 party/rejection/court 信號 (主張常是長句, span 可能落句中)
        look_back = fulltext[max(0,idx-80):send+1]
        if PARTY_RE.search(look_back):
            # 同窗有駁斥 cue → court_rejection, 否則 party
            if REJECTION_RE.search(look_back):
                sub = 'court_rejection_of_party_argument'
            else:
                sub = 'party_embedded_claim'
        else:
            for sig in COURT_SIGNALS:
                if sig in look_back:
                    sub = 'court_reasoning'; break
    return {**loc, 'l1_role':l1, 'l2_role':sub}

# ---- supported 准入判定 (deterministic 規則) ----
def can_support(l1_role, l2_role, claim_kind='case_holding'):
    """回 (allowed:bool, reason).
    claim_kind:
      case_holding   - 本案法院見解 (court_reasoning 可撐)
      rejection_holding - 法院不採某抗辯 (court_rejection_of_party_argument 可撐)
      abstract_rule  - 抽象法律規則 (legal_rule_recitation 可撐)
      fact           - 事實認定 (fact_finding 可撐)
      party_position - 當事人主張內容 (⚠️不得由 court_rejection 支撐, 因被駁斥)
    """
    if l2_role in ('not_located','ambiguous_span'):
        return (False, f'span_{l2_role}')   # 定位不到/不唯一 → 不得 supported
    # disposition (純主文結果句): 只撐「判決結果」claim, 不撐法律見解
    if l2_role == 'disposition':
        if claim_kind == 'case_outcome':
            return (True, 'disposition')
        return (False, 'disposition_cannot_support_legal_opinion')
    # 純當事人主張 → 不得支撐法院見解
    if l2_role == 'party_embedded_claim' or l1_role in ('原告主張','被告抗辯'):
        return (False, 'party_argument_as_holding')
    # 法院駁斥當事人主張: 可撐「法院不採該抗辯」, 不可撐「被駁斥的主張本身」
    if l2_role == 'court_rejection_of_party_argument':
        if claim_kind == 'rejection_holding':
            return (True, 'court_rejection_of_party_argument')
        if claim_kind == 'party_position':
            return (False, 'rejected_party_argument_cannot_support_party_position')
        # 當 case_holding: 法院駁斥本身也是一種法院見解 (不採=見解), 准
        if claim_kind == 'case_holding':
            return (True, 'court_rejection_as_holding')
        return (False, 'rejection_role_mismatch')
    if l2_role == 'court_reasoning':
        if claim_kind in ('case_holding','rejection_holding'):
            return (True, 'court_reasoning')
        return (False, 'court_reasoning_role_mismatch')
    # court_application_reasoning: 本案適用結論, 撐 case_holding; 不撐 abstract_rule/party_position
    if l2_role == 'court_application_reasoning':
        if claim_kind == 'case_holding':
            return (True, 'court_application_reasoning')
        if claim_kind in ('abstract_rule','party_position'):
            return (False, f'application_cannot_support_{claim_kind}')
        return (False, 'application_role_mismatch')
    # legal_rule_recitation: 只撐抽象規則, 不撐本案見解/結果/適用
    if l2_role == 'legal_rule_recitation':
        if claim_kind == 'abstract_rule':
            return (True, 'legal_rule_recitation')
        return (False, 'legal_rule_cannot_support_case_holding')
    if l2_role == 'fact_finding' or l1_role == '事實':
        if claim_kind == 'fact':
            return (True, 'fact_finding')
        return (False, 'fact_finding_cannot_support_legal_opinion')
    return (False, 'unknown_section_needs_review')
