"""Curated test cluster definition — shared by demo mode, seeder, and tests."""

from __future__ import annotations

from .models import ClusterInfo, IndexInfo


def _idx(
    name: str,
    size_gb: float = 0,
    size_mb: float = 0,
    size_kb: float = 0,
    docs: int = 0,
    queries: int = 0,
    query_rate: float = 0.0,
    indexing_total: int | None = None,
    indexing_rate: float = 0.0,
    pri: int = 2,
    rep: int = 1,
    health: str = "green",
    status: str = "open",
    last_query_at: str | None = None,
    last_write_at: str | None = None,
    created_at: str | None = None,
) -> IndexInfo:
    """Shorthand for building an IndexInfo."""
    if size_gb:
        size_bytes = int(size_gb * 1024**3)
    elif size_mb:
        size_bytes = int(size_mb * 1024**2)
    elif size_kb:
        size_bytes = int(size_kb * 1024)
    else:
        size_bytes = 0

    return IndexInfo(
        name=name,
        size_bytes=size_bytes,
        doc_count=docs,
        primary_shards=pri,
        replica_shards=rep,
        total_shards=pri * (1 + rep),
        query_rate=query_rate,
        query_total=queries,
        indexing_total=indexing_total if indexing_total is not None else docs,
        indexing_rate=indexing_rate,
        health=health,
        status=status,
        last_query_at=last_query_at,
        last_write_at=last_write_at,
        created_at=created_at,
    )


def make_v2_indices() -> list[IndexInfo]:
    """Return a curated set of indices covering 13 distinct issue patterns."""
    indices: list[IndexInfo] = []

    # ── Group 1: Clearly dead debug/test logs ──
    # Should produce high-confidence DELETE with real savings
    indices += [
        _idx("filebeat-debug-2025.01", size_gb=1.8, docs=12_000_000,
             created_at="2025-01-01T00:00:00Z", last_write_at="2025-01-31T23:59:00Z"),
        _idx("filebeat-debug-2025.02", size_gb=2.1, docs=14_500_000,
             created_at="2025-02-01T00:00:00Z", last_write_at="2025-02-28T23:59:00Z"),
        _idx("filebeat-debug-2025.03", size_gb=1.5, docs=10_200_000,
             created_at="2025-03-01T00:00:00Z", last_write_at="2025-03-31T23:59:00Z"),
        _idx("app-debug-2025.02", size_gb=0.9, docs=6_800_000,
             created_at="2025-02-01T00:00:00Z", last_write_at="2025-02-28T23:59:00Z"),
        _idx("test-runner-logs-2025.01", size_gb=0.4, docs=2_100_000,
             created_at="2025-01-15T00:00:00Z", last_write_at="2025-01-20T12:00:00Z"),
    ]

    # ── Group 2: Large retained but rarely queried access logs ──
    # Recent month gets 95% of queries; old months nearly zero
    for name, size_gb, docs, queries, month in [
        ("nginx-access-2025.01", 4.2, 85_000_000, 12, "01"),
        ("nginx-access-2025.02", 4.5, 91_000_000, 48, "02"),
        ("nginx-access-2025.03", 4.8, 96_000_000, 340, "03"),
        ("nginx-access-2025.04", 5.1, 102_000_000, 28_400, "04"),
        ("api-access-2025.01", 3.1, 62_000_000, 5, "01"),
        ("api-access-2025.02", 3.4, 68_000_000, 22, "02"),
        ("api-access-2025.03", 3.6, 72_000_000, 180, "03"),
        ("api-access-2025.04", 3.8, 76_000_000, 18_600, "04"),
    ]:
        indices.append(
            _idx(name, size_gb=size_gb, docs=docs, queries=queries,
                 query_rate=0.5 if queries > 100 else 0.0, pri=5,
                 created_at=f"2025-{month}-01T00:00:00Z",
                 last_write_at=f"2025-{month}-28T23:59:00Z",
                 last_query_at="2026-04-10T14:00:00Z" if queries > 100 else f"2025-{month}-15T10:00:00Z")
        )

    # ── Group 3: Hot production logs (should be SKIP) ──
    for name, size_gb, docs, queries in [
        ("app-prod-logs-2026.04", 28.0, 420_000_000, 185_000),
        ("payments-prod-logs-2026.04", 12.5, 95_000_000, 312_000),
        ("auth-prod-logs-2026.04", 8.2, 64_000_000, 224_000),
    ]:
        indices.append(
            _idx(name, size_gb=size_gb, docs=docs, queries=queries,
                 query_rate=15.0, indexing_rate=8_000.0,
                 pri=max(2, int(size_gb // 25)),
                 created_at="2026-04-01T00:00:00Z",
                 last_write_at="2026-04-12T23:59:00Z",
                 last_query_at="2026-04-12T23:59:30Z")
        )

    # ── Group 4: Duplicate ingestion patterns ──
    indices += [
        _idx("nginx-logs-2026.04", size_gb=6.2, docs=48_000_000, queries=4_200,
             query_rate=0.2, indexing_rate=400.0, pri=3,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-12T23:50:00Z",
             last_query_at="2026-04-12T20:00:00Z"),
        _idx("filebeat-nginx-2026.04", size_gb=5.8, docs=45_000_000, queries=1_800,
             query_rate=0.2, indexing_rate=400.0, pri=3,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-12T23:50:00Z",
             last_query_at="2026-04-12T18:00:00Z"),
        _idx("app-logs-v1", size_gb=3.4, docs=26_000_000, queries=320, pri=3,
             created_at="2025-06-01T00:00:00Z", last_write_at="2025-12-31T23:59:00Z",
             last_query_at="2026-03-01T09:00:00Z"),
        _idx("app-logs-v2", size_gb=3.8, docs=28_000_000, queries=12_400,
             query_rate=0.2, indexing_rate=400.0, pri=3,
             created_at="2026-01-01T00:00:00Z", last_write_at="2026-04-12T23:50:00Z",
             last_query_at="2026-04-12T22:00:00Z"),
    ]

    # ── Group 5: Over-sharded indices ──
    indices += [
        _idx("trace-raw-2026.04.01", size_mb=100, docs=850_000, queries=8_500,
             query_rate=1.0, indexing_rate=200.0, pri=50,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-01T23:59:00Z",
             last_query_at="2026-04-12T16:00:00Z"),
        _idx("trace-raw-2026.04.02", size_mb=120, docs=920_000, queries=8_500,
             query_rate=1.0, indexing_rate=200.0, pri=50,
             created_at="2026-04-02T00:00:00Z", last_write_at="2026-04-02T23:59:00Z",
             last_query_at="2026-04-12T16:00:00Z"),
        _idx("audit-small-2026.04.01", size_mb=40, docs=180_000, queries=8_500,
             query_rate=1.0, indexing_rate=200.0, pri=30,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-01T23:59:00Z",
             last_query_at="2026-04-12T12:00:00Z"),
    ]

    # ── Group 6: Compliance / audit indices ──
    indices += [
        _idx("security-audit-2025.03", size_gb=2.8, docs=18_000_000, queries=45, pri=3,
             created_at="2025-03-01T00:00:00Z", last_write_at="2025-03-31T23:59:00Z",
             last_query_at="2026-02-10T09:00:00Z"),
        _idx("pci-audit-2025.q1", size_gb=1.6, docs=9_200_000, queries=12, pri=3,
             created_at="2025-01-01T00:00:00Z", last_write_at="2025-03-31T23:59:00Z",
             last_query_at="2026-01-15T14:00:00Z"),
        _idx("auth-audit-archive-2024", size_gb=4.1, docs=32_000_000, queries=8, pri=3,
             created_at="2024-01-01T00:00:00Z", last_write_at="2024-12-31T23:59:00Z",
             last_query_at="2025-11-20T10:00:00Z"),
    ]

    # ── Group 7: Misleading small junk ──
    indices += [
        _idx("tmp-test-import-001", size_kb=8, docs=12, pri=1, rep=0,
             created_at="2026-03-20T14:00:00Z"),
        _idx("tmp-test-import-002", size_kb=12, docs=18, pri=1, rep=0,
             created_at="2026-03-20T14:05:00Z"),
        _idx("oneoff-migration-check", size_kb=4, docs=3, pri=1, rep=0,
             created_at="2026-02-10T09:00:00Z"),
    ]

    # ── Group 8: Controversial large archive ──
    indices.append(
        _idx("big-analytics-archive", size_gb=8.4, docs=125_000_000, queries=280, pri=5,
             created_at="2025-01-01T00:00:00Z", last_write_at="2025-12-31T23:59:00Z",
             last_query_at="2026-03-28T11:00:00Z")
    )

    # ── Group 9: Borderline REVIEW — queried just enough to be ambiguous ──
    # Analyzer should NOT confidently DELETE these
    indices += [
        _idx("support-case-archive-2025.q1", size_gb=1.8, docs=4_200_000, queries=3, pri=2,
             created_at="2025-01-01T00:00:00Z", last_write_at="2025-03-31T23:59:00Z",
             last_query_at="2026-04-02T16:30:00Z"),  # queried 10 days ago — someone still cares
        _idx("ops-investigation-2025.02", size_gb=2.4, docs=8_500_000, queries=1, pri=2,
             created_at="2025-02-01T00:00:00Z", last_write_at="2025-02-28T23:59:00Z",
             last_query_at="2026-03-15T08:00:00Z"),  # queried once last month during incident
        _idx("legacy-app-audit-2024", size_gb=3.2, docs=22_000_000, queries=4, pri=3,
             created_at="2024-01-01T00:00:00Z", last_write_at="2024-12-31T23:59:00Z",
             last_query_at="2026-04-10T09:00:00Z"),  # name says audit but not compliance-tagged
    ]

    # ── Group 10: Small but critical — hot, small, must NOT delete ──
    indices += [
        _idx("auth-failures-2026.04", size_mb=350, docs=1_200_000, queries=48_000,
             query_rate=5.0, indexing_rate=800.0, pri=2,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-12T23:59:00Z",
             last_query_at="2026-04-12T23:59:30Z"),
        _idx("deploy-events-2026.04", size_mb=180, docs=42_000, queries=22_000,
             query_rate=3.0, indexing_rate=50.0, pri=2,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-12T18:00:00Z",
             last_query_at="2026-04-12T23:55:00Z"),
    ]

    # ── Group 11: False-positive baits — look deletable but shouldn't be ──
    indices += [
        # Looks dead (0 queries) but it's a legal hold — name is the only hint
        _idx("legal-hold-2024", size_gb=2.6, docs=15_000_000, queries=0, pri=3,
             created_at="2024-06-01T00:00:00Z", last_write_at="2024-08-15T23:59:00Z"),
        # Name screams "debug" but it's actually a production audit trail
        _idx("debug-audit-prod-2026.04", size_gb=1.1, docs=3_800_000, queries=6_200,
             query_rate=0.8, indexing_rate=120.0, pri=2,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-12T23:50:00Z",
             last_query_at="2026-04-12T23:45:00Z"),
        # Just finished a migration cutover — looks dead but is intentionally kept
        _idx("migration-cutover-2026.04", size_mb=800, docs=2_500_000, queries=0,
             indexing_total=2_500_000, indexing_rate=0.0, pri=2,
             created_at="2026-04-08T00:00:00Z", last_write_at="2026-04-10T12:00:00Z"),
    ]

    # ── Group 12: Dirty data — yellow health, closed index ──
    indices += [
        # Yellow because a replica is unassigned (common in real clusters)
        _idx("metrics-infra-2026.04", size_gb=5.5, docs=38_000_000, queries=15_200,
             query_rate=2.0, indexing_rate=1_200.0, pri=3,
             health="yellow",
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-12T23:59:00Z",
             last_query_at="2026-04-12T23:58:00Z"),
        # Closed index — old data someone archived but didn't delete
        _idx("app-logs-2024.q3", size_gb=6.8, docs=52_000_000, queries=0,
             indexing_total=52_000_000, pri=5,
             status="close",
             created_at="2024-07-01T00:00:00Z", last_write_at="2024-09-30T23:59:00Z"),
    ]

    # ── Group 13: Weird ratio — high doc count but suspiciously small size ──
    indices.append(
        _idx("clickstream-raw-2026.04", size_mb=450, docs=85_000_000, queries=2_400,
             query_rate=0.3, indexing_rate=5_000.0, pri=3,
             created_at="2026-04-01T00:00:00Z", last_write_at="2026-04-12T23:59:00Z",
             last_query_at="2026-04-12T22:00:00Z")
    )

    return indices


def make_demo_cluster() -> ClusterInfo:
    """Build a complete cluster snapshot from curated indices for --demo mode."""
    indices = make_v2_indices()
    indices.sort(key=lambda i: i.size_bytes, reverse=True)

    return ClusterInfo(
        name="prod-logging-cluster",
        node_count=12,
        total_indices=len(indices),
        total_size_bytes=sum(i.size_bytes for i in indices),
        total_docs=sum(i.doc_count for i in indices),
        indices=indices,
    )
