"""HTML report output — self-contained, no external dependencies."""

from __future__ import annotations

from pathlib import Path

from ..models import ScanReport


def render(report: ScanReport, output_path: str | None = None) -> str:
    """Generate a self-contained HTML report string."""
    recs_rows = ""
    for rec in report.recommendations:
        confidence_class = rec.confidence.value.lower()
        priority_class = rec.priority.value.lower()
        reasons_html = "".join(f"<li>{_esc(r)}</li>" for r in rec.reasons)
        recs_rows += f"""<tr>
            <td class="action-{rec.action.value.replace(' ', '-').lower()}">{_esc(rec.action.value)}</td>
            <td>{_esc(rec.target)}</td>
            <td class="confidence-{confidence_class}">{_esc(rec.confidence.value)}</td>
            <td class="priority-{priority_class}">{_esc(rec.priority.value)}</td>
            <td class="number">{rec.size_gb:.2f} GB</td>
            <td class="number savings">${rec.annual_savings:,.0f}</td>
            <td><ul class="reasons">{reasons_html}</ul></td>
        </tr>"""

    indices_rows = ""
    for idx in report.cluster.indices:
        indices_rows += f"""<tr>
            <td>{_esc(idx.name)}</td>
            <td class="number">{idx.size_gb:.2f} GB</td>
            <td class="number">{idx.doc_count:,}</td>
            <td class="number">{idx.query_total:,}</td>
            <td class="number">{idx.total_shards}</td>
            <td>{_esc(idx.health)}</td>
            <td>{_esc(idx.status)}</td>
        </tr>"""

    summary_items = "".join(f"<li>{_esc(s)}</li>" for s in report.summary)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prunr Report — {_esc(report.cluster.name)}</title>
<style>
:root {{
    --color-bg: #f8f9fa;
    --color-surface: #ffffff;
    --color-border: #dee2e6;
    --color-text: #212529;
    --color-muted: #6c757d;
    --color-accent: #0d6efd;
    --color-danger: #dc3545;
    --color-warning: #ffc107;
    --color-success: #198754;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--color-bg);
    color: var(--color-text);
    line-height: 1.6;
    padding: 2rem;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 1.75rem; margin-bottom: 0.25rem; }}
.subtitle {{ color: var(--color-muted); margin-bottom: 2rem; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
.card {{
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 1.25rem;
}}
.card .label {{ font-size: 0.8rem; text-transform: uppercase; color: var(--color-muted); letter-spacing: 0.05em; }}
.card .value {{ font-size: 1.5rem; font-weight: 700; margin-top: 0.25rem; }}
.card .value.savings {{ color: var(--color-danger); }}
.card .value.cost {{ color: var(--color-warning); }}
section {{ margin-bottom: 2.5rem; }}
section h2 {{ font-size: 1.25rem; margin-bottom: 1rem; border-bottom: 2px solid var(--color-border); padding-bottom: 0.5rem; }}
table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    overflow: hidden;
    font-size: 0.875rem;
}}
th, td {{ padding: 0.6rem 0.75rem; text-align: left; border-bottom: 1px solid var(--color-border); }}
th {{ background: #f1f3f5; font-weight: 600; white-space: nowrap; }}
td.number {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.savings {{ font-weight: 700; color: var(--color-danger); }}
.confidence-high {{ color: var(--color-success); font-weight: 600; }}
.confidence-medium {{ color: #e67700; font-weight: 600; }}
.confidence-low {{ color: var(--color-danger); font-weight: 600; }}
.priority-high {{ color: var(--color-danger); font-weight: 600; }}
.priority-medium {{ color: #e67700; font-weight: 600; }}
.priority-low {{ color: var(--color-muted); }}
.action-delete {{ color: var(--color-danger); font-weight: 700; }}
.action-reduce-retention {{ color: #e67700; font-weight: 600; }}
.action-merge-shards {{ color: var(--color-accent); font-weight: 600; }}
.action-review {{ color: #6f42c1; font-weight: 600; }}
ul.reasons {{ margin: 0; padding-left: 1.2rem; }}
ul.reasons li {{ font-size: 0.8rem; color: var(--color-muted); }}
.summary-list {{ list-style: none; padding: 0; }}
.summary-list li {{ padding: 0.4rem 0; border-bottom: 1px solid var(--color-border); }}
.summary-list li:last-child {{ border-bottom: none; }}
footer {{ text-align: center; color: var(--color-muted); font-size: 0.8rem; margin-top: 3rem; }}
</style>
</head>
<body>
<div class="container">
    <h1>Prunr Cluster Report</h1>
    <p class="subtitle">Cluster: <strong>{_esc(report.cluster.name)}</strong> | Scanned: {_esc(report.scan_timestamp)}</p>

    <div class="cards">
        <div class="card">
            <div class="label">Total Indices</div>
            <div class="value">{report.cluster.total_indices}</div>
        </div>
        <div class="card">
            <div class="label">Total Size</div>
            <div class="value">{report.cluster.total_size_gb:.1f} GB</div>
        </div>
        <div class="card">
            <div class="label">Nodes</div>
            <div class="value">{report.cluster.node_count}</div>
        </div>
        <div class="card">
            <div class="label">Est. Monthly Cost</div>
            <div class="value cost">${report.estimated_monthly_cost:,.0f}</div>
        </div>
        <div class="card">
            <div class="label">Est. Annual Waste</div>
            <div class="value savings">${report.total_annual_savings:,.0f}</div>
        </div>
    </div>

    <section>
        <h2>Key Findings</h2>
        <ul class="summary-list">
            {summary_items}
        </ul>
    </section>

    <section>
        <h2>Recommendations ({len(report.recommendations)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Action</th>
                    <th>Target</th>
                    <th>Confidence</th>
                    <th>Priority</th>
                    <th>Size</th>
                    <th>Annual Savings</th>
                    <th>Reasons</th>
                </tr>
            </thead>
            <tbody>
                {recs_rows}
            </tbody>
        </table>
    </section>

    <section>
        <h2>Index Details ({report.cluster.total_indices})</h2>
        <table>
            <thead>
                <tr>
                    <th>Index</th>
                    <th>Size</th>
                    <th>Docs</th>
                    <th>Queries</th>
                    <th>Shards</th>
                    <th>Health</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {indices_rows}
            </tbody>
        </table>
    </section>

    <footer>Generated by prunr &mdash; https://github.com/rickyruima/prunr</footer>
</div>
</body>
</html>"""

    if output_path:
        Path(output_path).write_text(html)

    return html


def _esc(text: str | None) -> str:
    """Escape HTML special characters."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
