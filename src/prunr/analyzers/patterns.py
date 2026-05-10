"""Shared patterns used across analyzers."""

from __future__ import annotations

import re

COMPLIANCE_PATTERNS = [
    re.compile(r"audit", re.IGNORECASE),
    re.compile(r"compliance", re.IGNORECASE),
    re.compile(r"pci", re.IGNORECASE),
    re.compile(r"sox", re.IGNORECASE),
    re.compile(r"hipaa", re.IGNORECASE),
    re.compile(r"gdpr", re.IGNORECASE),
    re.compile(r"security[-_]", re.IGNORECASE),
    re.compile(r"legal[-_]", re.IGNORECASE),
    re.compile(r"forensic", re.IGNORECASE),
    re.compile(r"litigation", re.IGNORECASE),
]


def is_compliance_index(name: str) -> bool:
    return any(p.search(name) for p in COMPLIANCE_PATTERNS)
