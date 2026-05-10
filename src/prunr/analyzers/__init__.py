"""Analyzers that produce recommendations from cluster data."""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import Action, ClusterInfo, Confidence, Priority, Recommendation
from .compliance import ComplianceDetector
from .cost import CostEstimator
from .dead_index import DeadIndexDetector
from .duplicate import DuplicateDetector
from .retention import RetentionAnalyzer
from .shard import ShardOptimizer
from .storage_hog import StorageHogRanker

CONFIDENCE_RANK = {
    Confidence.HIGH: 3,
    Confidence.MEDIUM: 2,
    Confidence.LOW: 1,
    Confidence.SKIP: 0,
}

PRIORITY_RANK = {
    Priority.HIGH: 3,
    Priority.MEDIUM: 2,
    Priority.LOW: 1,
}

# Pattern to extract family base from index names (strip dates, versions, suffixes)
_FAMILY_PATTERN = re.compile(
    r"^(.*?)(?:[-_]v\d+|[-_]\d{4}[.\-_]\d{2}(?:[.\-_]\d{2})?|[-_]\d{4}\.q\d)$"
)


def _index_family(name: str) -> str:
    """Extract family base name: 'filebeat-debug-2025.01' -> 'filebeat-debug'."""
    m = _FAMILY_PATTERN.match(name)
    return m.group(1) if m else name


def _calculate_priority(rec: Recommendation) -> Priority:
    """Determine priority based on savings and size — independent of confidence."""
    # High priority: significant savings or large size
    if rec.annual_savings >= 10:
        return Priority.HIGH
    if rec.size_bytes >= 5 * 1024**3:  # >= 5 GB
        return Priority.HIGH

    # Medium priority: moderate savings or size
    if rec.annual_savings >= 1:
        return Priority.MEDIUM
    if rec.size_bytes >= 500 * 1024**2:  # >= 500 MB
        return Priority.MEDIUM

    # Low priority: tiny savings, small size
    return Priority.LOW


def run_all(cluster: ClusterInfo, cost_per_gb_month: float) -> list[Recommendation]:
    """Run all analyzers and return recommendations sorted by impact."""
    analyzers = [
        DeadIndexDetector(cost_per_gb_month),
        RetentionAnalyzer(cost_per_gb_month),
        StorageHogRanker(cost_per_gb_month),
        DuplicateDetector(cost_per_gb_month),
        ShardOptimizer(),
        ComplianceDetector(cost_per_gb_month),
        CostEstimator(cost_per_gb_month),
    ]

    recs: list[Recommendation] = []
    for analyzer in analyzers:
        recs.extend(analyzer.analyze(cluster))

    # Deduplicate by target
    # Rule: REVIEW from compliance always wins over DELETE (safety override)
    # Otherwise: keep highest savings, then highest confidence
    seen: dict[str, Recommendation] = {}
    for r in recs:
        if r.target not in seen:
            seen[r.target] = r
        else:
            existing = seen[r.target]
            # Compliance REVIEW overrides DELETE — never auto-delete compliance data
            if r.action == Action.REVIEW and existing.action == Action.DELETE:
                seen[r.target] = r
            elif existing.action == Action.REVIEW and r.action == Action.DELETE:
                pass  # keep existing REVIEW
            elif r.annual_savings > existing.annual_savings or (
                r.annual_savings == existing.annual_savings
                and CONFIDENCE_RANK.get(r.confidence, 0)
                > CONFIDENCE_RANK.get(existing.confidence, 0)
            ):
                seen[r.target] = r

    deduped = list(seen.values())

    # Calculate priority for each rec
    for r in deduped:
        r.priority = _calculate_priority(r)

    # Group single-index DELETE recs into families
    grouped = _group_into_families(deduped)

    # Sort: priority first, then confidence, then size
    result = sorted(
        grouped,
        key=lambda r: (
            PRIORITY_RANK.get(r.priority, 0),
            CONFIDENCE_RANK.get(r.confidence, 0),
            r.size_bytes,
        ),
        reverse=True,
    )

    return result


def _group_into_families(recs: list[Recommendation]) -> list[Recommendation]:
    """Merge individual DELETE recs for the same index family into one grouped rec."""
    # Separate: groupable DELETE recs vs everything else
    groupable: list[Recommendation] = []
    other: list[Recommendation] = []

    for r in recs:
        if r.action == Action.DELETE and r.index_count == 1:
            groupable.append(r)
        else:
            other.append(r)

    # Group by family
    families: dict[str, list[Recommendation]] = defaultdict(list)
    for r in groupable:
        family = _index_family(r.target)
        families[family].append(r)

    result = list(other)

    for family, members in families.items():
        if len(members) == 1:
            result.append(members[0])
        else:
            # Merge into family recommendation
            total_size = sum(r.size_bytes for r in members)
            total_savings = sum(r.annual_savings for r in members)
            names = sorted([r.target for r in members])
            # Best confidence in the group
            best_conf = max(members, key=lambda r: CONFIDENCE_RANK.get(r.confidence, 0)).confidence

            # Collect unique reasons from first member, add family context
            base_reasons = members[0].reasons[:2]  # core evidence
            reasons = [
                f"{len(members)} indices in family '{family}-*'",
                f"Combined size: {total_size / 1024**3:.1f} GB",
            ] + base_reasons
            reasons.append("Indices: " + ", ".join(names))

            grouped_rec = Recommendation(
                action=Action.DELETE,
                target=f"{family}-* ({len(members)} indices)",
                confidence=best_conf,
                reasons=reasons,
                size_bytes=total_size,
                annual_savings=total_savings,
                index_count=len(members),
            )
            grouped_rec.priority = _calculate_priority(grouped_rec)
            result.append(grouped_rec)

    return result
