"""Command line: ``gsps <command>``. Every command reads files and prints or writes new ones."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Annotated

import typer

from gsps import __version__
from gsps.cascade.graph import DependencyGraph
from gsps.deliverable.fill_report import build_fill_report, render_fill_report
from gsps.deliverable.text import docx_text
from gsps.library import Library
from gsps.model.records import Token
from gsps.requirements.brief import load_brief
from gsps.requirements.business_case import load_claims, validate_routing
from gsps.rules.estimates import recompute
from gsps.rules.integrity import run_integrity_checks
from gsps.store.csv_io import load_records
from gsps.views.build import build_views, write_views
from gsps.walk.gates import paste_block
from gsps.walk.run import WalkRun
from gsps.walk.ship import ship_check
from gsps.walk.track1 import load_track1, validate_track1
from gsps.walk.track2 import load_track2

app = typer.Typer(
    name="gsps",
    help="GSPS provenance engine: walk every figure to its owner, ship the receipts.",
    no_args_is_help=True,
    add_completion=False,
)

LibraryOpt = Annotated[
    Path,
    typer.Option("--library", "-l", envvar="GSPS_LIBRARY", help="Library root folder."),
]


def _date(text: str | None) -> dt.date | None:
    return dt.date.fromisoformat(text) if text else None


def _page_text(path: Path) -> str:
    return docx_text(path) if path.suffix.lower() == ".docx" else path.read_text(encoding="utf-8")


@app.command()
def version() -> None:
    """Print the version."""
    typer.echo(__version__)


@app.command()
def views(
    library: LibraryOpt,
    as_of: Annotated[str | None, typer.Option(help="Simulate a date, YYYY-MM-DD.")] = None,
    dry: Annotated[bool, typer.Option(help="Print instead of writing a new version.")] = False,
) -> None:
    """Derive the library views (written as a new dated version under VIEWS/)."""
    lib = Library.load(library)
    day = _date(as_of)
    if dry:
        typer.echo(build_views(lib, day or dt.date.today(), simulated=day is not None))
        return
    typer.echo(f"wrote {write_views(lib, day)}")


@app.command("vocab-check")
def vocab_check(library: LibraryOpt) -> None:
    """Integrity and vocabulary checks. Exit 1 when anything needs a ruling or a fix."""
    lib = Library.load(library)
    results = run_integrity_checks(
        lib.anchors, lib.citations, lib.deliverables, lib.findings, lib.registry
    )
    bad = [r for r in results if not r.ok]
    for r in results:
        typer.echo(
            f"{'OK  ' if r.ok else 'FLAG'}  {r.name}{'' if r.ok else ': ' + ', '.join(r.offenders)}"
        )
    raise typer.Exit(1 if bad else 0)


@app.command("fill-report")
def fill_report(
    library: LibraryOpt,
    tokens: Annotated[Path, typer.Option(help="Token registry CSV.")],
    page: Annotated[Path, typer.Option(help="Page text (.txt/.md) or .docx.")],
    doc_version: Annotated[str, typer.Option(help="Version label of the page.")],
    keeper: Annotated[
        str, typer.Option(envvar="GSPS_KEEPER", help="Owner name used for our own estimates.")
    ] = "keeper",
) -> None:
    """One row per token: how each value on the page was decided, and what is dirty."""
    lib = Library.load(library)
    rows = build_fill_report(
        load_records(tokens, Token), lib.anchors_by_id, _page_text(page), doc_version, keeper=keeper
    )
    typer.echo(render_fill_report(rows, f"{page.name} ({doc_version})"))
    raise typer.Exit(1 if any(r.dirty for r in rows) else 0)


@app.command("validate-walk")
def validate_walk(
    claims: Annotated[Path, typer.Option(help="Claims CSV.")],
    track1: Annotated[Path, typer.Option(help="Track-1 log CSV.")],
) -> None:
    """Check routing and every Track-1 entry against the rules."""
    cs = load_claims(claims)
    problems = validate_routing(cs) + validate_track1(cs, load_track1(track1))
    for p in problems:
        typer.echo(p)
    typer.echo("walk is consistent" if not problems else f"{len(problems)} problem(s)")
    raise typer.Exit(1 if problems else 0)


@app.command("ship-check")
def ship(
    claims: Annotated[Path, typer.Option(help="Claims CSV.")],
    track1: Annotated[Path, typer.Option(help="Track-1 log CSV.")],
    track2: Annotated[Path, typer.Option(help="Track-2 register CSV.")],
    page: Annotated[Path | None, typer.Option(help="Page text, to check estimate labels.")] = None,
    contested: Annotated[str, typer.Option(help="Comma-separated contested claim IDs.")] = "",
) -> None:
    """Can the page ship? Exit 0 only when every claim on it is accounted for."""
    report = ship_check(
        load_claims(claims),
        load_track1(track1),
        load_track2(track2),
        contested=[c.strip() for c in contested.split(",") if c.strip()],
        page_text=_page_text(page) if page else None,
    )
    typer.echo(report.render())
    raise typer.Exit(0 if report.ok else 1)


@app.command()
def impact(
    library: LibraryOpt,
    anchor: Annotated[str, typer.Option(help="Anchor ID whose value moved.")],
    tokens: Annotated[Path | None, typer.Option(help="Token registry CSV.")] = None,
) -> None:
    """Everything downstream of one anchor (estimates, tokens, deliverables)."""
    lib = Library.load(library)
    graph = DependencyGraph.build(
        lib.anchors, load_records(tokens, Token) if tokens else [], lib.citations
    )
    imp = graph.impact(anchor)
    typer.echo(f"anchors:      {', '.join(sorted(imp.anchors)) or '-'}")
    typer.echo(f"tokens:       {', '.join(sorted(imp.tokens)) or '-'}")
    typer.echo(f"deliverables: {', '.join(sorted(imp.deliverables)) or '-'}")


@app.command("recompute")
def recompute_cmd(
    method: Annotated[
        str, typer.Option(help="Expression over anchor IDs, e.g. 'SAM-001 * PRC-001 * 12'.")
    ],
    stated: Annotated[str, typer.Option(help="The value the document states.")],
    inputs: Annotated[list[str], typer.Option("--input", help="ID=value, repeatable.")],
) -> None:
    """Re-run an estimate from its inputs and compare with the stated value."""
    env = dict(i.split("=", 1) for i in inputs)
    try:
        check = recompute(method, env, stated)
    except (ValueError, KeyError, SyntaxError) as exc:
        typer.echo(f"cannot recompute: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(check.explain())
    raise typer.Exit(0 if check.ok else 1)


@app.command("paste-block")
def paste(urls: list[str]) -> None:
    """Print a paste-ready block of URLs (for clearing web gates)."""
    typer.echo(paste_block(urls))


@app.command("new-run")
def new_run(
    runs_dir: Annotated[Path, typer.Option(help="Folder holding WR-### runs.")],
    doc_version: Annotated[str, typer.Option(help="Version label of the reviewed document.")],
) -> None:
    """Create the next walk-run folder."""
    typer.echo(WalkRun.create(runs_dir, doc_version).path)


@app.command()
def brief(path: Path) -> None:
    """Show a walk brief: questions, inputs and scope."""
    b = load_brief(path)
    typer.echo(f"{b.id} from {b.requester}, {b.date} (blind: {b.blind})")
    for i in b.inputs:
        typer.echo(f"  input [{i.role}] {i.path}")
    for q in b.questions:
        typer.echo(f"  {q.id}: {q.text}")
    typer.echo(f"  in scope: {', '.join(b.scope.in_) or '-'}")
    typer.echo(f"  held:     {', '.join(b.scope.held) or '-'}")


if __name__ == "__main__":  # pragma: no cover
    app()
