"""Seed an OpenSearch/ES cluster with curated test data from fixtures."""

from __future__ import annotations

import json
import random
import string
from .client import Connection
from .fixtures import make_v2_indices


def clean_seeded_indices(conn: Connection, *, verbose: bool = True) -> None:
    """Delete only the indices that seed would create (leaves other indices intact)."""
    indices = make_v2_indices()
    names = [idx.name for idx in indices]
    deleted = 0
    for name in names:
        try:
            conn.get(f"/{name}")
            conn.request("DELETE", f"/{name}")
            deleted += 1
            if verbose:
                print(f"  Deleted {name}")
        except Exception:
            pass
    if verbose:
        print(f"Cleaned {deleted} seeded indices.")


def seed_cluster(conn: Connection, *, verbose: bool = True) -> None:
    """Create all fixture indices with realistic data in a live cluster."""
    indices = make_v2_indices()

    if verbose:
        print(f"Seeding {len(indices)} indices...")

    for idx in indices:
        # Skip if index already exists
        try:
            conn.get(f"/{idx.name}")
            if verbose:
                size_str = (
                    f"{idx.size_bytes / 1024**3:.1f} GB"
                    if idx.size_bytes >= 1024**3
                    else f"{idx.size_bytes / 1024**2:.0f} MB"
                )
                print(f"  {idx.name} ({size_str}) — already exists, skipping")
            continue
        except Exception:
            pass

        # Create with settings
        settings = {
            "settings": {
                "number_of_shards": idx.primary_shards,
                "number_of_replicas": 0,  # single-node test clusters
            }
        }
        conn.request("PUT", f"/{idx.name}", body=settings)

        # Bulk insert docs (enough to hit target size approximately)
        # We can't perfectly match size, but we insert enough docs to be realistic
        target_docs = min(idx.doc_count, 500)  # cap at 500 per index for speed
        if target_docs > 0:
            _bulk_insert(conn, idx.name, target_docs, idx.size_bytes)

        # Generate search activity to match query_total
        if idx.query_total > 0:
            searches = min(idx.query_total, 20)  # cap for speed
            for _ in range(searches):
                try:
                    conn.request(
                        "POST",
                        f"/{idx.name}/_search",
                        body={"query": {"match_all": {}}, "size": 1},
                    )
                except Exception as e:
                    if verbose:
                        print(f"  WARNING: search on {idx.name} failed: {e}")
                    break

        if verbose:
            size_str = (
                f"{idx.size_bytes / 1024**3:.1f} GB"
                if idx.size_bytes >= 1024**3
                else f"{idx.size_bytes / 1024**2:.0f} MB"
            )
            print(
                f"  {idx.name} ({size_str}, {idx.primary_shards} shards, {target_docs} docs seeded)"
            )

    # Refresh all
    try:
        conn.request("POST", "/_refresh")
    except Exception as e:
        if verbose:
            print(f"  WARNING: refresh failed: {e}")

    if verbose:
        print(f"Done — {len(indices)} indices created.")


def _bulk_insert(conn: Connection, index: str, count: int, target_size: int) -> None:
    """Insert documents via _bulk API."""
    # Estimate doc size to roughly approach target
    avg_doc_size = max(100, min(5000, target_size // max(count, 1)))

    lines: list[str] = []
    batch_size = min(count, 100)

    for i in range(count):
        lines.append(json.dumps({"index": {}}))
        lines.append(json.dumps(_make_doc(avg_doc_size)))

        if len(lines) >= batch_size * 2:
            _send_bulk(conn, index, lines)
            lines = []

    if lines:
        _send_bulk(conn, index, lines)


def _send_bulk(conn: Connection, index: str, lines: list[str]) -> None:
    body = "\n".join(lines) + "\n"
    try:
        resp = conn.request(
            "POST",
            f"/{index}/_bulk",
            body=body,
            headers={"Content-Type": "application/x-ndjson"},
        )
        if isinstance(resp, dict) and resp.get("errors"):
            first_err = next(
                (item["index"]["error"]["reason"]
                 for item in resp.get("items", [])
                 if "error" in item.get("index", {})),
                "unknown error",
            )
            print(f"  WARNING: bulk insert to {index} had errors: {first_err}")
    except Exception as e:
        print(f"  WARNING: bulk insert to {index} failed: {e}")


def _make_doc(target_size: int) -> dict:
    """Generate a realistic-looking log document."""
    ts = f"2025-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}Z"
    levels = ["INFO", "WARN", "ERROR", "DEBUG"]
    services = ["api-gateway", "auth-service", "payments", "search", "notifications"]

    doc = {
        "@timestamp": ts,
        "level": random.choice(levels),
        "service": random.choice(services),
        "message": "".join(
            random.choices(string.ascii_lowercase + " ", k=max(50, target_size - 200))
        ),
        "host": f"node-{random.randint(1, 20):02d}",
        "request_id": "".join(random.choices(string.hexdigits, k=32)),
    }
    return doc
