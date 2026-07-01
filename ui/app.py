"""Streamlit UI for MN DHS encounter 837 validation.

Run with:
    streamlit run ui/app.py
or:
    mn-encounter-ui
"""

from __future__ import annotations

import streamlit as st

from mn_encounter_toolkit.web.enrich import EnrichedFinding
from mn_encounter_toolkit.web.validate_service import (
    ALL_LAYER_NUMBERS,
    ValidationReport,
    report_to_csv,
    report_to_json,
    validate_upload,
)

st.set_page_config(
    page_title="MN DHS Encounter Validator",
    page_icon="📋",
    layout="wide",
)


def _render_finding(item: EnrichedFinding) -> None:
    finding = item.finding
    severity = finding.severity.upper()
    loc = f"line {finding.line_number}" if finding.line_number is not None else "no line"
    seg = f" [{finding.segment_id}]" if finding.segment_id else ""
    title = f"[{severity}] Layer {finding.layer} — {finding.rule_id} ({loc}){seg}"
    with st.expander(title, expanded=finding.severity == "error"):
        st.write(finding.message)
        if finding.source_citation:
            st.caption(f"SOURCE: {finding.source_citation}")
        if item.segment_snippet:
            st.code(item.segment_snippet, language=None)
        if item.context_lines:
            st.markdown("**Nearby segments**")
            st.code("\n".join(item.context_lines), language=None)
        if item.billing_loop_note:
            st.markdown("**Billing loop context**")
            st.code(item.billing_loop_note, language=None)


def _render_results(report: ValidationReport, uploaded_name: str) -> None:
    if not report.findings:
        st.success("No findings — all selected layers passed.")
        return

    download_col1, download_col2 = st.columns(2)
    download_col1.download_button(
        "Download JSON report",
        data=report_to_json(report),
        file_name=f"{uploaded_name}.validation.json",
        mime="application/json",
    )
    download_col2.download_button(
        "Download CSV report",
        data=report_to_csv(report),
        file_name=f"{uploaded_name}.validation.csv",
        mime="text/csv",
    )

    file_findings = [item for item in report.findings if item.scope == "file"]
    claim_findings = [item for item in report.findings if item.scope == "claim"]

    if file_findings:
        st.markdown("### File / envelope")
        for item in file_findings:
            _render_finding(item)

    claims_with_findings: dict[int, list[EnrichedFinding]] = {}
    for item in claim_findings:
        claims_with_findings.setdefault(item.claim_index or 0, []).append(item)

    for claim_index in sorted(claims_with_findings):
        items = claims_with_findings[claim_index]
        sample = items[0]
        header = f"Claim {claim_index}"
        if sample.claim_id:
            header += f" — {sample.claim_id}"
        if sample.claim_type:
            header += f" ({sample.claim_type})"
        st.markdown(f"### {header}")
        details = []
        if sample.subscriber_hl_id:
            details.append(f"Subscriber HL **{sample.subscriber_hl_id}**")
        if sample.billing_hl_id:
            details.append(f"Billing HL **{sample.billing_hl_id}**")
        if sample.member_name or sample.member_id:
            member = sample.member_name or "—"
            mid = sample.member_id or "—"
            details.append(f"Member **{member}** (ID {mid})")
        if details:
            st.caption(" · ".join(details))
        for item in items:
            _render_finding(item)


def main() -> None:
    st.title("MN DHS Encounter Validator")
    st.caption(
        "Upload an 837P/837I encounter file to run compliance validation. "
        "Files are processed in memory and are not stored on disk."
    )

    with st.sidebar:
        st.header("Validation options")
        layer_selection = {
            number: st.checkbox(f"Layer {number}", value=True, key=f"layer_{number}")
            for number in ALL_LAYER_NUMBERS
        }
        layer_labels = {
            1: "Envelope (ISA/GS/ST)",
            2: "X12 syntax",
            3: "DHS business rules",
            4: "Cross-field consistency",
        }
        for number, label in layer_labels.items():
            st.caption(f"**Layer {number}:** {label}")

    uploaded = st.file_uploader("837 file (.x12)", type=["x12", "txt", "edi"])

    if uploaded is None:
        st.info("Upload a file to begin validation.")
        return

    selected_layers = tuple(number for number, enabled in layer_selection.items() if enabled)
    if not selected_layers:
        st.error("Select at least one validation layer.")
        return

    text = uploaded.read().decode("utf-8", errors="replace")
    report = validate_upload(text, filename=uploaded.name, layer_numbers=selected_layers)

    if report.parse_error:
        st.error(f"Could not parse file: {report.parse_error}")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Claims in file", len(report.claims))
    col2.metric("Errors", report.error_count)
    col3.metric("Warnings", report.warning_count)
    col4.metric("Exit code", report.exit_code)

    if report.passed:
        st.success(f"{report.filename}: PASS — no error-level findings.")
    else:
        st.error(f"{report.filename}: {report.error_count} error(s) found.")

    if report.claims:
        st.subheader("Claims in this file")
        st.dataframe(
            [
                {
                    "#": claim.claim_index,
                    "Claim ID": claim.claim_id or "—",
                    "Type": claim.claim_type,
                    "Subscriber HL": claim.subscriber_hl_id,
                    "Billing HL": claim.billing_hl_id,
                    "Member ID": claim.member_id or "—",
                    "Member name": claim.member_name or "—",
                }
                for claim in report.claims
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Findings")
    _render_results(report, uploaded.name)


if __name__ == "__main__":
    main()
