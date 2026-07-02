"""Streamlit view functions shared across UI pages."""

from __future__ import annotations

import streamlit as st

from mn_encounter_toolkit.web.enrich import EnrichedFinding
from mn_encounter_toolkit.web.layer_reference import (
    LAYER_INFO,
    LAYER_SUMMARIES,
    VALIDATION_LAYERS_DOC,
    find_rules,
)
from mn_encounter_toolkit.web.validate_service import (
    ALL_LAYER_NUMBERS,
    ValidationReport,
    report_to_csv,
    report_to_json,
    validate_upload,
)


def render_finding(item: EnrichedFinding) -> None:
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


def _render_report_downloads(report: ValidationReport, uploaded_name: str) -> None:
    download_col1, download_col2 = st.columns(2)
    download_col1.download_button(
        "Download JSON report",
        data=report_to_json(report),
        file_name=f"{uploaded_name}.validation.json",
        mime="application/json",
        key=f"json_{uploaded_name}",
    )
    download_col2.download_button(
        "Download CSV report",
        data=report_to_csv(report),
        file_name=f"{uploaded_name}.validation.csv",
        mime="text/csv",
        key=f"csv_{uploaded_name}",
    )


def render_validation_results(report: ValidationReport, uploaded_name: str) -> None:
    _render_report_downloads(report, uploaded_name)

    if not report.findings:
        st.success("No findings — all selected layers passed.")
        return

    severity_filter = st.multiselect(
        "Filter by severity",
        options=["error", "warning", "info"],
        default=["error", "warning"],
        key=f"severity_filter_{uploaded_name}",
    )
    layer_filter = st.multiselect(
        "Filter by layer",
        options=list(ALL_LAYER_NUMBERS),
        default=list(ALL_LAYER_NUMBERS),
        key=f"layer_filter_{uploaded_name}",
    )

    filtered = [
        item
        for item in report.findings
        if item.finding.severity in severity_filter and item.finding.layer in layer_filter
    ]
    if not filtered:
        st.info("No findings match the current filters.")
        return

    file_findings = [item for item in filtered if item.scope == "file"]
    claim_findings = [item for item in filtered if item.scope == "claim"]

    if file_findings:
        st.markdown("### File / envelope")
        for item in file_findings:
            render_finding(item)

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
            render_finding(item)


def render_layer_reference_sidebar() -> None:
    st.sidebar.caption("Open **Validation layers** in the menu for the full searchable rule catalog.")


def _severity_label(severity: str) -> str:
    return {
        "error": "Error",
        "warning": "Warning",
        "info": "Info",
        "stub": "Stub (no findings)",
    }.get(severity, severity)


def page_validation_layers() -> None:
    st.header("Validation layers reference")
    st.caption(
        "What each layer checks when you validate an 837 file. "
        "Use this page to look up rule IDs from validation findings."
    )

    st.info(
        "**999 deterministic** responses use **Layers 1 and 2 only** (envelope + syntax). "
        "Layers **3 and 4** apply to full 837 validation."
    )

    overview = [
        {
            "Layer": layer.number,
            "Title": layer.title,
            "Rules": len(layer.rules),
            "Authority": layer.authority,
        }
        for layer in LAYER_INFO
    ]
    st.subheader("Overview")
    st.dataframe(overview, use_container_width=True, hide_index=True)

    st.subheader("Search rules")
    query = st.text_input(
        "Search by rule ID or keyword",
        placeholder="e.g. UMPI, L3-BILLING, charge, ISA",
        key="layer_ref_search",
    )
    if query.strip():
        matches = find_rules(query)
        if not matches:
            st.warning("No rules matched your search.")
        else:
            st.dataframe(
                [
                    {
                        "Layer": layer.number,
                        "Rule ID": rule.rule_id,
                        "Severity": _severity_label(rule.severity),
                        "Description": rule.description,
                        "Notes": rule.notes,
                    }
                    for layer, rule in matches
                ],
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("Rules by layer")
    tabs = st.tabs([f"Layer {layer.number}" for layer in LAYER_INFO])
    for tab, layer in zip(tabs, LAYER_INFO):
        with tab:
            st.markdown(f"**{layer.title}**")
            st.write(layer.scope)
            st.caption(f"**Authority:** {layer.authority}")
            st.caption(f"**Code module:** `{layer.module_path}`")
            st.dataframe(
                [
                    {
                        "Rule ID": rule.rule_id,
                        "Severity": _severity_label(rule.severity),
                        "What it checks": rule.description,
                        "Notes": rule.notes,
                    }
                    for rule in layer.rules
                ],
                use_container_width=True,
                hide_index=True,
            )

    with st.expander("Severity and exit codes"):
        st.markdown(
            """
| Severity | Meaning | Fails validation? |
|----------|---------|-------------------|
| **Error** | Must be corrected for a clean file | Yes — exit code `1` |
| **Warning** | Advisory / documented ambiguity | No — exit code stays `0` |
| **Stub** | Registered but produces no findings | No |

Parse failures return exit code `2`.
            """
        )
    st.caption(f"Repository copy: `{VALIDATION_LAYERS_DOC}`")


def page_validate() -> None:
    st.header("Validate 837")
    st.caption("Upload an 837P/837I file to run compliance validation.")

    with st.sidebar:
        st.subheader("Validation layers")
        layer_selection = {
            number: st.checkbox(
                f"Layer {number} — {LAYER_SUMMARIES[number]['title']}",
                value=True,
                key=f"val_layer_{number}",
            )
            for number in ALL_LAYER_NUMBERS
        }
        render_layer_reference_sidebar()

    uploaded = st.file_uploader("837 file (.x12)", type=["x12", "txt", "edi"], key="validate_upload")
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
    render_validation_results(report, uploaded.name)


def page_gen999() -> None:
    st.header("Generate 999")
    st.caption("Upload an 837 file to produce a 999 Implementation Acknowledgment.")

    uploaded = st.file_uploader("837 source file", type=["x12", "txt", "edi"], key="999_upload")
    mode = st.radio("Mode", ["deterministic", "simulation"], horizontal=True, key="999_mode")
    sender_id = st.text_input("999 sender ID (DHS payer)", value="411674742", key="999_sender")
    seed = 0
    outcome_weights = None
    if mode == "simulation":
        seed = st.number_input("Seed", min_value=0, value=0, step=1, key="999_seed")
        outcome_weights = st.text_input(
            "Outcome weights",
            value="A=70,E=20,R=10",
            help="A=accept, E=accept with errors, R=reject",
            key="999_weights",
        )

    if uploaded is None:
        st.info("Upload an 837 file to generate a 999.")
        return

    from mn_encounter_toolkit.web.common import read_upload_text
    from mn_encounter_toolkit.web.response_service import generate_999_from_text

    if st.button("Generate 999", type="primary", key="999_generate"):
        result = generate_999_from_text(
            read_upload_text(uploaded),
            mode=mode,
            seed=int(seed),
            outcome_weights=outcome_weights,
            sender_id=sender_id.strip(),
        )
        st.session_state["999_result"] = result
        st.session_state["999_source_name"] = uploaded.name

    result = st.session_state.get("999_result")
    if result is None:
        return
    if result.error_message:
        st.error(result.error_message)
        return

    st.success(f"Generated 999 ({result.mode} mode).")
    if result.layer1_clean:
        st.caption("Layer 1 envelope check on output: PASS")
    else:
        st.warning(f"Layer 1 envelope check on output: {result.layer1_error_count} error(s)")

    base = st.session_state.get("999_source_name", "source.x12")
    stem = base.rsplit(".", 1)[0]
    st.download_button(
        "Download 999 file",
        data=result.output_text,
        file_name=f"{stem}_999.x12",
        mime="application/octet-stream",
        key="999_download",
    )
    with st.expander("Preview first 40 lines"):
        st.code("\n".join(result.output_text.splitlines()[:40]), language=None)


def page_gen835e() -> None:
    st.header("Generate 835E")
    st.caption("Upload an 837 file to produce an 835E encounter remittance file.")

    uploaded = st.file_uploader("837 source file", type=["x12", "txt", "edi"], key="835_upload")
    mode = st.radio("Mode", ["deterministic", "simulation"], horizontal=True, key="835_mode")
    payment_method = st.selectbox("Payment method (BPR04)", ["NON", "ACH", "CHK", "FWT"], key="835_payment")
    seed = 0
    outcome_weights = None
    if mode == "simulation":
        seed = st.number_input("Seed", min_value=0, value=0, step=1, key="835_seed")
        outcome_weights = st.text_input(
            "Outcome weights",
            value="paid_full=55,paid_partial=30,denied=15",
            key="835_weights",
        )

    if uploaded is None:
        st.info("Upload an 837 file to generate an 835E.")
        return

    from mn_encounter_toolkit.web.common import read_upload_text
    from mn_encounter_toolkit.web.response_service import generate_835e_from_text

    if st.button("Generate 835E", type="primary", key="835_generate"):
        result = generate_835e_from_text(
            read_upload_text(uploaded),
            mode=mode,
            seed=int(seed),
            outcome_weights=outcome_weights,
            payment_method=payment_method,
        )
        st.session_state["835_result"] = result
        st.session_state["835_source_name"] = uploaded.name

    result = st.session_state.get("835_result")
    if result is None:
        return
    if result.error_message:
        st.error(result.error_message)
        return

    st.success(f"Generated 835E ({result.mode} mode).")
    if result.layer1_clean:
        st.caption("Layer 1 envelope check on output: PASS")
    else:
        st.warning(f"Layer 1 envelope check on output: {result.layer1_error_count} error(s)")

    base = st.session_state.get("835_source_name", "source.x12")
    stem = base.rsplit(".", 1)[0]
    st.download_button(
        "Download 835E file",
        data=result.output_text,
        file_name=f"{stem}_835e.x12",
        mime="application/octet-stream",
        key="835_download",
    )
    with st.expander("Preview first 40 lines"):
        st.code("\n".join(result.output_text.splitlines()[:40]), language=None)


def page_scenario_lab() -> None:
    st.header("Scenario lab")
    st.caption(
        "Generate sample 837 files from built-in scenarios for demos and training. "
        "Use err_* scenarios to produce files that fail validation on purpose."
    )

    from mn_encounter_toolkit.web.generate_service import generate_batch_from_scenarios, list_scenario_options

    options = list_scenario_options()
    labels = {
        name: f"{name} — {desc}{' [ERROR]' if err else ''}"
        for name, desc, err in options
    }
    selected = st.multiselect(
        "Scenarios",
        options=[name for name, _, _ in options],
        format_func=lambda name: labels[name],
        key="lab_scenarios",
    )
    seed = st.number_input("Seed", min_value=0, value=42, step=1, key="lab_seed")
    count = st.number_input("Instances per scenario", min_value=1, value=1, step=1, key="lab_count")

    if st.button("Generate 837 batch", type="primary", key="lab_generate"):
        result = generate_batch_from_scenarios(
            selected,
            seed=int(seed),
            count_per_scenario=int(count),
        )
        st.session_state["lab_result"] = result

    result = st.session_state.get("lab_result")
    if result is None:
        return
    if result.error_message:
        st.error(result.error_message)
        return

    st.success(f"Generated {result.encounter_count} encounter(s) from {len(result.scenario_names)} scenario slot(s).")
    st.download_button(
        "Download 837 file",
        data=result.output_text,
        file_name=f"lab_seed{seed}.x12",
        mime="application/octet-stream",
        key="lab_download",
    )
    st.caption("Tip: open the **Validate 837** page and upload this file to review findings.")
