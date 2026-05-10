"""Rich terminal report output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..models import Action, Confidence, Priority, Recommendation, ScanReport

CONFIDENCE_COLORS = {
    Confidence.HIGH: "green",
    Confidence.MEDIUM: "yellow",
    Confidence.LOW: "red",
    Confidence.SKIP: "dim",
}

CONFIDENCE_ICONS = {
    Confidence.HIGH: "[green]●[/]",
    Confidence.MEDIUM: "[yellow]●[/]",
    Confidence.LOW: "[red]●[/]",
    Confidence.SKIP: "[dim]○[/]",
}


def render(report: ScanReport, console: Console | None = None) -> None:
    console = console or Console()

    # Header
    header = Text()
    header.append("PRUNR CLUSTER REPORT\n", style="bold white")
    header.append(f"Cluster: {report.cluster.name}", style="cyan")
    header.append(f"  |  {report.cluster.total_indices} indices", style="dim")
    header.append(f"  |  {report.cluster.total_size_gb:.1f} GB", style="dim")
    header.append(f"  |  {report.cluster.node_count} nodes", style="dim")
    if report.scan_timestamp:
        header.append(f"\nScanned: {report.scan_timestamp}", style="dim")

    console.print(Panel(header, border_style="blue"))
    console.print()

    # Cost summary
    cost_text = Text()
    cost_text.append(
        f"  ESTIMATED MONTHLY COST:  ${report.estimated_monthly_cost:,.0f}\n", style="dim"
    )
    cost_text.append(
        f"  ESTIMATED ANNUAL WASTE:  ${report.total_annual_savings:,.0f}",
        style="bold red" if report.total_annual_savings > 0 else "green",
    )

    console.print(Panel(cost_text, title="Cost Overview", border_style="yellow"))
    console.print()

    # Cluster-level summary
    if report.summary:
        console.print("[bold]KEY FINDINGS[/]\n")
        for finding in report.summary:
            console.print(f"  [yellow]→[/] {finding}")
        console.print()

    # Recommendations
    if not report.recommendations:
        console.print("[green]No recommendations — your cluster looks clean![/]")
        return

    # Group into sections
    cleanup: list[Recommendation] = []
    needs_review: list[Recommendation] = []
    efficiency: list[Recommendation] = []
    duplicates: list[Recommendation] = []

    for rec in report.recommendations:
        if rec.action in (Action.DELETE, Action.REDUCE_RETENTION):
            cleanup.append(rec)
        elif rec.action == Action.MERGE_SHARDS:
            efficiency.append(rec)
        elif "may overlap" in " ".join(rec.reasons).lower():
            duplicates.append(rec)
        else:
            needs_review.append(rec)

    sections = [
        ("RECOMMENDED CLEANUP", "red", cleanup),
        ("NEEDS REVIEW", "yellow", needs_review),
        ("CLUSTER EFFICIENCY", "cyan", efficiency),
        ("POTENTIAL DUPLICATE INGESTION", "magenta", duplicates),
    ]

    for title, color, recs_list in sections:
        if not recs_list:
            continue

        console.print(f"[bold {color}]{title}[/]\n")

        for rec in recs_list[:5]:
            _render_rec(console, rec)

        if len(recs_list) > 5:
            console.print(f"  [dim]... and {len(recs_list) - 5} more[/]\n")

    # Full index breakdown
    console.print()
    table = Table(title="Full Index Breakdown", show_lines=False, padding=(0, 1))
    table.add_column("Index", style="cyan", max_width=30)
    table.add_column("Size", justify="right")
    table.add_column("Docs", justify="right")
    table.add_column("Queries", justify="right")
    table.add_column("Shards", justify="right")
    table.add_column("Action", justify="center")
    table.add_column("Confidence", justify="center")
    table.add_column("Priority", justify="center")

    for idx in report.cluster.indices:
        rec = _find_rec_for_index(idx.name, report.recommendations)

        if rec:
            action_labels = {
                "DELETE": ("[red]", "DELETE"),
                "REDUCE RETENTION": ("[yellow]", "REDUCE"),
                "MERGE SHARDS": ("[cyan]", "MERGE"),
                "REVIEW": ("[magenta]", "REVIEW"),
            }
            color, label = action_labels.get(rec.action.value, ("[white]", rec.action.value))
            action_str = f"{color}{label}[/]"

            conf = rec.confidence
            conf_labels = {
                Confidence.HIGH: "[green]HIGH[/]",
                Confidence.MEDIUM: "[yellow]MED[/]",
                Confidence.LOW: "[red]LOW[/]",
            }
            conf_label = conf_labels.get(conf, "[dim]—[/]")

            pri = rec.priority
            pri_labels = {
                Priority.HIGH: "[red]HIGH[/]",
                Priority.MEDIUM: "[yellow]MED[/]",
                Priority.LOW: "[dim]LOW[/]",
            }
            pri_label = pri_labels.get(pri, "[dim]—[/]")
        else:
            action_str = "[dim]—[/]"
            conf_label = "[dim]—[/]"
            pri_label = "[dim]SKIP[/]"

        size_str = _format_size(idx.size_bytes)
        docs_str = _format_number(idx.doc_count)

        table.add_row(
            idx.name,
            size_str,
            docs_str,
            str(idx.query_total),
            str(idx.total_shards),
            action_str,
            conf_label,
            pri_label,
        )

    console.print(table)
    console.print()
    console.print("[dim]Generated by prunr — https://github.com/rickyruima/prunr[/]")


def _render_rec(console: Console, rec: Recommendation) -> None:
    color = CONFIDENCE_COLORS.get(rec.confidence, "white")
    priority_color = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "dim"}.get(
        rec.priority.value, "dim"
    )

    console.print(
        f"  [bold]{rec.action.value}[/]  [cyan]{rec.target}[/]  ({rec.size_gb:.1f} GB)"
    )
    console.print(
        f"     Confidence: [{color}]{rec.confidence.value}[/]  |  Priority: [{priority_color}]{rec.priority.value}[/]"
    )

    if rec.annual_savings > 0:
        console.print(f"     [bold yellow]Annual savings: ${rec.annual_savings:,.0f}[/]")

    console.print("     [dim]Reasoning:[/]")
    for reason in rec.reasons:
        console.print(
            f"       [dim]{'✓' if rec.confidence == Confidence.HIGH else '⚠'}[/] {reason}"
        )

    if rec.index_count > 1:
        console.print(f"     [dim]Covers {rec.index_count} indices[/]")
    console.print()


def _find_rec_for_index(name: str, recs: list) -> object | None:
    """Find the most specific recommendation that covers this index name."""
    from ..models import Confidence

    confidence_rank = {
        Confidence.HIGH: 3,
        Confidence.MEDIUM: 2,
        Confidence.LOW: 1,
        Confidence.SKIP: 0,
    }
    best = None
    best_score = -1

    for r in recs:
        matched = False

        # Exact match (highest specificity)
        if r.target == name:
            return r  # can't do better than exact

        # Check explicit "Indices:" list first — most reliable
        if hasattr(r, "reasons"):
            for reason in r.reasons:
                if reason.startswith("Indices: ") and name in reason.split(": ", 1)[1].split(", "):
                    matched = True
                    break

        # Family match: "filebeat-debug-* (3 indices)" should match "filebeat-debug-2025.01"
        # But only if the rec does NOT have an explicit Indices list (which is more precise)
        if not matched and "*" in r.target:
            has_indices_list = any(
                reason.startswith("Indices: ") for reason in getattr(r, "reasons", [])
            )
            if not has_indices_list:
                pattern = r.target.split("*")[0].rstrip("- (")
                if name.startswith(pattern) and (
                    len(name) == len(pattern) or name[len(pattern)] in "-_."
                ):
                    matched = True

        if matched:
            score = confidence_rank.get(r.confidence, 0)
            if score > best_score:
                best = r
                best_score = score

    return best


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024**3:
        return f"{size_bytes / 1024**3:.1f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / 1024**2:.0f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"


def _format_number(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
