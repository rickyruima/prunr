"""Detect over-sharded indices."""

from __future__ import annotations

from ..models import Action, ClusterInfo, Confidence, Recommendation
from .patterns import is_compliance_index

# ES best practice: shards should be 10-50 GB each
MIN_SHARD_SIZE_MB = 1024  # 1 GB — below this is over-sharded
MAX_SHARDS_PER_INDEX = 50


class ShardOptimizer:
    def analyze(self, cluster: ClusterInfo) -> list[Recommendation]:
        recs: list[Recommendation] = []

        for idx in cluster.indices:
            if idx.total_shards <= 1:
                continue

            avg_mb = idx.avg_shard_size_mb
            is_compliance = is_compliance_index(idx.name)

            if idx.total_shards > MAX_SHARDS_PER_INDEX and avg_mb < MIN_SHARD_SIZE_MB:
                # Severely over-sharded: many tiny shards — always flag even for compliance
                ideal_shards = max(1, int(idx.size_gb / 30))  # target ~30 GB per shard

                reasons = [
                    f"{idx.total_shards} shards averaging {avg_mb:.0f} MB each",
                    f"Recommended: ~{ideal_shards} shards @ ~30 GB each",
                    "Over-sharding wastes cluster memory and slows queries",
                    "Read-only optimization — no data loss",
                ]

                if is_compliance:
                    reasons.append(
                        "Compliance index — coordinate with data governance before changes"
                    )

                recs.append(
                    Recommendation(
                        action=Action.MERGE_SHARDS,
                        target=idx.name,
                        confidence=Confidence.HIGH,
                        reasons=reasons,
                        size_bytes=idx.size_bytes,
                        annual_savings=0,
                    )
                )

            elif avg_mb < 200 and idx.total_shards > 5:
                # Moderately over-sharded — shards under 200 MB
                reasons = [
                    f"{idx.total_shards} shards averaging {avg_mb:.0f} MB each",
                    "Small shards add unnecessary cluster overhead",
                ]

                if is_compliance:
                    reasons.append(
                        "Compliance index — coordinate with data governance before changes"
                    )

                recs.append(
                    Recommendation(
                        action=Action.REVIEW if is_compliance else Action.MERGE_SHARDS,
                        target=idx.name,
                        confidence=Confidence.MEDIUM,
                        reasons=reasons,
                        size_bytes=idx.size_bytes,
                        annual_savings=0,
                    )
                )

        return recs
