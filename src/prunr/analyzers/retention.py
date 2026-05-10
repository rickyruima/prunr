"""Analyze index retention patterns and suggest reductions."""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import Action, ClusterInfo, Confidence, Recommendation

# Match date-based index patterns like filebeat-2025.04.01, logs-2025-04
DATE_PATTERN = re.compile(r"^(.*?)[-_](\d{4})[.\-_](\d{2})(?:[.\-_](\d{2}))?$")


class RetentionAnalyzer:
    def __init__(self, cost_per_gb_month: float):
        self.cost_per_gb_month = cost_per_gb_month

    def analyze(self, cluster: ClusterInfo) -> list[Recommendation]:
        # Group indices by their base pattern (strip date suffix)
        groups: dict[str, list] = defaultdict(list)
        for idx in cluster.indices:
            match = DATE_PATTERN.match(idx.name)
            if match:
                base = match.group(1)
                groups[base].append(idx)

        recs: list[Recommendation] = []
        for base, indices in groups.items():
            if len(indices) < 7:  # need enough history to analyze
                continue

            # Sort by name (chronological for date-based indices)
            indices.sort(key=lambda i: i.name)

            total_queries = sum(i.query_total for i in indices)

            if total_queries == 0:
                continue  # dead_index analyzer handles this

            # Find how many recent indices get most queries
            queried_indices = [i for i in indices if i.query_total > 0]
            if not queried_indices:
                continue

            # Check query concentration: are recent indices getting almost all queries?
            n = len(indices)
            recent_25pct = indices[int(n * 0.75):]  # newest 25%
            recent_50pct = indices[int(n * 0.50):]  # newest 50%
            q_25 = sum(i.query_total for i in recent_25pct) / total_queries if total_queries else 0
            q_50 = sum(i.query_total for i in recent_50pct) / total_queries if total_queries else 0

            if q_25 >= 0.95 and n > 8:
                # 95%+ queries in newest 25% — strong signal
                old_indices = indices[:int(n * 0.75)]
                old_size = sum(i.size_bytes for i in old_indices)
                old_size_gb = old_size / (1024**3)
                annual = old_size_gb * self.cost_per_gb_month * 12

                reasons = [
                    f"{q_25:.0%} of queries hit the newest 25% of indices",
                    f"{len(old_indices)} older indices ({old_size_gb:.1f} GB) rarely queried",
                    f"Pattern: {base}-* has {n} indices spanning long retention",
                ]

                recs.append(
                    Recommendation(
                        action=Action.REDUCE_RETENTION,
                        target=f"{base}-*",
                        confidence=Confidence.HIGH,
                        reasons=reasons,
                        size_bytes=old_size,
                        annual_savings=annual,
                        index_count=len(old_indices),
                    )
                )
            elif q_50 >= 0.90 and n > 14:
                # 90%+ queries in newest 50% — moderate signal
                old_indices = indices[:int(n * 0.50)]
                old_size = sum(i.size_bytes for i in old_indices)
                old_size_gb = old_size / (1024**3)
                annual = old_size_gb * self.cost_per_gb_month * 12

                reasons = [
                    f"{q_50:.0%} of queries hit the newest 50% of indices",
                    f"{len(old_indices)} older indices ({old_size_gb:.1f} GB) rarely queried",
                    f"Pattern: {base}-* has {n} indices spanning long retention",
                ]

                recs.append(
                    Recommendation(
                        action=Action.REDUCE_RETENTION,
                        target=f"{base}-*",
                        confidence=Confidence.MEDIUM,
                        reasons=reasons,
                        size_bytes=old_size,
                        annual_savings=annual,
                        index_count=len(old_indices),
                    )
                )

        return recs
