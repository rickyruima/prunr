"""Detect indices that look like audit/compliance data — flag for human review."""

from __future__ import annotations

from ..models import Action, ClusterInfo, Confidence, Recommendation
from .patterns import COMPLIANCE_PATTERNS


class ComplianceDetector:
    def __init__(self, cost_per_gb_month: float):
        self.cost_per_gb_month = cost_per_gb_month

    def analyze(self, cluster: ClusterInfo) -> list[Recommendation]:
        recs: list[Recommendation] = []

        for idx in cluster.indices:
            if not any(p.search(idx.name) for p in COMPLIANCE_PATTERNS):
                continue

            reasons = [
                "Index name suggests audit or compliance data",
                f"Low query activity ({idx.query_total:,} queries observed)",
                f"Size: {idx.size_gb:.1f} GB",
                "May be subject to regulatory retention requirements — verify before deletion",
            ]

            recs.append(
                Recommendation(
                    action=Action.REVIEW,
                    target=idx.name,
                    confidence=Confidence.LOW,
                    reasons=reasons,
                    size_bytes=idx.size_bytes,
                    annual_savings=0,  # can't recommend deletion
                )
            )

        return recs
