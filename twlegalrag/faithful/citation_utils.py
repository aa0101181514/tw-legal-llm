"""citation_utils — 台灣判決引用字號的正規化與比對純函式。

零依賴, 只用 re + unicodedata (canonical key / jcase 正規化 / doc_id 前綴→法院名)。

提供的函式:
  normalize_citation_text / normalize_jcase / canonical_citation_key
  doc_id_citation_key / jcase_query_variants / parse_citations_from_text
  court_name_from_doc_id (比對法院身份用)

這裡只負責「字號正規化 / 比 key / 解析法院」的純邏輯。
「AI 引用身份是否 == selected_doc_id」的判斷在 verifier.py, 不在這。
"""
from __future__ import annotations
import re
import unicodedata

# ── citation 正規化 + canonical key ──

_RE_PARSE_CANONICAL = re.compile(r'(\d{2,3})\s*年度?\s*(\S{1,10}?)\s*字第\s*(\d+)\s*號')
_ORD_CN = "一二三四五六七八九十"
_RE_JCASE_PAREN_ORD = re.compile(r"(更|緝)\(([" + _ORD_CN + r"])\)")


def normalize_citation_text(cit: str) -> str:
    """NFKC + 台→臺 + 去空白 + strip markdown/引號標點. 保持可讀供 regex。"""
    if not cit:
        return ""
    s = unicodedata.normalize("NFKC", cit)
    s = s.replace("台", "臺")
    s = re.sub(r"\s+", "", s)
    return s.strip("`*_*[]()（）「」『』,，:：;；.。")


def _ordinal_to_canonical(s: str) -> str:
    """更審序數統一國字形: 上更(一)/上更㈠(NFKC→(一)) → 上更一 (不受末尾 strip 破壞)。"""
    return _RE_JCASE_PAREN_ORD.sub(lambda m: f"{m.group(1)}{m.group(2)}", s)


def normalize_jcase(jcase: str) -> str:
    """jcase token 正規化 (canonical=臺+國字序數), 上更(一)/㈠/一 收斂單一形。"""
    s = unicodedata.normalize("NFKC", jcase)
    s = _ordinal_to_canonical(s)
    s = normalize_citation_text(s)
    s = re.sub(r"^.*法院", "", s)
    return s


def jcase_query_variants(jcase: str) -> list[str]:
    """DB 查詢變體: 台/臺 + 更審序數三編碼 (括號(一)/圈號㈠/國字一) 反向展開。"""
    norm = normalize_jcase(jcase)
    base = {norm, norm.replace("臺", "台"), norm.replace("台", "臺")}
    variants: set[str] = set()
    for v in base:
        variants.add(v)
        for i, cn in enumerate(_ORD_CN):
            m = re.search(r"(更|緝)" + cn + r"(?=$|[^" + _ORD_CN + r"])", v)
            if m:
                circ = chr(0x3220 + i)  # ㈠=U+3220 .. ㈩
                variants.add(re.sub(r"(更|緝)" + cn + r"(?=$|[^" + _ORD_CN + r"])",
                                    lambda mm: f"{mm.group(1)}({cn})", v))
                variants.add(re.sub(r"(更|緝)" + cn + r"(?=$|[^" + _ORD_CN + r"])",
                                    lambda mm: f"{mm.group(1)}{circ}", v))
    return [v for v in variants if v]


def canonical_citation_key(cit: str) -> tuple[str, str, str] | None:
    """citation text → (jyear, jcase, jno); 短長形指同案回同 key。"""
    if not cit:
        return None
    cit = normalize_citation_text(cit)
    m = _RE_PARSE_CANONICAL.search(cit)
    if not m:
        return None
    return (m.group(1), normalize_jcase(m.group(2)), m.group(3))


def doc_id_citation_key(doc_id: str) -> tuple[str, str, str] | None:
    """canonical doc_id → (jyear, jcase, jno). e.g. TPHM,106,上易,634,20180101,1。"""
    if not doc_id:
        return None
    parts = [p.strip() for p in doc_id.split(",")]
    if len(parts) < 4:
        return None
    jyear, jcase, jno = parts[1], normalize_jcase(parts[2]), parts[3]
    if not (jyear and jcase and jno):
        return None
    return (jyear, jcase, jno)


# ── citation 抽取 ──

_RE_FULL = re.compile(
    r'(?:臺灣|最高|高等|花蓮|臺中|臺南|高雄|臺北|新北|桃園|基隆|新竹|苗栗|彰化|南投|雲林|嘉義|屏東|宜蘭|澎湖|金門|連江)'
    r'[^\n]{5,40}?(?:字第\s*\d+\s*號)'
)
_RE_SHORT = re.compile(r'\d{2,3}\s*年度[^\n年院判]{2,30}?字第\s*\d+\s*號')


def parse_citations_from_text(text: str) -> list[str]:
    """從答案 text 抽判決字號 (FULL+SHORT, 去重保序)。"""
    if not text:
        return []
    seen, out = set(), []
    for m in _RE_FULL.findall(text) + _RE_SHORT.findall(text):
        s = m.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


# ── 法院身份 (wrong_doc_identity 用) ──
# doc_id 前綴碼 → 法院名. 用於比 AI citation 寫的法院 vs selected_doc_id 真實法院。
COURT_CODE_TO_NAME: dict[str, str] = {
    "TPS": "最高法院", "TPSM": "最高法院", "TPSV": "最高法院", "TPSU": "最高法院", "TPUA": "最高法院",
    "TPA": "最高行政法院", "TPAV": "最高行政法院", "TPAA": "最高行政法院",
    "TPH": "臺灣高等法院", "TPHM": "臺灣高等法院", "TPHV": "臺灣高等法院", "TPHA": "臺灣高等法院", "TPHU": "臺灣高等法院",
    "TCH": "臺灣高等法院臺中分院", "TCHM": "臺灣高等法院臺中分院", "TCHV": "臺灣高等法院臺中分院",
    "TNH": "臺灣高等法院臺南分院", "TNHM": "臺灣高等法院臺南分院", "TNHV": "臺灣高等法院臺南分院",
    "KSH": "臺灣高等法院高雄分院", "KSHM": "臺灣高等法院高雄分院", "KSHV": "臺灣高等法院高雄分院",
    "HLH": "臺灣高等法院花蓮分院", "HLHM": "臺灣高等法院花蓮分院", "HLHV": "臺灣高等法院花蓮分院",
    "KMH": "福建高等法院金門分院", "KMHM": "福建高等法院金門分院", "KMHV": "福建高等法院金門分院",
    "TPB": "臺北高等行政法院", "TPBA": "臺北高等行政法院",
    "TCB": "臺中高等行政法院", "TCBA": "臺中高等行政法院",
    "KSB": "高雄高等行政法院", "KSBA": "高雄高等行政法院",
    "IPC": "智慧財產及商業法院", "IPCA": "智慧財產及商業法院", "IPCM": "智慧財產及商業法院", "IPCV": "智慧財產及商業法院",
    # 地院主要碼 (常見, 非全量; 缺漏回 None 由 verifier 標 unknown 不誤判)
    "TPD": "臺灣臺北地方法院", "PCD": "臺灣新北地方法院", "SLD": "臺灣士林地方法院",
    "TYD": "臺灣桃園地方法院", "SCD": "臺灣新竹地方法院", "MLD": "臺灣苗栗地方法院",
    "TCD": "臺灣臺中地方法院", "CHD": "臺灣彰化地方法院", "NTD": "臺灣南投地方法院",
    "ULD": "臺灣雲林地方法院", "CYD": "臺灣嘉義地方法院", "TND": "臺灣臺南地方法院",
    "KSD": "臺灣高雄地方法院", "PTD": "臺灣屏東地方法院", "TTD": "臺灣臺東地方法院",
    "HLD": "臺灣花蓮地方法院", "ILD": "臺灣宜蘭地方法院", "KLD": "臺灣基隆地方法院",
    "PHD": "臺灣澎湖地方法院", "KMD": "福建金門地方法院", "LCD": "福建連江地方法院",
    "KSY": "臺灣高雄少年及家事法院", "TYH": "臺灣桃園地方法院",
    # 地方行政訴訟庭 (2026 行政訴訟改制, 各地院設; *TA 結尾). 這類代碼若缺漏, 易被 2 字母 fallback 誤判。
    "TPTA": "臺北高等行政法院地方行政訴訟庭", "TCTA": "臺中高等行政法院地方行政訴訟庭",
    "KSTA": "高雄高等行政法院地方行政訴訟庭", "TNTA": "高雄高等行政法院地方行政訴訟庭",
}

# 案類 (jcase) 前綴 → 法院所在地 hint (jcase 案類前綴比 doc_id 2字母 fallback 更可靠).
# 簡易庭/專庭案類常以地名簡稱起頭, 用於 court-identity 衝突時的第三方信號。
JCASE_PLACE_HINT: dict[str, str] = {
    "營簡": "臺南", "沙簡": "臺中", "六簡": "雲林", "豐簡": "臺中", "潭簡": "臺中",
    "中簡": "臺中", "南簡": "臺南", "雄簡": "高雄", "鳳簡": "高雄", "岡簡": "高雄",
    "屏簡": "屏東", "潮簡": "屏東", "竹簡": "新竹", "苗簡": "苗栗", "彰簡": "彰化",
    "投簡": "南投", "嘉簡": "嘉義", "朴簡": "嘉義", "北簡": "臺北", "板簡": "新北",
    "重簡": "新北", "士簡": "士林", "湖簡": "士林", "桃簡": "桃園", "壢簡": "桃園",
    "基簡": "基隆", "宜簡": "宜蘭", "羅簡": "宜蘭", "花簡": "花蓮", "東簡": "臺東",
    "澎簡": "澎湖", "金簡": "金門", "新簡": "新北", "店簡": "新北", "三簡": "新北",
    "稅簡": None,  # 稅簡 跨地院+地行訴訟庭, 不單獨定地, 交其他信號
}


def jcase_place_hint(jcase: str) -> str | None:
    """從 jcase 前綴抓法院所在地 hint (None=無把握). 供 verifier 第三方信號比對。"""
    if not jcase:
        return None
    j = normalize_jcase(jcase)
    for pref, place in JCASE_PLACE_HINT.items():
        if j.startswith(pref):
            return place
    return None


# 2 字母「院別+地區」碼 → 法院 family (不把簡易庭院區當法院名).
# doc_id prefix = 2字母地區碼 + 庭別碼(D普通/E簡易/H高分院/S最高/B高行政/A行政...) + 1字母(V民/M刑/A行政...)
# 同地區所有庭別 (KSD/KSE...) 都解到同法院 family; 高院/行政/最高由 3 碼精確表先吃掉。
COURT_REGION2_FAMILY: dict[str, str] = {
    "TP": "臺灣臺北地方法院", "PC": "臺灣新北地方法院", "SL": "臺灣士林地方法院",
    "TY": "臺灣桃園地方法院", "SC": "臺灣新竹地方法院", "ML": "臺灣苗栗地方法院",
    "TC": "臺灣臺中地方法院", "CH": "臺灣彰化地方法院", "NT": "臺灣南投地方法院",
    "UL": "臺灣雲林地方法院", "CY": "臺灣嘉義地方法院", "TN": "臺灣臺南地方法院",
    "KS": "臺灣高雄地方法院", "PT": "臺灣屏東地方法院", "TT": "臺灣臺東地方法院",
    "HL": "臺灣花蓮地方法院", "IL": "臺灣宜蘭地方法院", "KL": "臺灣基隆地方法院",
    "PH": "臺灣澎湖地方法院", "KM": "福建金門地方法院", "LC": "福建連江地方法院",
    "SY": "臺灣高雄少年及家事法院", "IP": "智慧財產及商業法院",
    # 簡易庭獨立院區碼 (E 結尾簡易庭常用前 2 碼是簡易庭所在地簡稱, 對齊地院):
    "CT": "臺灣臺中地方法院", "CD": "臺灣臺中地方法院", "SJ": "臺灣士林地方法院",
    "ST": "臺灣新北地方法院", "FS": "臺灣高雄地方法院", "NH": "臺灣士林地方法院",
    "FY": "臺灣臺中地方法院", "CL": "臺灣桃園地方法院", "CP": "臺灣臺中地方法院",
    "SD": "臺灣臺南地方法院", "GS": "臺灣高雄地方法院", "CC": "臺灣嘉義地方法院",
    "SS": "臺灣新北地方法院", "PK": "臺灣屏東地方法院", "PD": "臺灣屏東地方法院",
    "HU": "臺灣雲林地方法院", "JC": "臺灣基隆地方法院", "LT": "臺灣高雄地方法院",
    "MK": "臺灣澎湖地方法院", "OL": "臺灣臺中地方法院", "TL": "臺灣臺中地方法院",
}


COURT_REGION2_VENUE_ALIAS: dict[str, tuple[str, ...]] = {
    "CT": ("臺中簡易庭", "臺中"),
    "CD": ("臺中簡易庭", "臺中"),
    "SJ": ("士林簡易庭", "士林"),
    "ST": ("新店簡易庭", "新店"),
    "FS": ("鳳山簡易庭", "鳳山"),
    "NH": ("內湖簡易庭", "內湖"),
    "FY": ("豐原簡易庭", "豐原"),
    "CL": ("中壢簡易庭", "中壢"),
    "CP": ("沙鹿簡易庭", "沙鹿"),
    "SD": ("善化簡易庭", "善化"),
    "GS": ("岡山簡易庭", "岡山"),
    "CC": ("朴子簡易庭", "朴子"),
    "SS": ("三重簡易庭", "三重"),
    "PK": ("屏東簡易庭", "屏東"),
    "PD": ("潮州簡易庭", "潮州"),
    "HU": ("虎尾簡易庭", "虎尾"),
    "JC": ("基隆簡易庭", "基隆"),
    "LT": ("旗山簡易庭", "旗山"),
    "MK": ("馬公簡易庭", "馬公"),
    "OL": ("沙鹿簡易庭", "沙鹿"),
    "TL": ("大里簡易庭", "大里"),
}

_COURT_PLACE_NAMES = (
    "臺北", "新北", "士林", "桃園", "新竹", "苗栗", "臺中", "彰化", "南投", "雲林",
    "嘉義", "臺南", "高雄", "屏東", "臺東", "花蓮", "宜蘭", "基隆", "澎湖", "金門",
    "連江", "橋頭", "智慧財產及商業", "智慧財產", "新店", "鳳山", "內湖", "豐原",
    "中壢", "沙鹿", "善化", "岡山", "朴子", "三重", "潮州", "虎尾", "旗山",
    "馬公", "大里",
)


def _court_token(text: str) -> str:
    """法院名/簡稱比對 token. 只供 verifier 身分比對, 不改 citation key。"""
    s = normalize_citation_text(text)
    s = s.replace("福建", "").replace("臺灣", "")
    replacements = (
        ("少年及家事法院", "少家法院"),
        ("地方法院", "地院"),
        ("高等行政法院", "高行政法院"),
        ("高等法院", "高院"),
        ("智慧財產及商業法院", "智商法院"),
    )
    for old, new in replacements:
        s = s.replace(old, new)
    return s


def _aliases_for_court_name(name: str) -> set[str]:
    aliases = {_court_token(name)}
    token = _court_token(name)
    for place in _COURT_PLACE_NAMES:
        p = _court_token(place)
        if p and p in token:
            if "地院" in token:
                aliases.update({_court_token(f"{place}地院"), _court_token(f"{place}地方法院")})
            if "高院" in token:
                aliases.update({_court_token(f"{place}高院"), _court_token(f"{place}高分院")})
            if "高行政法院" in token:
                aliases.update({_court_token(f"{place}高行政法院")})
            if "少家法院" in token:
                aliases.update({_court_token(f"{place}少家法院"), _court_token(f"{place}少年及家事法院")})
    if token == _court_token("最高法院"):
        aliases.update({_court_token("最高院"), _court_token("最高法院")})
    return {a for a in aliases if a}


_COURT_MENTION_RE = re.compile(
    # ⚠️ 最高行政法院 必須排在 最高法院 之前 (alternation 是有序的, 否則「最高法院」會先吃掉「最高」前綴)
    r"(最高行政法院|最高法院|最高院|臺灣高等法院(?:臺中|台中|臺南|台南|高雄|花蓮|金門)?分院|福建高等法院金門分院|臺灣高等法院|智慧財產及商業法院|智慧財產法院|智財法院|"
    r"(?:臺北|台北|新北|士林|桃園|新竹|苗栗|臺中|台中|彰化|南投|雲林|嘉義|臺南|台南|高雄|屏東|臺東|台東|花蓮|宜蘭|基隆|澎湖|金門|連江|橋頭|新店|鳳山|內湖|豐原|中壢|沙鹿|善化|岡山|朴子|三重|潮州|虎尾|旗山|馬公|大里)"
    r"(?:地方法院|地院|高等法院(?:臺中|台中|臺南|台南|高雄|花蓮|金門)?分院|高等法院|高院|高分院|高等行政法院|高行政法院|少年及家事法院|少家法院|簡易庭))"
)


def parse_court_mention(text: str) -> str | None:
    """從 AI citation/claim 抽法院提及, 支援地院/高分院/最高院/簡易庭等簡稱。"""
    if not text:
        return None
    s = normalize_citation_text(text)
    m = _COURT_MENTION_RE.search(s)
    if not m:
        return None
    mention = m.group(1)
    if mention == "最高院":
        mention = "最高法院"
    if mention in ("智財法院", "智慧財產法院"):
        mention = "智慧財產及商業法院"
    return _court_token(mention)


def court_name_from_doc_id(doc_id: str) -> str | None:
    """doc_id → 法院名。
    優先序: 精確表 (完整/4/3 碼) → 2 字母地區碼 fallback (cover 簡易庭)。
    真的解不出才回 None (verifier 對 None 不放過, 改 needs_review)。"""
    if not doc_id or "," not in doc_id:
        return None
    prefix = doc_id.split(",", 1)[0].strip().upper()
    for n in (len(prefix), 4, 3):
        cand = prefix[:n]
        if cand in COURT_CODE_TO_NAME:
            return COURT_CODE_TO_NAME[cand]
    # fallback: 2 字母地區碼 (cover 所有庭別/簡易庭), 回 family 不回半截院區名
    return COURT_REGION2_FAMILY.get(prefix[:2])


def court_resolution_confidence(doc_id: str) -> str:
    """doc_id 法院解析的可信度。
    'exact'     : 來自精確表 COURT_CODE_TO_NAME (完整/4/3 碼) — 可信, 可用於 fail。
    'fallback'  : 只來自 2 字母地區碼 (推測性, 部分代碼會解錯, 如橋頭 CTD 被誤判為臺中) — 不可用於 fail, 降 needs_review。
    'none'      : 解不出。
    ⚠️ wrong_court fail 只在 exact 才成立; fallback 一律降 needs_review(court_name_imprecise)。"""
    if not doc_id or "," not in doc_id:
        return "none"
    prefix = doc_id.split(",", 1)[0].strip().upper()
    for n in (len(prefix), 4, 3):
        if prefix[:n] in COURT_CODE_TO_NAME:
            return "exact"
    if COURT_REGION2_FAMILY.get(prefix[:2]):
        return "fallback"
    return "none"


def court_aliases_from_doc_id(doc_id: str) -> set[str]:
    """selected doc_id 可接受的法院身分 aliases (family + venue alias)."""
    if not doc_id or "," not in doc_id:
        return set()
    prefix = doc_id.split(",", 1)[0].strip().upper()
    aliases: set[str] = set()
    family = court_name_from_doc_id(doc_id)
    if family:
        aliases.update(_aliases_for_court_name(family))
    for venue in COURT_REGION2_VENUE_ALIAS.get(prefix[:2], ()):
        aliases.add(_court_token(venue))
    return {a for a in aliases if a}


def court_region_code(doc_id: str) -> str | None:
    """回 doc_id 的 2 字母地區碼 (院別身分核心). 用於 wrong_doc 比身分時, 院區一致即視同法院一致。"""
    if not doc_id or "," not in doc_id:
        return None
    return doc_id.split(",", 1)[0].strip().upper()[:2] or None
