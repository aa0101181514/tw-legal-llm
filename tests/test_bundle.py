"""Offline tests for the bundle builder (no network, no LLM)."""

from twlegalrag.bundle import build_bundle
from twlegalrag.retrieval import Judgment


def _judgment(rank, doc_id, citation_text, fulltext=""):
    return Judgment(
        rank=rank,
        doc_id=doc_id,
        citation_text=citation_text,
        court_name="某法院",
        jdate="20000911",
        snippet="〔損害賠償〕| 判決結果: 原告勝訴",
        citation_url="https://dr-lawbot.com/fullview/X",
        citation_markdown="",
        result_token="tok",
        fulltext=fulltext,
        cited_articles=["民法第184條"],
    )


def test_bundle_has_stable_citation_ids():
    js = [
        _judgment(1, "MLDM,89,交易,54,20000911", "甲案", "理由甲"),
        _judgment(2, "TPSV,100,台上,1,20110101", "乙案", "理由乙"),
    ]
    b = build_bundle("我的問題", js)
    assert b["allowed_citations"] == ["J1", "J2"]
    assert b["judgments"][0]["citation_id"] == "J1"
    assert b["judgments"][1]["citation_id"] == "J2"
    assert b["retrieval_only"] is True


def test_bundle_carries_verification_instructions():
    b = build_bundle("q", [_judgment(1, "MLDM,89,交易,54,20000911", "甲案", "理由")])
    vi = b["verification_instructions"]
    assert vi["required"] is True
    assert len(vi["rules"]) >= 5
    # Every judgment carries a per-item warning about party-vs-court.
    assert b["judgments"][0]["warning"]


def test_bundle_marks_truncation():
    big = "字" * 9000
    b = build_bundle("q", [_judgment(1, "MLDM,89,交易,54,20000911", "甲案", big)])
    assert b["judgments"][0]["fulltext_truncated"] is True
    assert len(b["judgments"][0]["fulltext_excerpt"]) == 6000
