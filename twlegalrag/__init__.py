"""Taiwan Legal RAG — retrieve → answer with your own LLM → verify citations.

Three stages, deliberately decoupled:

1. ``retrieval``  — query the TLR API (your judgments stay on the server; only
   the matched judgments come back). No LLM here.
2. ``llm``        — feed the retrieved judgments to *your own* LLM account
   (OpenAI / Anthropic / any OpenAI-compatible endpoint). Zero server-side LLM.
3. ``faithful``   — verify every citation in the answer against the retrieved
   full text (wrong case / fabricated quote / party-as-court). Pure functions.
"""

__version__ = "0.1.0"
