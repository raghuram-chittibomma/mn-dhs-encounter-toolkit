"""Web UI support layer — enriches validator output for human-facing tools.

The Streamlit app and any future HTTP API should call into this package;
validator and CLI logic stay unchanged in validator/ and cli/.
"""

from mn_encounter_toolkit.web.enrich import ClaimSummary, EnrichedFinding, enrich_findings, summarize_claims
from mn_encounter_toolkit.web.validate_service import ValidationReport, validate_upload

__all__ = [
    "ClaimSummary",
    "EnrichedFinding",
    "ValidationReport",
    "enrich_findings",
    "summarize_claims",
    "validate_upload",
]
