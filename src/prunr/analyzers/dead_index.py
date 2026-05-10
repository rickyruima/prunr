"""Detect indices with no query or indexing activity."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from ..models import Action, ClusterInfo, Confidence, IndexInfo, Recommendation

# Patterns that suggest low-value / debug data
LOW_VALUE_PATTERNS = [
    re.compile(r"debug", re.IGNORECASE),
    re.compile(r"trace", re.IGNORECASE),
    re.compile(r"test", re.IGNORECASE),
    re.compile(r"tmp", re.IGNORECASE),
    re.compile(r"temp", re.IGNORECASE),
    re.compile(r"dev[-_]", re.IGNORECASE),
    re.compile(r"staging", re.IGNORECASE),
]


class DeadIndexDetector:
    def __init__(self, cost_per_gb_month: float):
        self.cost_per_gb_month = cost_per_gb_month

    def analyze(self, cluster: ClusterInfo) -> list[Recommendation]:
        recs: list[Recommendation] = []

        for idx in cluster.indices:
            if idx.query_total == 0:
                # Skip recently written indices — they may be new or just finished a job
                if self._is_recently_written(idx):
                    continue

                confidence, reasons = self._score(idx)
                if confidence == Confidence.SKIP:
                    continue

                annual = idx.size_gb * self.cost_per_gb_month * 12
                recs.append(
                    Recommendation(
                        action=Action.DELETE,
                        target=idx.name,
                        confidence=confidence,
                        reasons=reasons,
                        size_bytes=idx.size_bytes,
                        annual_savings=annual,
                    )
                )

            elif idx.query_total > 0 and idx.query_rate == 0 and idx.indexing_total == 0:
                # Had queries historically but zero current activity and never written to
                reasons = [
                    f"Total of {idx.query_total} queries historically, but 0 recent activity",
                    "No indexing activity detected",
                ]
                annual = idx.size_gb * self.cost_per_gb_month * 12
                recs.append(
                    Recommendation(
                        action=Action.REVIEW,
                        target=idx.name,
                        confidence=Confidence.MEDIUM,
                        reasons=reasons,
                        size_bytes=idx.size_bytes,
                        annual_savings=annual,
                    )
                )

        return recs

    def _is_recently_written(self, idx: IndexInfo, days: int = 14) -> bool:
        """Return True if the index was written to within the last N days."""
        if not idx.last_write_at:
            return False
        try:
            last_write = datetime.fromisoformat(idx.last_write_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - last_write
            return age.days < days
        except (ValueError, TypeError):
            return False

    def _score(self, idx: IndexInfo) -> tuple[Confidence, list[str]]:
        reasons: list[str] = []
        score = 0

        reasons.append("No observed queries in scan window")
        score += 2

        if idx.indexing_total == 0:
            reasons.append("No observed write activity")
            score += 2
        else:
            reasons.append(
                f"{idx.indexing_total:,} docs indexed historically, but not actively writing"
            )

        low_value_matches = [p for p in LOW_VALUE_PATTERNS if p.search(idx.name)]
        if low_value_matches:
            reasons.append(f"Index name matches low-value pattern: {idx.name}")
            score += 1
            if len(low_value_matches) > 1:
                score += 1  # multiple low-value signals

        if score >= 4:
            return Confidence.HIGH, reasons
        elif score >= 2:
            return Confidence.MEDIUM, reasons
        else:
            return Confidence.LOW, reasons
