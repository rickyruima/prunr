"""Shared test helpers for building mock cluster data."""

from __future__ import annotations

from prunr.models import ClusterInfo, IndexInfo


def make_index(
    name: str,
    size_bytes: int = 1024,
    doc_count: int = 10,
    search_count: int = 0,
    index_count: int = 0,
    shard_count: int = 1,
    replica_count: int = 0,
) -> IndexInfo:
    """Build a minimal IndexInfo for testing."""
    return IndexInfo(
        name=name,
        size_bytes=size_bytes,
        doc_count=doc_count,
        primary_shards=shard_count,
        replica_shards=replica_count,
        total_shards=shard_count * (1 + replica_count),
        query_rate=0.0,
        query_total=search_count,
        indexing_total=index_count,
        indexing_rate=0.0,
        health="green",
        status="open",
    )


def make_cluster(indices: list[IndexInfo]) -> ClusterInfo:
    """Build a minimal ClusterInfo for testing (sorts by size desc like collector)."""
    sorted_indices = sorted(indices, key=lambda i: i.size_bytes, reverse=True)
    return ClusterInfo(
        name="test",
        node_count=3,
        total_indices=len(sorted_indices),
        total_size_bytes=sum(i.size_bytes for i in sorted_indices),
        total_docs=sum(i.doc_count for i in sorted_indices),
        indices=sorted_indices,
    )
