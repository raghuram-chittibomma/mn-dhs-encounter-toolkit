"""Shared helpers for web UI services."""

from __future__ import annotations


def parse_outcome_weights(spec: str | None) -> dict[str, int] | None:
    """Parse ``A=70,E=20,R=10`` into a weight dict."""
    if not spec or not spec.strip():
        return None
    weights: dict[str, int] = {}
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        key, _, value = chunk.partition("=")
        weights[key.strip()] = int(value.strip())
    return weights or None


def read_upload_text(uploaded_file) -> str:
    return uploaded_file.read().decode("utf-8", errors="replace")
