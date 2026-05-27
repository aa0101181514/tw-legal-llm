"""Offline tests for the verification layer (no network, no LLM, no tokens)."""

from twlegalrag.retrieval import Judgment
from twlegalrag.verify import citation_check


def _judgment(rank, doc_id, citation_text, fulltext=""):
    return Judgment(
        rank=rank,
        doc_id=doc_id,
        citation_text=citation_text,
        court_name="",
        jdate="",
        snippet="",
        citation_url="",
        citation_markdown="",
        result_token="tok",
        fulltext=fulltext,
    )


def test_real_citation_passes():
    j = _judgment(1, "MLDM,89,交易,54,20000911", "臺灣苗栗地方法院 89 年度交易字第 54 號（刑事）")
    rep = citation_check("依臺灣苗栗地方法院 89 年度交易字第 54 號,法院認定過失。", [j])
    assert rep.overall == "pass"
    assert rep.in_bundle == 1
    assert rep.out_of_bundle == 0


def test_fabricated_citation_fails():
    j = _judgment(1, "MLDM,89,交易,54,20000911", "臺灣苗栗地方法院 89 年度交易字第 54 號（刑事）")
    rep = citation_check("另參最高法院 888 年度台上字第 99999 號判決。", [j])
    assert rep.overall == "fail"
    assert rep.out_of_bundle == 1
    assert any("citation_no_doc" in v.reasons for v in rep.verdicts)


def test_mixed_real_and_fake():
    j = _judgment(1, "MLDM,89,交易,54,20000911", "臺灣苗栗地方法院 89 年度交易字第 54 號（刑事）")
    answer = (
        "依臺灣苗栗地方法院 89 年度交易字第 54 號,被告有過失;"
        "另參最高法院 888 年度台上字第 99999 號,亦同。"
    )
    rep = citation_check(answer, [j])
    assert rep.overall == "fail"
    assert rep.in_bundle == 1
    assert rep.out_of_bundle == 1


def test_dedup_across_long_and_short_form():
    """Same case cited in long + short form counts once."""
    j = _judgment(1, "MLDM,89,交易,54,20000911", "臺灣苗栗地方法院 89 年度交易字第 54 號（刑事）")
    answer = "臺灣苗栗地方法院 89 年度交易字第 54 號;簡稱 89 年度交易字第 54 號。"
    rep = citation_check(answer, [j])
    assert rep.citations_found == 1


def test_no_citations_passes():
    j = _judgment(1, "MLDM,89,交易,54,20000911", "臺灣苗栗地方法院 89 年度交易字第 54 號（刑事）")
    rep = citation_check("一般性法律說明,沒有引用任何判決字號。", [j])
    assert rep.overall == "pass"
    assert rep.citations_found == 0
