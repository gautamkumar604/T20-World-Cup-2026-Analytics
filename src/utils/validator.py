"""
Validation utilities for data integrity, cryptographic checksums, and schema verification.
"""

import hashlib
from pathlib import Path
from typing import Dict, Any


def compute_sha256(file_path: Path, block_size: int = 65536) -> str:
    """Computes the SHA-256 hash of a given file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            sha256.update(block)
    return sha256.hexdigest()


def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """Verifies that a file matches the expected SHA-256 hash."""
    computed = compute_sha256(file_path)
    return computed.lower() == expected_hash.strip().lower()


def validate_cricsheet_json_structure(data: Dict[str, Any]) -> bool:
    """
    Validates that a dictionary conforms to Cricsheet JSON top-level requirements.
    Must contain 'meta' and 'info' keys, and 'info' must have 'dates' and 'teams'.
    """
    if not isinstance(data, dict):
        return False

    if "meta" not in data or "info" not in data:
        return False

    info = data.get("info", {})
    if not isinstance(info, dict):
        return False

    if "dates" not in info or "teams" not in info:
        return False

    return True

