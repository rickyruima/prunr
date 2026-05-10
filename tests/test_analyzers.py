"""Unit tests for Prunr analyzers using mock cluster data."""

from __future__ import annotations

from prunr.analyzers import run_all

from .conftest import make_cluster, make_index


class TestDeadIndexDetector:
    def test_inactive_index_flagged(self):
        idx = make_index("old-logs-2023.01", search_count=0, index_count=0)
        cluster = make_cluster([idx])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        matching = [r for r in recs if r.target == "old-logs-2023.01"]
        assert len(matching) >= 1
        assert matching[0].action.value == "DELETE"

    def test_active_index_not_flagged(self):
        idx = make_index("active-index", search_count=500, index_count=100)
        cluster = make_cluster([idx])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        matching = [r for r in recs if r.target == "active-index"]
        delete_recs = [r for r in matching if r.action.value == "DELETE"]
        assert len(delete_recs) == 0

    def test_debug_pattern_flagged(self):
        idx = make_index("debug-data-2024.06", search_count=0, index_count=0)
        cluster = make_cluster([idx])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        matching = [r for r in recs if r.target == "debug-data-2024.06"]
        assert len(matching) >= 1


class TestShardOptimizer:
    def test_oversharded_flagged(self):
        idx = make_index(
            "tiny-index", size_bytes=500, shard_count=20, search_count=100, index_count=50
        )
        cluster = make_cluster([idx])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        shard_recs = [
            r for r in recs if r.target == "tiny-index" and "shard" in " ".join(r.reasons).lower()
        ]
        assert len(shard_recs) >= 1

    def test_well_sharded_not_flagged(self):
        idx = make_index("big-index", size_bytes=100 * 1024**3, shard_count=2)
        cluster = make_cluster([idx])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        shard_recs = [
            r for r in recs if r.target == "big-index" and "shard" in " ".join(r.reasons).lower()
        ]
        assert len(shard_recs) == 0


class TestDuplicateDetector:
    def test_versioned_indices_flagged(self):
        idx1 = make_index("app-logs-v1", doc_count=100)
        idx2 = make_index("app-logs-v2", doc_count=100)
        cluster = make_cluster([idx1, idx2])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        dup_recs = [
            r
            for r in recs
            if "duplicate" in " ".join(r.reasons).lower()
            or "overlap" in " ".join(r.reasons).lower()
        ]
        assert len(dup_recs) >= 1

    def test_single_index_not_flagged_as_duplicate(self):
        idx = make_index("unique-index")
        cluster = make_cluster([idx])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        dup_recs = [
            r
            for r in recs
            if "duplicate" in " ".join(r.reasons).lower()
            or "overlap" in " ".join(r.reasons).lower()
        ]
        assert len(dup_recs) == 0


class TestRetentionAnalyzer:
    def test_long_retention_flagged(self):
        indices = []
        for m in range(1, 25):
            q = 100 if m > 12 else 0
            indices.append(
                make_index(
                    f"filebeat-2023.{m:02d}",
                    search_count=q,
                    index_count=10,
                    size_bytes=1024 * 1024 * 100,
                )
            )
        cluster = make_cluster(indices)
        recs = run_all(cluster, cost_per_gb_month=0.10)
        retention_recs = [r for r in recs if r.action.value == "REDUCE RETENTION"]
        assert len(retention_recs) >= 1

    def test_short_retention_not_flagged(self):
        indices = [make_index(f"filebeat-2025.{m:02d}") for m in range(1, 4)]
        cluster = make_cluster(indices)
        recs = run_all(cluster, cost_per_gb_month=0.10)
        retention_recs = [r for r in recs if "retention" in " ".join(r.reasons).lower()]
        assert len(retention_recs) == 0


class TestStorageHog:
    def test_large_index_surfaced(self):
        big = make_index(
            "huge-analytics", size_bytes=500 * 1024**3, search_count=100, index_count=50
        )
        small = make_index("tiny-logs", size_bytes=1024)
        cluster = make_cluster([big, small])
        recs = run_all(cluster, cost_per_gb_month=0.10)
        hog_recs = [
            r
            for r in recs
            if r.target == "huge-analytics" and "storage" in " ".join(r.reasons).lower()
        ]
        assert len(hog_recs) >= 1
