"""Generate cluster-level summary findings."""

from __future__ import annotations

from ..models import Action, ClusterInfo, Recommendation


def generate_summary(cluster: ClusterInfo, recs: list[Recommendation]) -> list[str]:
    """Produce high-level cluster findings from recommendations."""
    findings: list[str] = []

    total_size = cluster.total_size_bytes
    if total_size == 0:
        return findings

    # 1. Percentage of storage in low/no-usage indices
    no_query_size = sum(i.size_bytes for i in cluster.indices if i.query_total == 0)
    if no_query_size > 0:
        pct = (no_query_size / total_size) * 100
        gb = no_query_size / 1024**3
        findings.append(
            f"{pct:.0f}% of storage ({gb:.1f} GB) is in indices with no search activity"
        )

    # 2. Duplicate families
    dup_recs = [
        r for r in recs if r.action == Action.REVIEW and "may overlap" in " ".join(r.reasons).lower()
    ]
    if dup_recs:
        count = sum(r.index_count for r in dup_recs)
        findings.append(
            f"{len(dup_recs)} index families may have overlapping ingestion paths ({count} indices)"
        )

    # 3. Over-sharding — count from indices directly
    over_sharded = [
        idx for idx in cluster.indices if idx.total_shards > 10 and idx.avg_shard_size_mb < 200
    ]
    if over_sharded:
        total_shards = sum(idx.total_shards for idx in over_sharded)
        total_shard_size = sum(idx.size_bytes for idx in over_sharded)
        size_mb = total_shard_size / 1024**2
        findings.append(
            f"{len(over_sharded)} indices are over-sharded: "
            f"{total_shards} shards hold only {size_mb:.0f} MB of data"
        )

    # 4. Retention opportunities
    ret_recs = [r for r in recs if r.action == Action.REDUCE_RETENTION]
    if ret_recs:
        total_idx = sum(r.index_count for r in ret_recs)
        findings.append(
            f"{len(ret_recs)} index families may have excessive retention ({total_idx} indices)"
        )

    # 5. Total recoverable savings
    total_savings = sum(r.annual_savings for r in recs)
    if total_savings > 0:
        findings.append(
            f"Estimated ${total_savings:,.0f}/year recoverable through recommended actions"
        )

    return findings
