import random

from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.web.enrich import enrich_findings
from mn_encounter_toolkit.web.validate_service import report_to_csv, validate_upload
from mn_encounter_toolkit.validator.run import validate_text


def test_enrich_maps_subscriber_hl_to_claim_id():
    rng = random.Random(42)
    good = registry.build_encounter("clean_professional_original", seed=1)
    bad = registry.build_encounter("err_missing_umpi", seed=2)
    text = write_batch_checked([good, bad], allow_inconsistent=True)
    from mn_encounter_toolkit.edi.parser import parse_segments

    doc = parse_segments(text)
    findings = validate_text(text)
    enriched = enrich_findings(doc, findings)
    assert len(enriched) == 1
    item = enriched[0]
    assert item.scope == "claim"
    assert item.subscriber_hl_id == "4"
    assert item.claim_id is not None
    assert item.claim_index == 2
    assert item.member_name is not None
    assert item.billing_loop_note is not None


def test_enrich_maps_line_number_to_claim():
    rng = random.Random(1)
    encounter = registry.build_encounter("err_charge_mismatch", seed=3)
    text = write_batch_checked([encounter], allow_inconsistent=True)
    from mn_encounter_toolkit.edi.parser import parse_segments

    doc = parse_segments(text)
    findings = [f for f in validate_text(text) if f.rule_id == "L4-CHARGE-BALANCE"]
    enriched = enrich_findings(doc, findings)
    assert enriched[0].scope == "claim"
    assert enriched[0].claim_id is not None
    assert enriched[0].segment_snippet is not None
    assert enriched[0].finding.line_number is not None


def test_validate_upload_reports_parse_errors():
    report = validate_upload("not an edi file", filename="bad.x12")
    assert report.parse_error is not None
    assert report.exit_code == 2
    assert report.claims == ()


def test_report_to_csv_includes_claim_columns():
    rng = random.Random(5)
    encounter = registry.build_encounter("err_missing_umpi", seed=4)
    text = write_batch_checked([encounter], allow_inconsistent=True)
    report = validate_upload(text, filename="err.x12")
    csv_text = report_to_csv(report)
    assert "L3-BILLING-UMPI-REQUIRED" in csv_text
    assert "claim" in csv_text.lower()
