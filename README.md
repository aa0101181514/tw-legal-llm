# TW Legal LLM (TLL)

> Bring Taiwan court judgments to your AI client. Free, citation-ready, BYO-LLM.

`tw-legal-llm` is an MCP (Model Context Protocol) client that lets Claude
Desktop, Cursor, and other MCP-compatible AI clients search and read Taiwan
court judgments. Your AI client generates the answers; we just provide the
judgments and citations.

- ✅ **No vendor lock-in** — works with Claude, Cursor, Cline, or any MCP host.
- ✅ **You bring the LLM** — uses your own Claude Pro / Cursor / etc. subscription.
- ✅ **Citation-ready** — every result includes a verified court citation
  and a link to the judgment on dr-lawbot.com.
- ✅ **Audited access** — ISO 42001-aligned access logs on the server side.
- ✅ **Apache 2.0** — open client, simple install.

## Install (Claude Desktop)

Paste this into your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tw-legal-llm": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/aa0101181514/tw-legal-llm",
        "tw-legal-llm"
      ],
      "env": {
        "TLL_API_KEY": "tll_xxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

Restart Claude Desktop. Two tools will appear:
`search_judgments` and `get_judgment_fulltext`.

> Need an API key? Email Aaron at `aa.0101181514@gmail.com` (manual issue
> during early access — no signup form yet).

## Install (Cursor)

```json
{
  "mcpServers": {
    "tw-legal-llm": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/aa0101181514/tw-legal-llm",
        "tw-legal-llm"
      ],
      "env": {
        "TLL_API_KEY": "tll_xxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

## What the tools do

See [`docs/tools-reference.md`](docs/tools-reference.md) for the public tool
contract.

In short:

- **`search_judgments`** — search Taiwan court judgments by legal issue,
  keyword, case number, court name, or statute. Returns ranked judgment
  metadata and short excerpts.
- **`get_judgment_fulltext`** — retrieve available text for a judgment
  selected from search results.

## How it works

This package contains a thin MCP client. The actual retrieval runs on
`tll.dr-lawbot.com`. We don't open-source the retrieval implementation
because the value is in the data quality and curation, not the algorithm.

What we *do* publish:

- This MCP client.
- The tool contract (inputs, outputs, error codes).
- Usage docs and config examples.

What we *don't* publish:

- Backend retrieval code, ranking, prompts, or thresholds.
- Quota and abuse-detection rules.
- Internal stack details.

## Limitations

- Free tier has daily limits. You'll get an opaque rate-limit error if you
  hit them.
- Some judgments may not have full text available.
- The LLM (Claude, Cursor, etc.) is responsible for the final answer.
  Citations are guaranteed by us; answer quality depends on your LLM.

## Privacy

Your queries are logged (hashed) on our server for audit and abuse
detection. We do not log full-text query content. See
[`docs/privacy.md`](docs/privacy.md).

## License

Apache 2.0. See [LICENSE](LICENSE).

## Contact

- GitHub Issues: https://github.com/aa0101181514/tw-legal-llm/issues
- Email (API key requests, partnerships): `aa.0101181514@gmail.com`
