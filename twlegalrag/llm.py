"""Stage 2 — answer with the USER's own LLM account.

No server-side LLM, no shared keys. The caller supplies their own credentials
via config/env and picks a provider:

* ``openai``       — OpenAI Chat Completions (needs ``openai`` extra).
* ``anthropic``    — Anthropic Messages (needs ``anthropic`` extra).
* ``openai-compat``— any OpenAI-compatible ``/chat/completions`` endpoint,
  e.g. Zhipu GLM, Together, Groq, a local vLLM/Ollama gateway. Set
  ``base_url`` to that endpoint.

The provider is given the user's question plus the *reasoning full text* of the
retrieved judgments, and asked to ground its analysis only in those judgments.
It must cite using the exact ``citation_text`` we pass in — that contract is
what makes Stage 3 (faithfulness verification) meaningful.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator, Optional

from .retrieval import Judgment

# Per-judgment full-text budget fed to the LLM. Mirrors production Ask behaviour
# (~4k chars/judgment) to keep total context bounded.
_PER_DOC_CHARS = 4000

_SYSTEM_PROMPT = (
    "你是資深臺灣法律分析師。根據使用者問題與下方檢索到的判決全文,"
    "以白話文提供法律分析。\n"
    "嚴格規則:\n"
    "1. 只能引用下方提供的判決,不得引用未提供的任何字號或見解。\n"
    "2. 引用判決時,必須使用提供的「引用字號」原文(完整 citation_text),不得改寫。\n"
    "3. 描述某判決的法院見解時,必須忠於該判決全文,不得把當事人主張寫成法院見解,"
    "不得虛構引文。\n"
    "4. 若提供的判決不足以回答,直說資料不足,不要編造。\n"
    "輸出結構: 先白話結論,再法律分析(引用具體判決),最後 2-4 點行動建議。"
)


@dataclass
class LLMConfig:
    provider: str = "openai"           # openai | anthropic | openai-compat
    model: str = "gpt-4o"
    api_key: Optional[str] = None
    base_url: Optional[str] = None      # for openai-compat
    temperature: float = 0.2
    max_tokens: int = 2000

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Build config from TWLEGALRAG_* env vars, falling back to provider defaults."""
        provider = os.environ.get("TWLEGALRAG_LLM_PROVIDER", "openai")
        key = os.environ.get("TWLEGALRAG_LLM_API_KEY")
        if not key:
            # Fall back to the provider's conventional env var.
            key = {
                "openai": os.environ.get("OPENAI_API_KEY"),
                "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
                "openai-compat": os.environ.get("OPENAI_API_KEY"),
            }.get(provider)
        default_model = {
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-20250514",
            "openai-compat": "glm-4",
        }.get(provider, "gpt-4o")
        return cls(
            provider=provider,
            model=os.environ.get("TWLEGALRAG_LLM_MODEL", default_model),
            api_key=key,
            base_url=os.environ.get("TWLEGALRAG_LLM_BASE_URL"),
            temperature=float(os.environ.get("TWLEGALRAG_LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.environ.get("TWLEGALRAG_LLM_MAX_TOKENS", "2000")),
        )


class LLMError(RuntimeError):
    pass


def build_context(judgments: list[Judgment]) -> str:
    """Assemble the grounded context block from retrieved judgments' full text."""
    blocks = []
    for j in judgments:
        body = (j.fulltext or "").strip()
        if not body:
            # No reasoning text retrieved — give the LLM the listing so it knows
            # the case exists, but it cannot quote a holding from it.
            body = f"(未取得判決理由全文,僅有摘要) {j.snippet}"
        else:
            body = body[:_PER_DOC_CHARS]
        arts = ", ".join(j.cited_articles[:6]) if j.cited_articles else "（未標註）"
        blocks.append(
            f"【判決 {j.rank}】\n"
            f"引用字號: {j.citation_text}\n"
            f"法院: {j.court_name}\n"
            f"引用法條: {arts}\n"
            f"判決全文:\n{body}\n"
        )
    return "\n---\n".join(blocks)


def build_messages(question: str, judgments: list[Judgment]) -> list[dict]:
    context = build_context(judgments)
    user = (
        f"使用者問題:\n{question}\n\n"
        f"檢索到的判決(僅能根據以下內容作答):\n{context}"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def stream_answer(cfg: LLMConfig, messages: list[dict]) -> Iterator[str]:
    """Stream the answer text from the user's chosen provider."""
    if not cfg.api_key:
        raise LLMError(
            "No LLM API key. Set TWLEGALRAG_LLM_API_KEY (or OPENAI_API_KEY / "
            "ANTHROPIC_API_KEY), or pass one in config. This CLI never uses a "
            "shared key — you bring your own."
        )
    if cfg.provider == "anthropic":
        yield from _stream_anthropic(cfg, messages)
    elif cfg.provider in ("openai", "openai-compat"):
        if cfg.provider == "openai-compat" and not cfg.base_url:
            # Fail fast: an openai-compat provider with no base_url would
            # silently fall through to the official OpenAI endpoint and spend
            # tokens on the wrong service. Force the user to be explicit.
            raise LLMError(
                "provider 'openai-compat' requires a base_url. Set "
                "TWLEGALRAG_LLM_BASE_URL (e.g. your GLM / vLLM / Ollama "
                "endpoint), or use provider 'openai' for the official OpenAI API."
            )
        yield from _stream_openai(cfg, messages)
    else:
        raise LLMError(f"Unknown provider: {cfg.provider}")


def _stream_openai(cfg: LLMConfig, messages: list[dict]) -> Iterator[str]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMError(
            "openai package not installed. Run: pip install 'twlegalrag[openai]'"
        ) from exc
    client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
    stream = client.chat.completions.create(
        model=cfg.model,
        messages=messages,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


def _stream_anthropic(cfg: LLMConfig, messages: list[dict]) -> Iterator[str]:
    try:
        import anthropic
    except ImportError as exc:
        raise LLMError(
            "anthropic package not installed. Run: pip install 'twlegalrag[anthropic]'"
        ) from exc
    # Anthropic takes system separately from the message list.
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    convo = [m for m in messages if m["role"] != "system"]
    client = anthropic.Anthropic(api_key=cfg.api_key, base_url=cfg.base_url)
    with client.messages.stream(
        model=cfg.model,
        system=system,
        messages=convo,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    ) as stream:
        for text in stream.text_stream:
            yield text
