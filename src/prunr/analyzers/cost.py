"""Estimate per-index costs."""

from __future__ import annotations

from ..models import ClusterInfo, Recommendation


class CostEstimator:
    """Attaches cost estimates. Does not produce standalone recommendations —
    other analyzers reference cost_per_gb_month directly."""

    def __init__(self, cost_per_gb_month: float):
        self.cost_per_gb_month = cost_per_gb_month

    def analyze(self, cluster: ClusterInfo) -> list[Recommendation]:
        # Cost estimation is embedded in other analyzers.
        # This exists as a hook for future standalone cost reports.
        return []
