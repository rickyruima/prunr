"""Load and save ClusterInfo snapshots as JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from .models import ClusterInfo, IndexInfo


def save_snapshot(cluster: ClusterInfo, path: str) -> None:
    """Serialize a ClusterInfo to a JSON file."""
    data = {
        "cluster": {
            "name": cluster.name,
            "node_count": cluster.node_count,
        },
        "indices": [
            {
                "name": idx.name,
                "size_bytes": idx.size_bytes,
                "doc_count": idx.doc_count,
                "primary_shards": idx.primary_shards,
                "replica_shards": idx.replica_shards,
                "total_shards": idx.total_shards,
                "query_rate": idx.query_rate,
                "query_total": idx.query_total,
                "indexing_total": idx.indexing_total,
                "indexing_rate": idx.indexing_rate,
                "health": idx.health,
                "status": idx.status,
                "creation_date_ms": idx.creation_date_ms,
                "last_query_at": idx.last_query_at,
                "last_write_at": idx.last_write_at,
                "created_at": idx.created_at,
            }
            for idx in cluster.indices
        ],
    }
    Path(path).write_text(json.dumps(data, indent=2))


def load_snapshot(path: str) -> ClusterInfo:
    """Deserialize a ClusterInfo from a JSON file."""
    data = json.loads(Path(path).read_text())
    cluster_meta = data.get("cluster", {})

    indices: list[IndexInfo] = []
    for raw in data.get("indices", []):
        indices.append(
            IndexInfo(
                name=raw["name"],
                size_bytes=raw["size_bytes"],
                doc_count=raw["doc_count"],
                primary_shards=raw["primary_shards"],
                replica_shards=raw.get("replica_shards", 0),
                total_shards=raw.get("total_shards", raw["primary_shards"]),
                query_rate=raw.get("query_rate", 0.0),
                query_total=raw.get("query_total", 0),
                indexing_total=raw.get("indexing_total", 0),
                indexing_rate=raw.get("indexing_rate", 0.0),
                health=raw.get("health", "green"),
                status=raw.get("status", "open"),
                creation_date_ms=raw.get("creation_date_ms"),
                last_query_at=raw.get("last_query_at"),
                last_write_at=raw.get("last_write_at"),
                created_at=raw.get("created_at"),
            )
        )

    indices.sort(key=lambda i: i.size_bytes, reverse=True)

    return ClusterInfo(
        name=cluster_meta.get("name", "snapshot"),
        node_count=cluster_meta.get("node_count", 1),
        total_indices=len(indices),
        total_size_bytes=sum(i.size_bytes for i in indices),
        total_docs=sum(i.doc_count for i in indices),
        indices=indices,
    )
