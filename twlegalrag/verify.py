"""Citation check — bundle-level, best-effort.

This is NOT a semantic faithfulness verifier. It checks, with deterministic
string functions, only whether an answer's citations are consistent with the
retrieved bundle:

1. **Out-of-bundle detection.** Find every Taiwan case-number citation in the
   answer and check whether it corresponds to a judgment that was actually
   retrieved. A citation to a case that was never in the bundle is
   ``citation_no_doc`` — i.e. a plausible-looking but unsupplied case number.

2. **Wrong-doc identity.** For cited cases that *are* in the bundle, confirm the
   court/year/case-type/number key matches the retrieved judgment.

3. **Fake quote (narrow).** Check whether the answer's verbatim "the court
   said ..." quotes appear in the retrieved judgments' reasoning text. This is a
   pattern-based string match, not a semantic check.

What it CANNOT check: whether the court's reasoning was read correctly, whether
a party's argument was passed off as the court's holding, whether incidental
discussion was treated as the core holding, or any paraphrase-level error.
Those require reading the full judgment.

Every verdict is ``pass`` / ``needs_review`` / ``fail``, conservative by design:
ambiguous cases become ``needs_review``, never ``fail``. A ``pass`` means the
citation's identity checks out — not that the legal reasoning is correct.
Nothing here calls an LLM or a database — pure string functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .faithful import citation_utils as CU
from .faithful import verifier as V
from .retrieval import Judgment


@dataclass
class CitationVerdict:
    citation_text: str
    doc_id: Optional[str]          # matched retrieved judgment, or None if out-of-bundle
    status: str                    # pass | needs_review | fail
    reasons: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)


@dataclass
class VerifyReport:
    citations_found: int
    in_bundle: int
    out_of_bundle: int
    verdicts: list[CitationVerdict] = field(default_factory=list)
    fake_quote: dict = field(default_factory=dict)   # answer-level fake-quote check
    overall: str = "pass"                            # worst status across all checks


def citation_check(answer_text: str, judgments: list[Judgment]) -> VerifyReport:
    """Run the bundle-level citation check of ``answer_text`` against ``judgments``.

    Best-effort and deterministic; see the module docstring for what this does and
    does not check.
    """
    retrieved_doc_ids = [j.doc_id for j in judgments if j.doc_id]
    # Map canonical citation key -> retrieved judgment, so we can tell whether a
    # citation in the answer points at something we actually gave the model.
    key_to_judgment: dict[str, Judgment] = {}
    for j in judgments:
        k = CU.doc_id_citation_key(j.doc_id)
        if k:
            key_to_judgment.setdefault(k, j)

    # Use the verifier's own citation extractor (FULL + SHORT forms) then dedup
    # across forms by canonical key, so the same case cited in both long and
    # short form is not reported twice. Prefer the longer (court-qualified) form.
    by_key: dict[tuple, str] = {}
    for cit in CU.parse_citations_from_text(answer_text):
        ck = CU.canonical_citation_key(cit)
        if not ck:
            continue
        if ck not in by_key or len(cit) > len(by_key[ck]):
            by_key[ck] = cit
    citations = list(by_key.values())
    verdicts: list[CitationVerdict] = []
    in_bundle = out_of_bundle = 0

    for cit in citations:
        ck = CU.canonical_citation_key(cit)
        match = key_to_judgment.get(ck) if ck else None
        if match is None:
            out_of_bundle += 1
            verdicts.append(
                CitationVerdict(
                    citation_text=cit,
                    doc_id=None,
                    status="fail",
                    reasons=["citation_no_doc"],
                    detail={"note": "cited a case that was NOT among retrieved judgments"},
                )
            )
            continue
        in_bundle += 1
        r = V.check_wrong_doc_identity(cit, match.doc_id, retrieved_doc_ids)
        verdicts.append(
            CitationVerdict(
                citation_text=cit,
                doc_id=match.doc_id,
                status=r["status"],
                reasons=[r["reason"]],
                detail=r.get("detail", {}),
            )
        )

    # Answer-level fake-quote check: verify verbatim court quotes against the
    # concatenated reasoning text of all retrieved judgments that have full text.
    combined_fulltext = "\n\n".join(j.fulltext for j in judgments if j.fulltext)
    fq = V.check_fake_quote(answer_text, combined_fulltext, None)

    statuses = [v.status for v in verdicts] + [fq["status"]]
    if "fail" in statuses:
        overall = "fail"
    elif "needs_review" in statuses:
        overall = "needs_review"
    else:
        overall = "pass"

    return VerifyReport(
        citations_found=len(citations),
        in_bundle=in_bundle,
        out_of_bundle=out_of_bundle,
        verdicts=verdicts,
        fake_quote={"status": fq["status"], "reason": fq["reason"], "detail": fq.get("detail", {})},
        overall=overall,
    )


# Backwards-compatible alias.
verify_answer = citation_check
