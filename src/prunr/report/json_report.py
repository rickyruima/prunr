"""JSON report output."""

from __future__ import annotations

import json
from pathlib import Path

from ..models import ScanReport


def render(report: ScanReport, output_path: str | None = None) -> str:
    data = {
        "scan_timestamp": report.scan_timestamp,
        "cost_per_gb_month": report.cost_per_gb_month,
        "cluster": {
            "name": report.cluster.name,
            "node_count": report.cluster.node_count,
            "total_indices": report.cluster.total_indices,
            "total_size_bytes": report.cluster.total_size_bytes,
            "total_size_gb": round(report.cluster.total_size_gb, 2),
            "total_docs": report.cluster.total_docs,
        },
        "cost": {
            "estimated_monthly": round(report.estimated_monthly_cost, 2),
            "estimated_annual": round(report.estimated_annual_cost, 2),
            "estimated_annual_waste": round(report.total_annual_savings, 2),
        },
        "summary": report.summary,
        "recommendations": [
            {
                "action": rec.action.value,
                "target": rec.target,
                "confidence": rec.confidence.value,
                "reasons": rec.reasons,
                "size_bytes": rec.size_bytes,
                "size_gb": round(rec.size_gb, 2),
                "annual_savings": round(rec.annual_savings, 2),
                "index_count": rec.index_count,
                "priority": rec.priority.value,
            }
            for rec in report.recommendations
        ],
        "generated_by": "prunr — https://github.com/rickyruima/prunr",
        "indices": [
            {
                "name": idx.name,
                "size_bytes": idx.size_bytes,
                "size_gb": round(idx.size_gb, 2),
                "doc_count": idx.doc_count,
                "query_total": idx.query_total,
                "query_rate": round(idx.query_rate, 4),
                "indexing_rate": round(idx.indexing_rate, 4),
                "primary_shards": idx.primary_shards,
                "total_shards": idx.total_shards,
                "avg_shard_size_mb": round(idx.avg_shard_size_mb, 1),
                "health": idx.health,
                "status": idx.status,
                "last_query_at": idx.last_query_at,
                "last_write_at": idx.last_write_at,
                "created_at": idx.created_at,
            }
            for idx in report.cluster.indices
        ],
    }

    output = json.dumps(data, indent=2)

    if output_path:
        Path(output_path).write_text(output)

    return output
