"""Taiwan Legal RAG CLI — retrieve Taiwan court judgments for use with your own AI.

    twlegalrag search "勞資 加班費"                 # list matching judgments
    twlegalrag pack "車禍對方全責能求償什麼?" -o b.json  # bundle for your AI tool
    twlegalrag check b.json answer.txt              # citation check an answer
    twlegalrag health

This tool retrieves judgments and packages them for use with your own AI tools.
It does not generate legal advice and does not call any LLM.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .bundle import AI_USE_NOTICE, build_bundle
from .config import get_tlr_api_key, get_tlr_base_url
from .retrieval import Judgment, RetrievalError, TLRClient
from .verify import VerifyReport, citation_check

app = typer.Typer(
    add_completion=False,
    help="Taiwan Legal RAG — retrieve Taiwan court judgments for use with your own AI tools.",
)
console = Console()
err = Console(stderr=True)

_STATUS_STYLE = {"pass": "green", "needs_review": "yellow", "fail": "bold red"}
_STATUS_LABEL = {"pass": "通過", "needs_review": "待人工", "fail": "不在bundle/錯誤"}


def _client() -> TLRClient:
    return TLRClient(base_url=get_tlr_base_url(), api_key=get_tlr_api_key())


@app.command()
def health() -> None:
    """Check the TLR retrieval service is up."""
    try:
        with _client() as c:
            h = c.health()
    except RetrievalError as e:
        err.print(f"[bold red]TLR unreachable:[/] {e}")
        raise typer.Exit(1)
    ok = h.get("status") == "ok"
    console.print(
        Panel(
            f"status: {h.get('status')}\nretrieval: {h.get('retrieval')}",
            title="TLR health",
            border_style="green" if ok else "red",
        )
    )


@app.command()
def search(
    query: str = typer.Argument(..., help="搜尋字詞 (口語/關鍵字皆可)"),
    n: int = typer.Option(5, "--n", "-n", help="結果筆數 (1-10)", min=1, max=10),
    search_type: str = typer.Option("hybrid", "--type", help="hybrid | keyword | phrase"),
    read: bool = typer.Option(False, "--read", help="同時抓取判決理由全文片段 (excerpt)"),
) -> None:
    """Retrieval only — list matching judgments (no LLM, no cost)."""
    try:
        with _client() as c:
            hits = (
                c.search_and_read(query, search_type=search_type, max_results=n)
                if read
                else c.search(query, search_type=search_type, max_results=n)
            )
    except RetrievalError as e:
        err.print(f"[bold red]檢索失敗:[/] {e}")
        raise typer.Exit(1)
    if not hits:
        console.print("[yellow]無結果[/]")
        return
    table = Table(show_lines=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("字號", style="cyan")
    table.add_column("摘要")
    if read:
        table.add_column("全文字數", justify="right")
    for j in hits:
        row = [str(j.rank), j.citation_text, j.snippet[:60]]
        if read:
            row.append(str(len(j.fulltext or "")))
        table.add_row(*row)
    console.print(table)


def _print_report(rep: VerifyReport) -> None:
    style = _STATUS_STYLE.get(rep.overall, "white")
    header = (
        f"整體: [{style}]{_STATUS_LABEL.get(rep.overall, rep.overall)}[/]   "
        f"引用 {rep.citations_found} 筆 "
        f"(在 bundle 內 {rep.in_bundle} / 不在 bundle {rep.out_of_bundle})"
    )
    console.print(Panel(header, title="引用檢查 (citation check, bundle-level)", border_style=style))
    if rep.verdicts:
        table = Table(show_lines=False)
        table.add_column("狀態")
        table.add_column("引用字號", style="cyan")
        table.add_column("對應判決", style="dim")
        table.add_column("原因")
        for v in rep.verdicts:
            s = _STATUS_STYLE.get(v.status, "white")
            table.add_row(
                f"[{s}]{_STATUS_LABEL.get(v.status, v.status)}[/]",
                v.citation_text[:36],
                v.doc_id or "—",
                ", ".join(v.reasons),
            )
        console.print(table)
    qp = rep.quote_presence
    if qp.get("status") != "pass":
        s = _STATUS_STYLE.get(qp["status"], "white")
        console.print(
            f"引文存在性檢查 (bundle 層級): [{s}]{_STATUS_LABEL.get(qp['status'])}[/] ({qp['reason']})"
        )
    if rep.out_of_bundle:
        console.print(
            "[bold red]⚠ 偵測到引用了不在 bundle 內的判決字號 — 高度疑似捏造,請勿直接採信。[/]"
        )
    console.print(
        "[dim]註: 此檢查僅驗「引用字號是否在 bundle 內」+「逐字引文是否出現在 bundle 文字某處」。"
        "引文存在性是 bundle 層級,不保證引文出自答案所指那篇判決;也不檢查見解讀對、"
        "當事人主張被當成法院見解。請自行核對判決全文。[/]"
    )


@app.command()
def pack(
    question: str = typer.Argument(..., help="你的法律問題 (白話即可)"),
    n: int = typer.Option(5, "--n", "-n", help="檢索判決筆數 (1-10)", min=1, max=10),
    out: Optional[Path] = typer.Option(
        None, "--out", "-o", help="輸出 bundle JSON 路徑 (預設印到 stdout)"
    ),
    read_top: Optional[int] = typer.Option(
        None, "--read-top", help="抓全文的前 N 筆 (預設全部)"
    ),
) -> None:
    """Retrieve judgments and package them as a bundle for your own AI tool.

    The bundle (JSON) carries the judgments, stable citation ids (J1, J2, ...),
    full-text excerpts, allowed_citations, and verification instructions you can
    hand to ChatGPT / Claude / Gemini / a local model. No LLM is called here.
    """
    try:
        with _client() as c:
            err.print(f"[dim]檢索判決中... (TLR: {c.base_url})[/]")
            hits = c.search_and_read(question, max_results=n, read_top=read_top)
    except RetrievalError as e:
        err.print(f"[bold red]檢索失敗:[/] {e}")
        raise typer.Exit(1)
    if not hits:
        err.print("[yellow]檢索無結果。[/]")
        raise typer.Exit(1)
    data = build_bundle(question, hits)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    if out:
        out.write_text(payload, encoding="utf-8")
        err.print(f"[green]已寫入 {out}[/] ({len(hits)} 篇判決, allowed_citations={data['allowed_citations']})")
    else:
        console.print_json(payload)
    # Always remind, on stderr so it never pollutes piped JSON.
    err.print(f"\n[yellow]{AI_USE_NOTICE}[/]")


@app.command()
def check(
    bundle_path: Path = typer.Argument(..., help="pack 產生的 bundle JSON"),
    answer_path: Path = typer.Argument(..., help="要檢查的答案文字檔 (來自任何 AI)"),
) -> None:
    """Citation-check an answer against a bundle (bundle-level, best-effort).

    Verifies only that the answer's cited case numbers are in the bundle and that
    narrow verbatim quotes appear in the retrieved text. It does NOT verify legal
    reasoning or whether a holding was read correctly — read the judgments yourself.
    """
    try:
        data = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception as e:
        err.print(f"[bold red]讀取 bundle 失敗:[/] {e}")
        raise typer.Exit(1)
    _SUPPORTED_SCHEMA = "twlegalrag.bundle/v1"
    schema = data.get("schema") if isinstance(data, dict) else None
    if schema != _SUPPORTED_SCHEMA:
        err.print(
            f"[bold red]bundle 格式錯誤:[/] schema={schema!r}，"
            f"預期 {_SUPPORTED_SCHEMA!r}。請用 'twlegalrag pack' 重新產生 bundle。"
        )
        raise typer.Exit(1)
    try:
        answer = answer_path.read_text(encoding="utf-8")
    except Exception as e:
        err.print(f"[bold red]讀取答案失敗:[/] {e}")
        raise typer.Exit(1)
    # Rebuild Judgment objects from the bundle so the checker has doc_id + fulltext.
    hits = [
        Judgment(
            rank=i + 1,
            doc_id=j.get("doc_id", ""),
            citation_text=j.get("citation_text", ""),
            court_name=j.get("court_name", ""),
            jdate=j.get("jdate", ""),
            snippet=j.get("listing", ""),
            citation_url=j.get("citation_url", ""),
            citation_markdown="",
            result_token="",
            case_category=j.get("case_category"),
            fulltext=j.get("fulltext_excerpt", ""),
            cited_articles=j.get("cited_articles", []),
        )
        for i, j in enumerate(data.get("judgments", []))
    ]
    rep = citation_check(answer, hits)
    _print_report(rep)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="顯示版本"),
) -> None:
    if version:
        console.print(f"twlegalrag {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


def main() -> None:  # console_scripts entry
    app()


if __name__ == "__main__":
    app()
