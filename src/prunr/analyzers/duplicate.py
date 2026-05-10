"""Detect potential duplicate log data across indices."""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import Action, ClusterInfo, Confidence, Recommendation

# Strip dates, numbers, and common suffixes to find base service name
STRIP_PATTERN = re.compile(r"[-_](\d{4}[.\-_]\d{2}([.\-_]\d{2})?|\d+)$")
# Extract service name: everything before the data-type suffix
# e.g., "nginx-access-logs-2025.01" -> "nginx-access"
# e.g., "app-prod-logs-2026.04" -> "app-prod"
SERVICE_PATTERN = re.compile(r"^(.+?)[-_](logs?|data|events|raw|processed|archive)(?:[-_]|$)")


class DuplicateDetector:
    def __init__(self, cost_per_gb_month: float):
        self.cost_per_gb_month = cost_per_gb_month

    def analyze(self, cluster: ClusterInfo) -> list[Recommendation]:
        # Group by likely service/source
        groups: dict[str, list] = defaultdict(list)

        for idx in cluster.indices:
            key = self._extract_service(idx.name)
            if key:
                groups[key].append(idx)

        recs: list[Recommendation] = []

        for service, indices in groups.items():
            # Need multiple distinct index patterns (not just date rollover)
            base_names = set()
            for idx in indices:
                stripped = STRIP_PATTERN.sub("", idx.name)
                base_names.add(stripped)

            if len(base_names) < 2:
                continue

            # Same service, different index patterns = possible duplication
            total_size = sum(i.size_bytes for i in indices)
            total_size_gb = total_size / (1024**3)

            # Estimate: if truly duplicated, ~50% is waste
            potential_waste_gb = total_size_gb * 0.5
            annual = potential_waste_gb * self.cost_per_gb_month * 12

            index_names = [i.name for i in indices]
            reasons = [
                f"Service '{service}' has {len(base_names)} index families that may overlap:",
                *[f"  - {name}" for name in sorted(base_names)[:5]],
                f"Combined size: {total_size_gb:.1f} GB",
                "Review pipeline ownership and source routing",
                f"Indices: {', '.join(sorted(index_names))}",
            ]

            recs.append(
                Recommendation(
                    action=Action.REVIEW,
                    target=f"{service}-* (multiple patterns)",
                    confidence=Confidence.LOW,
                    reasons=reasons,
                    size_bytes=total_size,
                    annual_savings=annual,
                    index_count=len(indices),
                )
            )

        return recs

    def _extract_service(self, name: str) -> str | None:
        """Extract root service name for duplicate grouping.

        'nginx-access-2025.01' and 'nginx-logs-2026.04' -> both 'nginx'
        'app-prod-logs' stays separate from 'app-debug' (qualified by purpose).
        """
        # Strip date/version suffix first
        stripped = STRIP_PATTERN.sub("", name)
        stripped = re.sub(r"[-_]v\d+$", "", stripped)

        # Split into segments
        parts = re.split(r"[-_]", stripped)
        if not parts:
            return None

        # Data-type words (these describe what kind of data, not the service)
        data_types = {"logs", "log", "data", "events", "raw", "processed", "archive", "access"}
        # Purpose qualifiers (these differentiate different uses of same service)
        qualifiers = {"prod", "staging", "debug", "test", "dev", "qa", "tmp", "temp"}

        # Build service name: keep non-data-type segments
        # But preserve qualifiers to differentiate purpose
        service_parts = []
        for p in parts:
            if p.lower() in data_types:
                break  # stop at first data-type word
            service_parts.append(p)

        if not service_parts:
            return parts[0] if parts else None

        service = "-".join(service_parts)

        # If service is too generic (single short word), and there's a qualifier,
        # include it to avoid false grouping
        if len(service_parts) == 1 and len(parts) > 1:
            next_part = parts[1] if len(parts) > 1 else ""
            if next_part.lower() in qualifiers:
                service = f"{service_parts[0]}-{next_part}"

        return service if service else None
