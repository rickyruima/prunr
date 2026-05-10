"""Collect index and cluster data from ES/OpenSearch."""

from __future__ import annotations

from .client import Connection
from .models import ClusterInfo, IndexInfo


def collect(conn: Connection) -> ClusterInfo:
    """Collect all cluster and index metadata needed for analysis."""
    # Cluster info
    cluster_info = conn.get("/")
    cluster_name = cluster_info.get("cluster_name", "unknown")

    # Index list with basic stats
    raw_indices = conn.get("/_cat/indices?format=json&bytes=b")

    # Per-index stats (query/indexing rates)
    all_stats = conn.get("/_stats?level=indices")

    # Get cluster uptime for rate calculations
    nodes_stats = conn.get("/_nodes/stats/jvm")
    uptimes = [
        n.get("jvm", {}).get("uptime_in_millis", 0)
        for n in nodes_stats.get("nodes", {}).values()
    ]
    uptime_seconds = (max(uptimes) / 1000) if uptimes else 0

    # Build index info list, skip system indices
    indices: list[IndexInfo] = []
    stats_by_index = all_stats.get("indices", {})

    for idx in raw_indices:
        name = idx.get("index", "")
        if name.startswith("."):  # skip system/hidden indices
            continue

        istats = stats_by_index.get(name, {})
        primaries = istats.get("primaries", {})
        search_stats = primaries.get("search", {})
        indexing_stats = primaries.get("indexing", {})

        query_total = search_stats.get("query_total", 0)
        index_total = indexing_stats.get("index_total", 0)

        # Use node uptime for wall-clock rate approximation
        query_rate = 0.0
        indexing_rate = 0.0
        if uptime_seconds > 0:
            query_rate = query_total / uptime_seconds
            indexing_rate = index_total / uptime_seconds

        creation_date = istats.get("settings", {}).get("index", {}).get("creation_date")

        pri = _int(idx.get("pri", "0"))
        rep = _int(idx.get("rep", "0"))

        indices.append(
            IndexInfo(
                name=name,
                size_bytes=_int(idx.get("store.size", "0")),
                doc_count=_int(idx.get("docs.count", "0")),
                primary_shards=pri,
                replica_shards=rep,
                total_shards=pri * (1 + rep),
                query_rate=query_rate,
                query_total=query_total,
                indexing_total=index_total,
                indexing_rate=indexing_rate,
                health=idx.get("health", "unknown"),
                status=idx.get("status", "unknown"),
                creation_date_ms=int(creation_date) if creation_date else None,
            )
        )

    # Sort by size descending
    indices.sort(key=lambda i: i.size_bytes, reverse=True)

    total_size = sum(i.size_bytes for i in indices)
    total_docs = sum(i.doc_count for i in indices)

    # Node count
    nodes = conn.get("/_cat/nodes?format=json")
    node_count = len(nodes)

    return ClusterInfo(
        name=cluster_name,
        node_count=node_count,
        total_indices=len(indices),
        total_size_bytes=total_size,
        total_docs=total_docs,
        indices=indices,
    )


def _int(val: str | int) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0
