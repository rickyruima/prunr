"""Rank indices by storage consumption to surface biggest opportunities."""

from __future__ import annotations

import re

from ..models import Action, ClusterInfo, Confidence, Recommendation

ARCHIVE_PATTERN = re.compile(r"archive|backup|old|legacy|historical", re.IGNORECASE)


class StorageHogRanker:
    def __init__(self, cost_per_gb_month: float):
        self.cost_per_gb_month = cost_per_gb_month

    def analyze(self, cluster: ClusterInfo) -> list[Recommendation]:
        if not cluster.indices or cluster.total_size_bytes == 0:
            return []

        # Compute cluster median query density for comparison
        densities = []
        for idx in cluster.indices:
            if idx.size_gb > 0 and idx.query_total > 0:
                densities.append(idx.query_total / idx.size_gb)
        median_density = sorted(densities)[len(densities) // 2] if densities else 0

        recs: list[Recommendation] = []

        for idx in cluster.indices[:10]:  # top 10 by size (already sorted)
            pct = (idx.size_bytes / cluster.total_size_bytes) * 100

            if pct < 5:  # not significant enough
                continue

            if idx.query_total == 0:
                continue  # dead_index handles this

            # Large index with low query density
            queries_per_gb = idx.query_total / idx.size_gb if idx.size_gb > 0 else 0

            if queries_per_gb < 100:
                reasons = [
                    f"Uses {pct:.1f}% of total cluster storage ({idx.size_gb:.1f} GB)",
                    f"Query density: {queries_per_gb:.1f} queries/GB (cluster median: {median_density:.0f})",
                ]
                if queries_per_gb < 10:
                    reasons.append("Very low query activity relative to size")
                if idx.indexing_rate == 0:
                    reasons.append("No active write activity — may be stale data")
                if ARCHIVE_PATTERN.search(idx.name):
                    reasons.append("Archive-pattern naming suggests cold or historical data")
                    reasons.append("Candidate for archive tier or reduced retention")

                recs.append(
                    Recommendation(
                        action=Action.REVIEW,
                        target=idx.name,
                        confidence=Confidence.MEDIUM if queries_per_gb < 10 else Confidence.LOW,
                        reasons=reasons,
                        size_bytes=idx.size_bytes,
                        annual_savings=0,
                    )
                )

        return recs
