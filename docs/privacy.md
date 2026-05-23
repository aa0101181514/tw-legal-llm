# Privacy

## What is logged

When you use `tw-legal-llm`, our backend logs:

- API key id (not the key itself).
- Tool name (`search_judgments` / `get_judgment_fulltext`).
- A **SHA-256 hash** of your query (never the raw query).
- The `doc_id` of fulltext requests.
- Response status, latency, and result count.
- Timestamp.

We log this for audit, abuse detection, and ISO 42001-aligned access control.

## What is NOT logged

- Raw query text.
- Your AI client's prompts, conversations, or generated answers.
- Anything the LLM (Claude / Cursor / etc.) sends back to you.

The LLM-side conversation stays between you and your LLM provider. We never
see it.

## Citations

`citation_url` points to `dr-lawbot.com/fullview/<doc_id>`, which renders the
public judgment. The same URL is what we publish on our SEO / GEO surfaces
and what Google / ChatGPT / Perplexity index.

## Data retention

API request logs are retained for operational use. We do not sell, share, or
re-purpose logs.

## Contact

Email `aa.0101181514@gmail.com` for privacy questions or to request log
deletion for your API key.
