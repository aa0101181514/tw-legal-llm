"""Taiwan Legal RAG — retrieve Taiwan court judgments for use with your own AI.

Two stages, deliberately decoupled:

1. ``retrieval`` — query the TLR API (the judgment database stays on the server;
   only the matched judgments come back). No LLM here.
2. ``verify``    — a bundle-level citation check: does an answer cite a case that
   is actually in the retrieved bundle, and do its verbatim quotes appear
   somewhere in the bundle's text. Deterministic pure functions, no LLM. This is
   not a semantic faithfulness verifier — see ``verify`` for what it does NOT do.

``bundle`` packages retrieved judgments (with stable citation ids and explicit
verification instructions) for use with your own AI tool.
"""

__version__ = "0.1.0"
