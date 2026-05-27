"""Stage 1 — TLR retrieval client.

Talks to the public Taiwan Legal RAG API (default ``https://tlr.dr-lawbot.com``):

  POST /v1/search    — hybrid/keyword/phrase search over ~21M judgments.
                       Returns a structured Layer-1 *listing* per hit
                       (court / verdict / cited articles / type) plus a
                       short-lived ``result_token``. NOT reasoning text.
  POST /v1/fulltext  — given a doc_id + result_token, returns the judgment's
                       reasoning full text. THIS is what citation verification
                       needs — the listing alone has no holding text.

Design notes baked in from production experience:

* **strict=False JSON.** TLR responses embed raw control characters (full-width
  spaces, unescaped newlines from judgment text). A strict JSON parser rejects
  them — this is the same failure that breaks OpenAI's Action layer. We parse
  leniently so the CLI is robust where stricter clients are not.
* **result_token reuse.** One search returns a single token that encodes the
  whole result set; pass it back unchanged when fetching any hit's full text.
* **Public, authless by default.** A Bearer key is optional — supply one only
  if the server operator issued you one (it just lets them attribute your
  traffic in their logs). Per-IP rate limiting applies regardless.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

DEFAULT_BASE_URL = "https://tlr.dr-lawbot.com"
_SEARCH_PATH = "/v1/search"
_FULLTEXT_PATH = "/v1/fulltext"
_HEALTH_PATH = "/v1/health"


class RetrievalError(RuntimeError):
    """Raised when the TLR API cannot serve a request."""


@dataclass
class Judgment:
    """One search hit. ``fulltext``/``cited_articles`` populated after fetch_fulltext."""

    rank: int
    doc_id: str
    citation_text: str
    court_name: str
    jdate: str
    snippet: str          # Layer-1 listing line (NOT reasoning text)
    citation_url: str
    citation_markdown: str
    result_token: str
    case_category: Optional[str] = None
    # filled in by fetch_fulltext():
    fulltext: Optional[str] = None
    cited_articles: list[str] = field(default_factory=list)

    @property
    def has_fulltext(self) -> bool:
        return bool(self.fulltext)


def _loads_lenient(text: str):
    """Parse JSON tolerating embedded control characters (see module docstring)."""
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise RetrievalError(f"TLR returned unparseable JSON: {exc}") from exc


class TLRClient:
    """Thin client over the TLR retrieval API. Carries no LLM, no DB, no keys."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    # -- context manager so callers can `with TLRClient() as c:` --------------
    def __enter__(self) -> "TLRClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _post(self, path: str, body: dict) -> dict:
        url = self.base_url + path
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.post(url, headers=self._headers(), json=body)
            except httpx.HTTPError as exc:
                last_exc = exc
                time.sleep(0.6 * (attempt + 1))
                continue
            if resp.status_code == 429:
                # Per-IP rate limit. Back off and retry within budget.
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise RetrievalError(
                    "TLR rate limit hit (HTTP 429). Slow down or request an API key."
                )
            if resp.status_code == 503:
                raise RetrievalError(
                    "TLR service unavailable (HTTP 503) — the operator may have the "
                    "kill switch engaged."
                )
            data = _loads_lenient(resp.text)
            if resp.status_code >= 400:
                detail = data.get("detail", data) if isinstance(data, dict) else data
                raise RetrievalError(f"TLR error (HTTP {resp.status_code}): {detail}")
            return data
        raise RetrievalError(f"TLR request failed after retries: {last_exc}")

    # -- public API -----------------------------------------------------------
    def health(self) -> dict:
        resp = self._client.get(self.base_url + _HEALTH_PATH, headers=self._headers())
        return _loads_lenient(resp.text)

    def search(
        self,
        query: str,
        *,
        search_type: str = "hybrid",
        max_results: int = 5,
    ) -> list[Judgment]:
        """Search judgments. Returns Layer-1 listings (no reasoning text yet)."""
        if search_type not in ("hybrid", "keyword", "phrase"):
            raise ValueError("search_type must be hybrid | keyword | phrase")
        max_results = max(1, min(int(max_results), 10))  # server caps at 10
        data = self._post(
            _SEARCH_PATH,
            {"query": query, "search_type": search_type, "max_results": max_results},
        )
        results = data.get("results", []) if isinstance(data, dict) else []
        out: list[Judgment] = []
        for r in results:
            out.append(
                Judgment(
                    rank=r.get("rank", len(out) + 1),
                    doc_id=r.get("doc_id", ""),
                    citation_text=r.get("citation_text", ""),
                    court_name=r.get("court_name", ""),
                    jdate=r.get("jdate", ""),
                    snippet=r.get("snippet", ""),
                    citation_url=r.get("citation_url", ""),
                    citation_markdown=r.get("citation_markdown", ""),
                    result_token=r.get("result_token", ""),
                    case_category=r.get("case_category"),
                )
            )
        return out

    def fetch_fulltext(self, judgment: Judgment) -> Judgment:
        """Fetch reasoning full text for a hit and populate it in place.

        Required before citation verification: the search listing has no holding
        text, so faithfulness checks have nothing to compare against without this.
        """
        if not judgment.result_token:
            raise RetrievalError(
                f"{judgment.doc_id}: no result_token (fetch via search() first)."
            )
        data = self._post(
            _FULLTEXT_PATH,
            {"doc_id": judgment.doc_id, "result_token": judgment.result_token},
        )
        judgment.fulltext = data.get("text_excerpt", "") if isinstance(data, dict) else ""
        judgment.cited_articles = (
            data.get("cited_articles") or [] if isinstance(data, dict) else []
        )
        return judgment

    def search_and_read(
        self,
        query: str,
        *,
        search_type: str = "hybrid",
        max_results: int = 5,
        read_top: Optional[int] = None,
    ) -> list[Judgment]:
        """Search then fetch full text for the top ``read_top`` hits (default all).

        This is the one-call retrieval the CLI uses: locate via search, then read
        reasoning text so the bundle and the citation check have real holding text.
        """
        hits = self.search(query, search_type=search_type, max_results=max_results)
        n = len(hits) if read_top is None else min(read_top, len(hits))
        for j in hits[:n]:
            try:
                self.fetch_fulltext(j)
            except RetrievalError:
                # Leave fulltext empty; downstream verifier degrades to
                # needs_review rather than failing on missing text.
                pass
        return hits
