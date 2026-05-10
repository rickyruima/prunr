# Prunr

**Scan your Elasticsearch / OpenSearch cluster. Find dead indices, wasted storage, and cost savings.**

Prunr is a read-only CLI tool that connects to your cluster, analyzes index usage patterns, and tells you exactly what you can safely delete, shrink, or archive — with confidence levels and estimated savings.

> **Prunr never writes to your cluster.** All operations are read-only. It uses `_cat/indices`, `_stats`, and `_cluster/health` — nothing else.

---

## Install

```bash
pip install prunr
```

Or with [pipx](https://pipx.pypa.io/) (recommended):

```bash
pipx install prunr
```

Requires Python 3.11+.

## Quick start

```bash
# Scan a cluster
prunr scan --host http://localhost:9200

# With authentication
prunr scan --host https://my-cluster:9200 --user admin --password secret

# Save JSON report
prunr scan --host http://localhost:9200 --format json --output report.json

# Try it without a cluster (built-in demo data)
prunr scan --demo
```

## Sample output

```
╭──────────────────────────────────────────────────────────────────────────────╮
│ PRUNR CLUSTER REPORT                                                         │
│ Cluster: prod-logging-cluster  |  26 indices  |  1024.3 GB  |  12 nodes      │
│ Scanned: 2026-04-13 01:24:38 UTC                                             │
╰──────────────────────────────────────────────────────────────────────────────╯

╭─────────────────────────────── Cost Overview ────────────────────────────────╮
│   ESTIMATED MONTHLY COST:  $102                                              │
│   ESTIMATED ANNUAL WASTE:  $167                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

TOP RECOMMENDATIONS (by annual savings)

  1. REVIEW  api-access-* (multiple patterns)  (90.3 GB)
     Confidence: LOW
     Annual savings: $54
     Reasoning:
       ⚠ Service 'api-access' appears in 2 different index patterns
       ⚠ These may contain overlapping data from multiple pipelines

  2. DELETE  filebeat-2024.01  (26.1 GB)
     Confidence: MEDIUM
     Annual savings: $31
     Reasoning:
       ⚠ 0 queries since cluster restart
       ⚠ 0 indexing activity

  3. DELETE  debug-traces-2024.08.15  (11.5 GB)
     Confidence: HIGH
     Annual savings: $14
     Reasoning:
       ✓ 0 queries since cluster restart
       ✓ 0 indexing activity
       ✓ Index name matches low-value pattern: debug-traces-2024.08.15
```

A full sample JSON report is in [`examples/sample-report.json`](examples/sample-report.json).

## What Prunr detects

| Analyzer | What it finds | Action |
|---|---|---|
| **Dead index** | Indices with 0 queries and 0 writes since last restart | DELETE |
| **Retention** | Date-based index series where old indices are never queried | REDUCE RETENTION |
| **Storage hog** | Largest indices by size — surfaces the biggest saving opportunities | REVIEW |
| **Duplicate** | Multiple versioned indices (e.g. `logs-v1`, `logs-v2`) that may overlap | REVIEW |
| **Shard** | Over-sharded indices (many tiny shards wasting cluster memory) | MERGE SHARDS |

Each recommendation includes:
- **Confidence level**: HIGH, MEDIUM, or LOW
- **Evidence**: specific metrics (query count, indexing rate, size, pattern matches)
- **Estimated annual savings** in USD (based on `--cost-per-gb`, default $0.10/GB/mo)

## Confidence levels

| Level | Meaning |
|---|---|
| **HIGH** | Strong evidence — safe to act on after quick verification |
| **MEDIUM** | Likely waste — worth investigating |
| **LOW** | Possible issue — needs human review before acting |

## CLI reference

```
prunr scan [OPTIONS]

Options:
  --host TEXT              ES/OpenSearch URL (e.g. https://localhost:9200)
  --api-key TEXT           API key for authentication
  --user TEXT              Username for basic auth
  --password TEXT          Password for basic auth
  --cost-per-gb FLOAT     Cost per GB per month in USD (default: 0.10)
  --format [terminal|json] Output format (default: terminal)
  --output TEXT            Save report to file
  --no-verify-certs       Skip TLS certificate verification
  --demo                  Run with built-in sample data (no cluster needed)
```

## Safety

Prunr is **strictly read-only**. It will never:

- Delete, close, or modify any index
- Change cluster settings
- Write data to your cluster
- Require any write permissions

The only APIs it calls are:
- `GET /` (version check)
- `GET /_cat/indices`
- `GET /_stats`
- `GET /_cluster/health`

You can safely run it against production clusters.

## Limitations

- Query and indexing counts reset on node restart — Prunr can only see activity since the last restart
- Cost estimates use a flat $/GB/month rate; real costs depend on instance types, reserved pricing, and I/O
- Duplicate detection is heuristic (name-pattern based), not content-based
- Currently supports a single cluster per scan

## Development

```bash
git clone https://github.com/rickyruima/prunr.git
cd prunr
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -v
```

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.
