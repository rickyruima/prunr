"""Tests for the HTML report renderer."""

from __future__ import annotations

import tempfile
from pathlib import Path

from prunr.models import Action, ClusterInfo, Confidence, IndexInfo, Priority, Recommendation, ScanReport
from prunr.report.html_report import render


def _make_index(name, size_bytes=1024, doc_count=10, search_count=0):
    return IndexInfo(
        name=name,
        size_bytes=size_bytes,
        doc_count=doc_count,
        primary_shards=1,
        replica_shards=0,
        total_shards=1,
        query_rate=0.0,
        query_total=search_count,
        indexing_total=0,
        indexing_rate=0.0,
        health="green",
        status="open",
    )


def _make_cluster(indices):
    return ClusterInfo(
        name="test",
        node_count=3,
        total_indices=len(indices),
        total_size_bytes=sum(i.size_bytes for i in indices),
        total_docs=sum(i.doc_count for i in indices),
        indices=indices,
    )


def _make_report() -> ScanReport:
    indices = [
        _make_index("logs-2025.01", size_bytes=5 * 1024**3, doc_count=1_000_000, search_count=0),
        _make_index("metrics-2025.03", size_bytes=2 * 1024**3, doc_count=500_000, search_count=100),
    ]
    cluster = _make_cluster(indices)
    recommendations = [
        Recommendation(
            action=Action.DELETE,
            target="logs-2025.01",
            confidence=Confidence.HIGH,
            reasons=["Zero queries in 30 days", "Older than 90 days"],
            size_bytes=5 * 1024**3,
            annual_savings=30.0,
            index_count=1,
            priority=Priority.HIGH,
        ),
    ]
    return ScanReport(
        cluster=cluster,
        recommendations=recommendations,
        summary=["1 dead index detected", "Estimated $30 annual savings"],
        cost_per_gb_month=0.50,
        scan_timestamp="2026-05-16 12:00:00 UTC",
    )


def test_render_returns_html_string():
    report = _make_report()
    html = render(report)
    assert "<!DOCTYPE html>" in html
    assert "Prunr Cluster Report" in html
    assert "logs-2025.01" in html
    assert "$30" in html
    assert "Zero queries in 30 days" in html


def test_render_contains_cluster_summary():
    report = _make_report()
    html = render(report)
    assert "test" in html  # cluster name
    assert "2" in html  # total indices
    assert "12:00:00 UTC" in html


def test_render_escapes_html():
    """Ensure HTML special characters are escaped."""
    indices = [_make_index("<script>alert('xss')</script>", size_bytes=1024)]
    cluster = _make_cluster(indices)
    report = ScanReport(cluster=cluster, recommendations=[], summary=[])
    html = render(report)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_writes_to_file():
    report = _make_report()
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        path = f.name
    render(report, output_path=path)
    content = Path(path).read_text()
    assert "<!DOCTYPE html>" in content
    assert "logs-2025.01" in content
    Path(path).unlink()


def test_render_empty_recommendations():
    indices = [_make_index("healthy-index", size_bytes=1024**3, search_count=500)]
    cluster = _make_cluster(indices)
    report = ScanReport(
        cluster=cluster,
        recommendations=[],
        summary=["No issues found"],
        scan_timestamp="2026-05-16 12:00:00 UTC",
    )
    html = render(report)
    assert "<!DOCTYPE html>" in html
    assert "Recommendations (0)" in html
    assert "healthy-index" in html
