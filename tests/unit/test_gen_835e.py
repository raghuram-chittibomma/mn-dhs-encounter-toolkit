import random
from datetime import date
from decimal import Decimal

from mn_encounter_toolkit.edi.parser import parse_segments
from mn_encounter_toolkit.edi.writer import write_batch_checked
from mn_encounter_toolkit.generator.consistency import InconsistentEncounterError
from mn_encounter_toolkit.generator.scenarios import registry
from mn_encounter_toolkit.response.gen_835e import _allocate_line_paid, generate_835e_deterministic, generate_835e_simulated


def test_deterministic_835e_echoes_mco_paid_amount():
    encounter = registry.build_encounter("clean_professional_original", seed=1)
    text = write_batch_checked([encounter])
    out = generate_835e_deterministic(text)
    doc = parse_segments(out)
    clp = doc.first("CLP")
    assert clp.el_str(1) == encounter.encounter_id
    assert Decimal(clp.el_str(3)) == encounter.total_charge_amount
    assert Decimal(clp.el_str(4)) == encounter.mco_adjudication.paid_amount


def test_deterministic_835e_marks_void_claim_as_reversal_status_22():
    encounter = registry.build_encounter("void_encounter", seed=2)
    text = write_batch_checked([encounter])
    out = generate_835e_deterministic(text)
    doc = parse_segments(out)
    assert doc.first("CLP").el_str(2) == "22"


def test_deterministic_835e_denies_zero_paid_claim():
    encounter = registry.build_encounter("zero_paid_encounter", seed=3)
    text = write_batch_checked([encounter])
    out = generate_835e_deterministic(text)
    doc = parse_segments(out)
    assert doc.first("CLP").el_str(2) == "4"


def test_deterministic_835e_groups_claims_by_billing_tin():
    encounters = [
        registry.build_encounter("clean_professional_original", seed=10),
        registry.build_encounter("clean_professional_original", seed=11),
    ]
    text = write_batch_checked(encounters)
    out = generate_835e_deterministic(text)
    doc = parse_segments(out)
    # Two different billing providers (different TINs) -> two separate
    # ST/SE 835E transaction sets, one payee (N1*PE) loop each.
    sts = doc.find("ST")
    assert all(st.el_str(1) == "835" for st in sts)
    n1_pe = [n for n in doc.find("N1") if n.el_str(1) == "PE"]
    assert len(n1_pe) == len(sts)


def test_deterministic_835e_lines_sum_to_claim_paid_amount():
    encounter = registry.build_encounter("clean_institutional_original", seed=4)
    text = write_batch_checked([encounter])
    out = generate_835e_deterministic(text)
    doc = parse_segments(out)
    clp = doc.first("CLP")
    svcs = doc.find("SVC")
    line_paid_total = sum((Decimal(s.el_str(3)) for s in svcs), Decimal("0.00"))
    assert line_paid_total == Decimal(clp.el_str(4))


def test_simulated_835e_is_deterministic_for_same_seed():
    encounter = registry.build_encounter("clean_professional_original", seed=5)
    text = write_batch_checked([encounter])
    out1 = generate_835e_simulated(text, random.Random(55))
    out2 = generate_835e_simulated(text, random.Random(55))
    assert out1 == out2


def test_simulated_835e_can_force_full_denial():
    encounter = registry.build_encounter("clean_professional_original", seed=6)
    text = write_batch_checked([encounter])
    out = generate_835e_simulated(
        text, random.Random(1), outcome_weights={"paid_full": 0, "paid_partial": 0, "denied": 1}
    )
    doc = parse_segments(out)
    clp = doc.first("CLP")
    assert clp.el_str(2) == "4"
    assert Decimal(clp.el_str(4)) == Decimal("0.00")
    assert len(doc.find("CAS")) >= 1


def test_simulated_835e_can_force_full_payment():
    encounter = registry.build_encounter("clean_professional_original", seed=7)
    text = write_batch_checked([encounter])
    out = generate_835e_simulated(
        text, random.Random(1), outcome_weights={"paid_full": 1, "paid_partial": 0, "denied": 0}
    )
    doc = parse_segments(out)
    clp = doc.first("CLP")
    assert Decimal(clp.el_str(4)) == Decimal(clp.el_str(3))


def test_allocate_line_paid_splits_remaining_with_exact_balance():
    lines = [
        ("1", Decimal("33.33"), None, "HC:99213", "20260101"),
        ("2", Decimal("33.33"), None, "HC:99214", "20260101"),
        ("3", Decimal("33.34"), None, "HC:99215", "20260101"),
    ]
    remits = _allocate_line_paid(lines, Decimal("100.00"))
    assert sum((r.paid for r in remits), Decimal("0.00")) == Decimal("100.00")


def test_deterministic_835e_is_byte_identical_with_fixed_submission_time():
    encounter = registry.build_encounter("clean_professional_original", seed=12)
    text = write_batch_checked([encounter])
    kwargs = dict(submission_date=date(2026, 6, 30), submission_time="1530")
    out1 = generate_835e_deterministic(text, **kwargs)
    out2 = generate_835e_deterministic(text, **kwargs)
    assert out1 == out2


def test_deterministic_835e_handles_claim_with_no_explicit_line_paid_gracefully():
    """err_missing_mco_paid removes line-level REF*9D entirely -- the
    generator must fall back to proportional allocation and stay balanced."""
    encounter = registry.build_encounter("err_missing_mco_paid", seed=8)
    text = write_batch_checked([encounter], allow_inconsistent=True)
    out = generate_835e_deterministic(text)
    doc = parse_segments(out)
    clp = doc.first("CLP")
    assert clp is not None
    svcs = doc.find("SVC")
    line_paid_total = sum((Decimal(s.el_str(3)) for s in svcs), Decimal("0.00"))
    assert line_paid_total == Decimal(clp.el_str(4))
