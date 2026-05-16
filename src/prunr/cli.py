"""Prunr CLI — scan your ES/OpenSearch cluster for waste."""

from __future__ import annotations

from datetime import datetime, timezone

import click
from rich.console import Console

from . import __version__
from .analyzers import run_all
from .analyzers.summary import generate_summary
from .client import Connection
from .collector import collect
from .fixtures import make_demo_cluster
from .seed import seed_cluster
from .snapshot import load_snapshot, save_snapshot
from .models import ScanReport
from .report import terminal
from .report import json_report
from .report import html_report


@click.group()
@click.version_option(version=__version__)
def main():
    """Prunr — Find dead indices, wasted storage, and cost savings."""


@main.command()
@click.option(
    "--host", default=None, help="Elasticsearch/OpenSearch URL (e.g. https://localhost:9200)"
)
@click.option("--api-key", default=None, help="API key for authentication")
@click.option("--user", default=None, help="Username for basic auth")
@click.option("--password", default=None, help="Password for basic auth")
@click.option(
    "--cost-per-gb", default=0.50, type=float, help="Cost per GB per month in USD (default: 0.50)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "json", "html"]),
    default="terminal",
    help="Output format",
)
@click.option("--output", "output_path", default=None, help="Save report to file")
@click.option("--no-verify-certs", is_flag=True, help="Skip TLS certificate verification")
@click.option("--demo", is_flag=True, help="Run with built-in sample data (no cluster needed)")
@click.option("--snapshot", "snapshot_path", default=None, help="Load cluster data from a JSON snapshot file")
@click.option("--save-snapshot", "save_snapshot_path", default=None, help="Save collected cluster data as a JSON snapshot")
def scan(
    host: str | None,
    api_key: str | None,
    user: str | None,
    password: str | None,
    cost_per_gb: float,
    output_format: str,
    output_path: str | None,
    no_verify_certs: bool,
    demo: bool,
    snapshot_path: str | None,
    save_snapshot_path: str | None,
):
    """Scan a cluster and generate a cost/waste report."""
    console = Console()

    if snapshot_path:
        console.print(f"[dim]Loading snapshot from {snapshot_path}...[/]")
        cluster = load_snapshot(snapshot_path)
        console.print(
            f"[green]Loaded:[/] {cluster.total_indices} indices, {cluster.total_size_gb:.1f} GB"
        )
    elif demo:
        console.print("[dim]Running with built-in demo data...[/]")
        cluster = make_demo_cluster()
        console.print(
            f"[green]Demo cluster:[/] {cluster.total_indices} indices, {cluster.total_size_gb:.1f} GB"
        )
    elif host:
        # Connect
        conn = Connection(
            host=host,
            api_key=api_key,
            username=user,
            password=password,
            verify_certs=not no_verify_certs,
        )

        console.print(f"[dim]Connecting to {host}...[/]")

        try:
            info = conn.test_connection()
            version = info.get("version", {}).get("number", "unknown")
            distribution = info.get("version", {}).get("distribution", "Elasticsearch")
            console.print(f"[green]Connected:[/] {distribution} {version}")
        except Exception as e:
            console.print(f"[red]Connection failed:[/] {e}")
            raise SystemExit(1)

        # Collect
        console.print("[dim]Collecting index data...[/]")
        cluster = collect(conn)
        console.print(
            f"[green]Collected:[/] {cluster.total_indices} indices, {cluster.total_size_gb:.1f} GB"
        )
    else:
        console.print("[red]Error:[/] Provide --host, --snapshot, or use --demo")
        raise SystemExit(1)

    # Save snapshot if requested
    if save_snapshot_path:
        save_snapshot(cluster, save_snapshot_path)
        console.print(f"[green]Snapshot saved to {save_snapshot_path}[/]")

    # Analyze
    console.print("[dim]Analyzing...[/]")
    recommendations = run_all(cluster, cost_per_gb)
    summary = generate_summary(cluster, recommendations)

    # Build report
    report = ScanReport(
        cluster=cluster,
        recommendations=recommendations,
        summary=summary,
        cost_per_gb_month=cost_per_gb,
        scan_timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    console.print()

    # Output
    if output_format == "json":
        output = json_report.render(report, output_path)
        if not output_path:
            console.print(output)
        else:
            console.print(f"[green]Report saved to {output_path}[/]")
    elif output_format == "html":
        output = html_report.render(report, output_path)
        if not output_path:
            console.print(output)
        else:
            console.print(f"[green]HTML report saved to {output_path}[/]")
    else:
        terminal.render(report, console)
        if output_path:
            # Also save JSON alongside terminal output
            json_report.render(report, output_path)
            console.print(f"\n[dim]Report saved to {output_path}[/]")


@main.command()
@click.option(
    "--host",
    required=True,
    help="Elasticsearch/OpenSearch URL (e.g. http://localhost:9200)",
)
@click.option("--api-key", default=None, help="API key for authentication")
@click.option("--user", default=None, help="Username for basic auth")
@click.option("--password", default=None, help="Password for basic auth")
@click.option("--no-verify-certs", is_flag=True, help="Skip TLS certificate verification")
@click.option("--clean", is_flag=True, help="Delete seeded indices only (leaves other indices intact)")
def seed(
    host: str,
    api_key: str | None,
    user: str | None,
    password: str | None,
    no_verify_certs: bool,
    clean: bool,
):
    """Seed a cluster with curated test data (30 indices, 8 issue patterns)."""
    conn = Connection(
        host=host,
        api_key=api_key,
        username=user,
        password=password,
        verify_certs=not no_verify_certs,
    )

    try:
        conn.test_connection()
    except Exception as e:
        click.echo(f"Connection failed: {e}", err=True)
        raise SystemExit(1)

    if clean:
        from .seed import clean_seeded_indices
        clean_seeded_indices(conn)
    else:
        seed_cluster(conn)
