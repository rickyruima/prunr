"""Data models for Prunr."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SKIP = "SKIP"


class Priority(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Action(Enum):
    DELETE = "DELETE"
    REDUCE_RETENTION = "REDUCE RETENTION"
    MERGE_SHARDS = "MERGE SHARDS"
    REVIEW = "REVIEW"


@dataclass
class IndexInfo:
    name: str
    size_bytes: int
    doc_count: int
    primary_shards: int
    replica_shards: int
    total_shards: int
    query_rate: float  # queries per second (approximation from cumulative stats)
    query_total: int  # total queries since last restart
    indexing_total: int  # total docs indexed since last restart
    indexing_rate: float  # docs indexed per second (approximation)
    health: str  # green/yellow/red
    status: str  # open/close
    creation_date_ms: int | None = None
    last_query_at: str | None = None  # ISO timestamp, e.g. "2026-04-12T18:00:00Z"
    last_write_at: str | None = None  # ISO timestamp
    created_at: str | None = None  # ISO timestamp

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024**3)

    @property
    def avg_shard_size_mb(self) -> float:
        if self.total_shards == 0:
            return 0
        return (self.size_bytes / self.total_shards) / (1024**2)


@dataclass
class ClusterInfo:
    name: str
    node_count: int
    total_indices: int
    total_size_bytes: int
    total_docs: int
    indices: list[IndexInfo] = field(default_factory=list)

    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024**3)


@dataclass
class Recommendation:
    action: Action
    target: str  # index name or pattern
    confidence: Confidence
    reasons: list[str]
    size_bytes: int = 0
    annual_savings: float = 0.0  # estimated in USD
    index_count: int = 1  # how many indices this covers
    priority: Priority = Priority.MEDIUM  # how urgently this should be addressed

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024**3)


@dataclass
class ScanReport:
    cluster: ClusterInfo
    recommendations: list[Recommendation] = field(default_factory=list)
    summary: list[str] = field(default_factory=list)
    cost_per_gb_month: float = 0.50  # default, user can override
    scan_timestamp: str = ""

    @property
    def estimated_monthly_cost(self) -> float:
        return self.cluster.total_size_gb * self.cost_per_gb_month

    @property
    def estimated_annual_cost(self) -> float:
        return self.estimated_monthly_cost * 12

    @property
    def total_annual_savings(self) -> float:
        return sum(r.annual_savings for r in self.recommendations)
