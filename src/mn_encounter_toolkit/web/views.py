"""Streamlit view functions shared across UI pages."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from mn_encounter_toolkit.web.edi_html import format_plain_edi, render_edi_html
from mn_encounter_toolkit.web.enrich import EnrichedFinding
from mn_encounter_toolkit.web.layer_reference import (
    LAYER_INFO,
    LAYER_SUMMARIES,
    VALIDATION_LAYERS_DOC,
    LayerInfo,
    find_rules,
)
from mn_encounter_toolkit.web.rule_config import load_suppressed_rule_ids, save_suppressed_rule_ids
from mn_encounter_toolkit.web.validate_service import (
    ALL_LAYER_NUMBERS,
    ValidationReport,
    detect_transactions,
    layers_for_upload,
    report_to_csv,
    report_to_json,
    validate_upload,
)


_UPLOAD_TYPES = ["x12", "txt", "edi", "dat"]


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


def _suppressed_count_label(count: int) -> str:
    noun = "rule" if count == 1 else "rules"
    return f"{count} {noun} suppressed"


def _editor_rows(edited) -> list[dict]:
    if hasattr(edited, "to_dict"):
        return edited.to_dict("records")
    return list(edited)


def _apply_layer_editor(layer: LayerInfo, suppressed: set[str], edited) -> set[str]:
    layer_ids = {rule.rule_id for rule in layer.rules}
    turned_off = {row["Rule ID"] for row in _editor_rows(edited) if not row["Enabled"]}
    return (suppressed - layer_ids) | (turned_off & layer_ids)


def page_validation_layers() -> None:
    st.header("Validation layers reference")
    st.caption(
        "What each layer checks when you validate an 837 file. "
        "Uncheck Enabled to suppress that rule on the EDI file page. "
        "This list is saved on this machine and does not include uploaded files."
    )

    suppressed = set(load_suppressed_rule_ids())
    if st.button("Enable all rules"):
        if suppressed:
            for layer in LAYER_INFO:
                st.session_state.pop(f"rule_editor_{layer.number}", None)
            save_suppressed_rule_ids(set())
            st.rerun()
    if suppressed:
        st.warning(f"{_suppressed_count_label(len(suppressed))}. The EDI file page skips these findings.")
    else:
        st.caption("All rules are enabled.")

    st.info(
        "**999 deterministic** responses use **Layers 1 and 2 only** (envelope + syntax). "
        "Layers **3 and 4** apply to full 837 validation."
    )

    overview = [
        {
            "Layer": layer.number,
            "Title": layer.title,
            "Rules": len(layer.rules),
            "Suppressed": sum(1 for rule in layer.rules if rule.rule_id in suppressed),
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
            edited = st.data_editor(
                [
                    {
                        "Enabled": rule.rule_id not in suppressed,
                        "Rule ID": rule.rule_id,
                        "Severity": _severity_label(rule.severity),
                        "What it checks": rule.description,
                        "Notes": rule.notes,
                    }
                    for rule in layer.rules
                ],
                disabled=["Rule ID", "Severity", "What it checks", "Notes"],
                hide_index=True,
                use_container_width=True,
                key=f"rule_editor_{layer.number}",
            )
            updated = _apply_layer_editor(layer, suppressed, edited)
            if updated != suppressed:
                save_suppressed_rule_ids(updated)
                st.rerun()

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


def _layer_checkbox(number: int, *, checked: bool, disabled: bool, key: str) -> bool:
    return st.checkbox(
        f"Layer {number} — {LAYER_SUMMARIES[number]['title']}",
        value=checked,
        disabled=disabled,
        key=key,
    )


def page_validate() -> None:
    st.header("EDI file")
    st.caption("Upload an 837, 835, or 999 file. Validation and the readable view follow the transaction type.")
    suppressed_rule_ids = load_suppressed_rule_ids()
    if suppressed_rule_ids:
        st.caption(
            f"{_suppressed_count_label(len(suppressed_rule_ids))}. "
            "Change this on Validation layers."
        )
    view_mode = st.radio("View", ["Annotated", "Plain text"], horizontal=True, key="edi_view_mode")

    uploaded = st.file_uploader("EDI file (.x12, .txt, .edi, .dat)", type=_UPLOAD_TYPES, key="edi_upload")
    text = uploaded.read().decode("utf-8", errors="replace") if uploaded is not None else None
    detected = detect_transactions(text) if text is not None else None
    envelope_only = detected is not None and detected.runs_envelope_only
    encounter = detected is not None and detected.runs_encounter_rules

    with st.sidebar:
        st.subheader("Validation layers")
        if view_mode == "Plain text":
            st.caption("Plain text shows one segment per line and does not run validation.")
        elif envelope_only:
            st.caption("835 and 999 use layer 1 only. Layers 2–4 apply to 837 encounters.")
        elif detected is not None and not detected.kinds:
            st.caption("Guide version was not recognized. Encounter rules are not run.")
        layer_selection: dict[int, bool] = {}
        for number in ALL_LAYER_NUMBERS:
            if envelope_only:
                layer_selection[number] = _layer_checkbox(
                    number, checked=number == 1, disabled=True, key=f"edi_layer_fixed_{number}"
                )
            elif detected is not None and not detected.kinds:
                layer_selection[number] = _layer_checkbox(
                    number, checked=False, disabled=True, key=f"edi_layer_unknown_{number}"
                )
            else:
                layer_selection[number] = _layer_checkbox(
                    number, checked=True, disabled=view_mode == "Plain text", key=f"edi_layer_{number}"
                )
        render_layer_reference_sidebar()

    if text is None or uploaded is None:
        st.info("Upload a file to validate and view it.")
        return

    if detected is not None and detected.kinds:
        st.caption(f"Detected {detected.label}.")
    else:
        st.caption("Guide version was not recognized. The file is shown without encounter validation.")

    if view_mode == "Plain text":
        st.caption("One segment per line. Indentation follows the loop hierarchy. The download is the original file.")
        st.download_button(
            "Download original file",
            data=text,
            file_name=uploaded.name,
            mime="text/plain",
            key="edi_plain_download",
        )
        try:
            plain = format_plain_edi(text)
        except (ValueError, OSError) as exc:
            st.error(str(exc))
            plain = text
        st.code(plain, language=None)
        return

    selected = tuple(number for number, enabled in layer_selection.items() if enabled)
    layer_numbers = layers_for_upload(detected, selected) if detected is not None else None
    findings = None
    if layer_numbers is None:
        st.info("Encounter validation was not run for this file.")
    else:
        if not layer_numbers:
            st.error("Select at least one validation layer.")
            return
        report = validate_upload(
            text,
            filename=uploaded.name,
            layer_numbers=layer_numbers,
            suppressed_rule_ids=suppressed_rule_ids,
        )
        if report.parse_error:
            st.error(f"Could not parse file: {report.parse_error}")
            return
        _render_validation_summary(report, uploaded.name)
        findings = [
            {
                "severity": item.finding.severity,
                "rule_id": item.finding.rule_id,
                "message": item.finding.message,
                "segment_id": item.finding.segment_id,
                "line_number": item.finding.line_number,
            }
            for item in report.findings
            if item.finding.severity in {"error", "warning"}
        ]

    try:
        page = render_edi_html(text, filename=uploaded.name, findings=findings)
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        return

    st.subheader("Annotated view")
    st.caption("Previous and Next in the view walk each error and warning marker.")
    st.download_button(
        "Download HTML",
        data=page,
        file_name=f"{uploaded.name}.html",
        mime="text/html",
        key="edi_html_download",
    )
    components.html(page, height=900, scrolling=True)


def _render_validation_summary(report: ValidationReport, uploaded_name: str) -> None:
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
    render_validation_results(report, uploaded_name)


def page_gen999() -> None:
    st.header("Generate 999")
    st.caption("Upload an 837 file to produce a 999 Implementation Acknowledgment.")

    uploaded = st.file_uploader("837 source file (.x12, .txt, .edi, .dat)", type=_UPLOAD_TYPES, key="999_upload")
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

    uploaded = st.file_uploader("837 source file (.x12, .txt, .edi, .dat)", type=_UPLOAD_TYPES, key="835_upload")
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
    st.caption("Tip: open the **EDI file** page and upload this file to review findings.")


