"""Build a retrieval bundle for use with any external AI tool.

A *bundle* is a self-contained JSON package the user can hand to ChatGPT /
Claude / Gemini / a local model. It carries the retrieved judgments, stable
citation ids (J1, J2, ...), full-text excerpts, and an explicit set of
verification instructions telling the downstream model to cite only what is in
the bundle and to mark unsupported propositions as unverified.

This is retrieval-only. The bundle does not contain an answer and makes no
claim about the faithfulness of any answer later generated from it.
"""

from __future__ import annotations

from typing import Any

from .retrieval import Judgment

# Per-judgment full-text budget included in the bundle. Keeps total size
# reasonable for context windows while preserving the court's reasoning.
_EXCERPT_CHARS = 6000

_PER_JUDGMENT_WARNING = (
    "Use only the court's reasoning as authority. Do not quote party arguments, "
    "appellant/defendant submissions, or summaries of claims as the court's holding."
)

_VERIFICATION_INSTRUCTIONS: dict[str, Any] = {
    "required": True,
    "notice": (
        "This bundle is retrieval-only. Any answer generated from it must perform "
        "citation-faithfulness checks before presenting legal conclusions."
    ),
    "rules": [
        "Only cite judgments included in this bundle.",
        "Every legal proposition must cite a citation_id from allowed_citations.",
        "Do not treat party arguments, appellant arguments, defendant defenses, "
        "or summaries of claims as court holdings.",
        "Do not treat incidental discussion as the core holding of a judgment.",
        "If the cited judgment text does not clearly support a proposition, mark "
        "it as unverified.",
        "If the bundle is insufficient, say so instead of inventing authority.",
    ],
}

AI_USE_NOTICE = (
    "AI USE NOTICE:\n"
    "This is a retrieval package, not a verified legal answer.\n"
    "If you give this bundle to an AI model, require it to cite only citation_id "
    "values in this bundle and to mark unsupported propositions as unverified."
)


def build_bundle(query: str, judgments: list[Judgment]) -> dict[str, Any]:
    """Assemble the retrieval bundle dict from a query and retrieved judgments."""
    items = []
    allowed = []
    for i, j in enumerate(judgments, start=1):
        cid = f"J{i}"
        allowed.append(cid)
        excerpt = (j.fulltext or "")[:_EXCERPT_CHARS]
        items.append(
            {
                "citation_id": cid,
                "doc_id": j.doc_id,
                "citation_text": j.citation_text,
                "citation_url": j.citation_url,
                "court_name": j.court_name,
                "jdate": j.jdate,
                "case_category": j.case_category,
                "cited_articles": j.cited_articles,
                "listing": j.snippet,            # Layer-1 structured listing line
                "fulltext_excerpt": excerpt,
                "fulltext_truncated": bool(j.fulltext and len(j.fulltext) > _EXCERPT_CHARS),
                "warning": _PER_JUDGMENT_WARNING,
            }
        )
    return {
        "schema": "twlegalrag.bundle/v1",
        "query": query,
        "source": "Taiwan Legal RAG (TLR) retrieval endpoint",
        "retrieval_only": True,
        "allowed_citations": allowed,
        "judgments": items,
        "verification_instructions": _VERIFICATION_INSTRUCTIONS,
    }
