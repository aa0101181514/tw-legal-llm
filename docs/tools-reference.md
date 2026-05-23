# Tools Reference

The TLL MCP client exposes two tools. Public contract only — no implementation
details are documented or supported as a public API.

## `search_judgments`

Search Taiwan court judgments by legal issue, keyword, case number, court name,
or statute. Returns citation-ready judgment metadata and short excerpts.

**Do not cite judgments not returned by this tool.**

### Input

| Field | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | Search terms in Traditional Chinese. |
| `search_type` | enum [`hybrid`, `keyword`, `phrase`] | no | Default `hybrid`. |
| `max_results` | integer (1-20) | no | Default 10. |

### Output

```json
{
  "results": [
    {
      "rank": 1,
      "doc_id": "TPHV,106,家抗,96,20171024,1",
      "citation_text": "臺灣高等法院 106 年度家抗字第 96 號",
      "court_name": "臺灣高等法院",
      "jdate": "2017-10-24",
      "case_category": "民事",
      "snippet": "...",
      "citation_url": "https://dr-lawbot.com/fullview/TPHV,106,家抗,96,20171024,1",
      "result_token": "<short-lived token>"
    }
  ]
}
```

Notes:

- `result_token` is required when calling `get_judgment_fulltext`. It is
  short-lived; do not store it long-term.
- Raw ranking scores are not returned.
- Snippets are truncated for citation use, not exhaustive reading.

### Errors

| Error | Meaning |
|---|---|
| `unauthorized` | API key is missing or invalid. |
| `quota_exceeded` | Daily search limit reached. |
| `invalid_request` | Request schema rejected. |
| `internal_error` | Backend error. Retry later. |

---

## `get_judgment_fulltext`

Retrieve available text for a judgment selected from search results. Use only
when more detail is needed for legal analysis.

**Citation must match exactly the `citation_text` from `search_judgments`.**

### Input

| Field | Type | Required | Notes |
|---|---|---|---|
| `doc_id` | string | yes | Doc id from a recent `search_judgments` result. |
| `result_token` | string | yes | From the search response that returned this `doc_id`. |

### Output

```json
{
  "doc_id": "TPHV,106,家抗,96,20171024,1",
  "citation_text": "臺灣高等法院 106 年度家抗字第 96 號",
  "court_name": "臺灣高等法院",
  "jdate": "2017-10-24",
  "text_excerpt": "...",
  "cited_articles": ["民法第1030-1條"],
  "citation_url": "https://dr-lawbot.com/fullview/TPHV,106,家抗,96,20171024,1"
}
```

Notes:

- Fulltext is capped to a usable excerpt length. Not the entire judgment in
  every case.
- `cited_articles` lists statutes cited by the judgment, where extractable.

### Errors

| Error | Meaning |
|---|---|
| `unauthorized` | API key is missing or invalid. |
| `fulltext_not_available` | Run `search_judgments` first and reuse its `result_token`. |
| `token_expired` | `result_token` has expired. Search again. |
| `quota_exceeded` | Daily fulltext limit reached. |
| `internal_error` | Backend error. Retry later. |

---

## Guidance for AI clients

Whether you are Claude, Cursor, or another MCP host, follow these rules:

1. **Always call `search_judgments` before answering**. If results are empty,
   say so rather than fabricating a citation.
2. **Cite using `citation_text`** exactly. Do not paraphrase the court name
   or case number.
3. **Call `get_judgment_fulltext`** only when search snippets are
   insufficient for the legal analysis the user requested.
4. **Distinguish search results from fulltext analysis** in your answer.
5. **Do not invent case numbers, court names, or statutes** that did not come
   from a tool response.
