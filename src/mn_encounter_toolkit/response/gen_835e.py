"""835E (encounter remittance-advice variant) generator.

# KNOWN LIMITATION / INTERPRETATION NOTE -- read before trusting this module
# for anything beyond synthetic-fixture generation:
#
# mucg_835.pdf is the AUC Minnesota Uniform Companion Guide for the base
# X12/005010X221A1 Health Care Claim Payment/Advice (835) transaction. Per
# dhs_encounter_data_landing_rendered.md (captured during document
# acquisition), the DHS encounter-data landing page explicitly states the
# AUC MUCGs do not govern MCO encounter submissions or their responses --
# there is no retrieved, DHS-confirmed "835E" structural specification.
# This generator is therefore an *adaptation* of the base 835 mechanics
# (Section 2.4 transaction table, p.10-12) and Appendix C's worked
# CLP/SVC/CAS/AMT examples (p.19-25) to the encounter domain, built on this
# project's own assumption of roles:
#   - Sender (ISA06/GS02) = DHS (the 837 *receiver* of the original
#     encounter), since DHS is the party producing this acknowledgment-style
#     remittance back to the submitting MCO.
#   - Receiver (ISA08/GS03) = the originating MCO's trading partner id.
#   - Loop 1000A "Payer" = DHS; Loop 1000B "Payee" = the encounter's billing
#     provider (per mucg_835.pdf Sec 2.1.2.3: "the 835 payee corresponds to
#     the 837 billing provider").
#   - CLP02/CLP04 values mirror -- rather than recompute -- the MCO-reported
#     adjudication already present in the source 837 (AMT*D/AMT*EAF in Loop
#     2320), since DHS's encounter "remittance" is an acknowledgment of
#     amounts the MCO already paid, not a new adjudication/payment.
# See KNOWN_LIMITATIONS.md for the full caveat. CARC/RARC code values used
# below come from response/carc_rarc.py, which has its own sourcing caveat
# (mucg_835.pdf Appendix A delegates the actual code list to external
# bodies; see that module's docstring).
#
# Two modes, mirroring gen_999.py:
#   - Deterministic: parses the original 837 text and echoes back exactly
#     the charge/paid/patient-liability amounts already present in it
#     (Loop 2320 AMT*D/AMT*EAF, line REF*9D/9C or REF*9C/9A), computing a
#     CO-45 contractual write-off for any charge-paid-liability gap.
#   - Simulation: ignores the original amounts and draws a randomized
#     adjudication outcome (paid in full / contractual reduction / denied)
#     per claim from a seeded rng, using response/carc_rarc.py's pool.
"""

from __future__ import annotations

import datetime as _dt
import random
from dataclasses import dataclass, field
from decimal import Decimal

from mn_encounter_toolkit.edi.parser import ClaimBlock, ParsedDocument, parse_segments
from mn_encounter_toolkit.edi.x12_core import DEFAULT_SEPARATORS, Separators, build_segment
from mn_encounter_toolkit.models.core import DHS_PAYER_ID, DHS_PAYER_NAME, DHS_RECEIVER_FEIN_HYPHENATED
from mn_encounter_toolkit.response.carc_rarc import CarcRarcPair, pick_denial_reason


def _money(text: str) -> Decimal:
    text = (text or "").strip()
    if not text:
        return Decimal("0.00")
    try:
        return Decimal(text)
    except Exception:
        return Decimal("0.00")


@dataclass(frozen=True)
class LineRemit:
    line_number: str
    charge: Decimal
    paid: Decimal
    code_value: str  # procedure code (837P SV1) or revenue code (837I SV2)
    service_date: str
    adjustment: CarcRarcPair | None


@dataclass(frozen=True)
class ClaimRemit:
    icn: str
    total_charge: Decimal
    total_paid: Decimal
    patient_responsibility: Decimal
    status_code: str  # CLP02
    member_id: str
    member_last: str
    member_first: str
    lines: list[LineRemit] = field(default_factory=list)
    claim_adjustment: CarcRarcPair | None = None


@dataclass(frozen=True)
class PayeeRemit:
    tin: str
    payee_name: str
    claims: list[ClaimRemit]

    @property
    def total_paid(self) -> Decimal:
        return sum((c.total_paid for c in self.claims), Decimal("0.00"))


def _billing_tin_and_name(block: ClaimBlock) -> tuple[str, str]:
    ref_ei = next((s for s in block.billing_segments if s.seg_id == "REF" and s.el_str(1) == "EI"), None)
    tin = ref_ei.el_str(2) if ref_ei else "UNKNOWN"
    nm1_85 = next((s for s in block.billing_segments if s.seg_id == "NM1" and s.el_str(1) == "85"), None)
    name = nm1_85.el_str(3) if nm1_85 else "UNKNOWN PROVIDER"
    return tin, name


def _claim_frequency_code(block: ClaimBlock) -> str:
    clm = block.clm()
    if clm is None:
        return "1"
    clm05 = clm.composite(5)
    return clm05[2] if len(clm05) >= 3 else "1"


def _header_amounts(block: ClaimBlock) -> tuple[Decimal, Decimal]:
    """First Loop-2320 occurrence (the MCO's own adjudication, always
    written before any LX line loop -- see edi/writer.py
    write_mco_adjudication_loop / write_encounter_claim) -- AMT*D (paid)
    and AMT*EAF (remaining patient liability)."""
    first_lx = next((i for i, s in enumerate(block.claim_segments) if s.seg_id == "LX"), len(block.claim_segments))
    header = block.claim_segments[:first_lx]
    amt_d = next((s for s in header if s.seg_id == "AMT" and s.el_str(1) == "D"), None)
    amt_eaf = next((s for s in header if s.seg_id == "AMT" and s.el_str(1) == "EAF"), None)
    paid = _money(amt_d.el_str(2)) if amt_d else Decimal("0.00")
    liability = _money(amt_eaf.el_str(2)) if amt_eaf else Decimal("0.00")
    return paid, liability


def _line_groups(block: ClaimBlock) -> list[list]:
    groups: list[list] = []
    current: list = []
    for seg in block.claim_segments:
        if seg.seg_id == "LX":
            if current:
                groups.append(current)
            current = [seg]
        elif current:
            current.append(seg)
    if current:
        groups.append(current)
    return groups


def _extract_lines(block: ClaimBlock) -> list[tuple[str, Decimal, Decimal, str, str]]:
    """Returns (line_number, charge, paid, code_value, service_date) per
    service line, reading SV1 (837P) or SV2 (837I), REF*9D/9C (line paid),
    and DTP*472 (service date)."""
    out = []
    for group in _line_groups(block):
        lx = group[0]
        line_number = lx.el_str(1)
        sv1 = next((s for s in group if s.seg_id == "SV1"), None)
        sv2 = next((s for s in group if s.seg_id == "SV2"), None)
        if sv1 is not None:
            charge = _money(sv1.el_str(2))
            code = sv1.composite(1)[1] if len(sv1.composite(1)) >= 2 else ""
        elif sv2 is not None:
            charge = _money(sv2.el_str(3))
            code = sv2.el_str(1)
        else:
            charge = Decimal("0.00")
            code = ""
        ref_paid = next((s for s in group if s.seg_id == "REF" and s.el_str(1) in ("9D", "9C")), None)
        paid = _money(ref_paid.el_str(2)) if ref_paid else None
        dtp = next((s for s in group if s.seg_id == "DTP" and s.el_str(1) == "472"), None)
        service_date = dtp.el_str(3) if dtp else ""
        out.append((line_number, charge, paid, code, service_date))
    return out


def _allocate_line_paid(lines: list[tuple[str, Decimal, Decimal | None, str, str]], claim_paid: Decimal) -> list[LineRemit]:
    total_charge = sum((c for _, c, _, _, _ in lines), Decimal("0.00"))
    explicit_total = sum((p for _, _, p, _, _ in lines if p is not None), Decimal("0.00"))
    missing = [i for i, (_, _, p, _, _) in enumerate(lines) if p is None]
    remaining = claim_paid - explicit_total
    out: list[LineRemit] = []
    for i, (num, charge, paid, code, date) in enumerate(lines):
        if paid is not None:
            line_paid = paid
        elif missing and total_charge > 0:
            # Proportional fallback when the line didn't carry an explicit
            # REF*9D/9C paid amount -- distributes whatever's left of the
            # claim-level paid amount by charge share.
            share = (charge / total_charge) if total_charge else Decimal("0.00")
            line_paid = (remaining * share).quantize(Decimal("0.01"))
        else:
            line_paid = Decimal("0.00")
        adjustment = None
        if charge > line_paid:
            adjustment = CarcRarcPair("CO", "45", "Charge exceeds fee schedule/contracted fee arrangement.", None, None, 1)
        out.append(LineRemit(line_number=num, charge=charge, paid=line_paid, code_value=code, service_date=date, adjustment=adjustment))
    return out


def build_deterministic_remits(original_text: str) -> tuple[ParsedDocument, list[PayeeRemit]]:
    doc = parse_segments(original_text)
    by_tin: dict[str, PayeeRemit] = {}
    for block in doc.claim_blocks():
        clm = block.clm()
        if clm is None:
            continue
        icn = clm.el_str(1)
        total_charge = _money(clm.el_str(2))
        paid, liability = _header_amounts(block)
        freq = _claim_frequency_code(block)
        status = "22" if freq == "8" else ("1" if paid > 0 else "4")
        writeoff = total_charge - paid - liability
        claim_adj = CarcRarcPair("CO", "45", "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement.", None, None, 1) if writeoff > 0 else None
        if status == "4" and claim_adj is None and total_charge > 0:
            claim_adj = CarcRarcPair("CO", "96", "Non-covered charge(s).", "N130", "Consult plan benefit documents/guidelines for information about restrictions for this service.", 1)

        # NM1*IL*1*<last>*<first>****MI*<medicaid_id> -- el(3)=last,
        # el(4)=first, el(9)=id value (el(8) is the "MI" qualifier itself).
        nm1_il = next((s for s in block.claim_segments if s.seg_id == "NM1" and s.el_str(1) == "IL"), None)
        member_id = nm1_il.el_str(9) if nm1_il else ""
        member_last = nm1_il.el_str(3) if nm1_il else ""
        member_first = nm1_il.el_str(4) if nm1_il else ""

        raw_lines = _extract_lines(block)
        lines = _allocate_line_paid(raw_lines, paid)

        remit = ClaimRemit(
            icn=icn,
            total_charge=total_charge,
            total_paid=paid,
            patient_responsibility=liability,
            status_code=status,
            member_id=member_id,
            member_last=member_last,
            member_first=member_first,
            lines=lines,
            claim_adjustment=claim_adj,
        )
        tin, name = _billing_tin_and_name(block)
        if tin not in by_tin:
            by_tin[tin] = PayeeRemit(tin=tin, payee_name=name, claims=[])
        by_tin[tin].claims.append(remit)
    return doc, list(by_tin.values())


_OUTCOME_WEIGHTS = {"paid_full": 55, "paid_partial": 30, "denied": 15}


def build_simulated_remits(
    original_text: str, rng: random.Random, *, outcome_weights: dict[str, int] | None = None
) -> tuple[ParsedDocument, list[PayeeRemit]]:
    doc = parse_segments(original_text)
    weights = outcome_weights or _OUTCOME_WEIGHTS
    outcomes = list(weights.keys())
    weight_values = list(weights.values())

    by_tin: dict[str, PayeeRemit] = {}
    for block in doc.claim_blocks():
        clm = block.clm()
        if clm is None:
            continue
        icn = clm.el_str(1)
        total_charge = _money(clm.el_str(2))
        freq = _claim_frequency_code(block)
        raw_lines = _extract_lines(block)
        line_charges = [c for _, c, _, _, _ in raw_lines] or [total_charge]

        outcome = rng.choices(outcomes, weights=weight_values, k=1)[0]
        claim_adj = None
        if freq == "8":
            status, paid, liability = "22", Decimal("0.00"), Decimal("0.00")
        elif outcome == "paid_full":
            status, paid, liability = "1", total_charge, Decimal("0.00")
        elif outcome == "paid_partial":
            pct = Decimal(rng.randint(40, 95)) / Decimal(100)
            paid = (total_charge * pct).quantize(Decimal("0.01"))
            liability = Decimal("0.00")
            claim_adj = pick_denial_reason(rng) if total_charge > paid else None
            if claim_adj is None:
                claim_adj = CarcRarcPair("CO", "45", "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement.", None, None, 1)
            status = "1"
        else:
            status, paid, liability = "4", Decimal("0.00"), Decimal("0.00")
            claim_adj = pick_denial_reason(rng)

        nm1_il = next((s for s in block.claim_segments if s.seg_id == "NM1" and s.el_str(1) == "IL"), None)
        member_id = nm1_il.el_str(9) if nm1_il else ""
        member_last = nm1_il.el_str(3) if nm1_il else ""
        member_first = nm1_il.el_str(4) if nm1_il else ""

        total_line_charge = sum(line_charges, Decimal("0.00"))
        lines: list[LineRemit] = []
        for (num, charge, _orig_paid, code, date) in raw_lines:
            share = (charge / total_line_charge) if total_line_charge else Decimal("0.00")
            line_paid = (paid * share).quantize(Decimal("0.01"))
            line_adj = claim_adj if charge > line_paid else None
            lines.append(LineRemit(line_number=num, charge=charge, paid=line_paid, code_value=code, service_date=date, adjustment=line_adj))

        remit = ClaimRemit(
            icn=icn,
            total_charge=total_charge,
            total_paid=paid,
            patient_responsibility=liability,
            status_code=status,
            member_id=member_id,
            member_last=member_last,
            member_first=member_first,
            lines=lines,
            claim_adjustment=claim_adj,
        )
        tin, name = _billing_tin_and_name(block)
        if tin not in by_tin:
            by_tin[tin] = PayeeRemit(tin=tin, payee_name=name, claims=[])
        by_tin[tin].claims.append(remit)
    return doc, list(by_tin.values())


def _fmt_money(amount: Decimal) -> str:
    return f"{amount:.2f}"


def render_835e(
    original_doc: ParsedDocument,
    payee_remits: list[PayeeRemit],
    *,
    separators: Separators = DEFAULT_SEPARATORS,
    isa_control_number: int = 1,
    receiver_trading_partner_id: str | None = None,
    submission_date: _dt.date | None = None,
    payment_method: str = "NON",
) -> str:
    """Render the 835E text. One GS/ST per payee TIN found in the source
    837 (see module docstring re: 1000B payee = 837 billing provider)."""
    submission_date = submission_date or _dt.date.today()
    original_isa = original_doc.first("ISA")
    receiver_id = receiver_trading_partner_id or (original_isa.el_str(6).strip() if original_isa else "")

    segments: list[str] = []

    def add(*elements):
        segments.append(build_segment(separators, *elements))

    isa_cn = f"{isa_control_number:09d}"
    # SOURCE: mucg_835.pdf Sec 2.4 table (BPR04 payment method: ACH, CHK,
    # FWT, NON) -- ISA mapping otherwise follows the same conventions as
    # edi/writer.py write_batch (DHS-issued, MN repetition separator '[').
    add(
        "ISA", "00", " " * 10, "00", " " * 10, "ZZ", DHS_RECEIVER_FEIN_HYPHENATED.ljust(15), "ZZ",
        receiver_id.ljust(15), submission_date.strftime("%y%m%d"), _dt.datetime.now().strftime("%H%M"),
        separators.repetition_separator, "00501", isa_cn, "0", "T", separators.sub_element_separator,
    )

    gs_cn = 1
    st_cn = 1
    for payee in payee_remits:
        add(
            "GS", "HP", DHS_RECEIVER_FEIN_HYPHENATED, receiver_id, submission_date.strftime("%Y%m%d"),
            _dt.datetime.now().strftime("%H%M"), str(gs_cn), "X", "005010X221A1",
        )
        st_start = len(segments)
        add("ST", "835", str(st_cn), "005010X221A1")
        total_paid = payee.total_paid
        # SOURCE: mucg_835.pdf Sec 2.4 (BPR04 payment method code in {ACH,
        # CHK, FWT, NON}) -- BPR01="H" (Notification Only) and BPR04="NON"
        # (no payment data) reflect that this 835E acknowledges MCO-reported
        # amounts rather than issuing a new DHS payment -- see module
        # docstring's interpretation note. BPR16 is the only other element
        # this toolkit populates (production date); BPR05-15 (banking
        # routing/account details) are not applicable to a non-payment
        # notification and are left empty.
        bpr_elements = ["H", _fmt_money(total_paid), "C", payment_method] + [""] * 11 + [submission_date.strftime("%Y%m%d")]
        add("BPR", *bpr_elements)
        add("TRN", "1", f"{isa_cn}{gs_cn:04d}", DHS_RECEIVER_FEIN_HYPHENATED)
        add("REF", "EV", DHS_PAYER_ID)
        add("DTM", "405", submission_date.strftime("%Y%m%d"))
        add("N1", "PR", DHS_PAYER_NAME, "PI", DHS_PAYER_ID)
        add("N3", "540 CEDAR ST")
        add("N4", "ST PAUL", "MN", "551640001")
        # SOURCE: mucg_835.pdf Sec 2.1.2.3 ("the 835 payee corresponds to
        # the 837 billing provider") -- Loop 1000B.
        add("N1", "PE", payee.payee_name, "XX", payee.tin)
        add("N3", "ADDRESS ON FILE")
        add("N4", "ST PAUL", "MN", "551010000")

        for remit in payee.claims:
            # SOURCE: mucg_835.pdf Appendix C worked examples (p.19-25) --
            # CLP*<ICN>*<status>*<charge>*<paid>*<patient resp>*<filing
            # indicator>*<payer claim control #>*<freq>.
            add(
                "CLP", remit.icn, remit.status_code, _fmt_money(remit.total_charge), _fmt_money(remit.total_paid),
                _fmt_money(remit.patient_responsibility), "MC", remit.icn, "1",
            )
            add("NM1", "QC", "1", remit.member_last, remit.member_first, "", "", "", "MI", remit.member_id)
            if remit.claim_adjustment is not None:
                adj = remit.claim_adjustment
                claim_level_amount = remit.total_charge - remit.total_paid - remit.patient_responsibility
                if claim_level_amount > 0:
                    add("CAS", adj.group_code, adj.carc, _fmt_money(claim_level_amount))
            if remit.patient_responsibility > 0:
                add("CAS", "PR", "1", _fmt_money(remit.patient_responsibility))
            for line in remit.lines:
                add("SVC", ("HC", line.code_value), _fmt_money(line.charge), _fmt_money(line.paid))
                if line.service_date:
                    add("DTM", "472", line.service_date)
                if line.adjustment is not None and line.charge > line.paid:
                    add("CAS", line.adjustment.group_code, line.adjustment.carc, _fmt_money(line.charge - line.paid))

        se_count = len(segments) - st_start + 1
        add("SE", str(se_count), str(st_cn))
        add("GE", "1", str(gs_cn))
        gs_cn += 1
        st_cn += 1

    add("IEA", str(len(payee_remits)), isa_cn)
    return "\n".join(segments) + "\n"


def generate_835e_deterministic(original_text: str, **render_kwargs) -> str:
    doc, payees = build_deterministic_remits(original_text)
    return render_835e(doc, payees, **render_kwargs)


def generate_835e_simulated(
    original_text: str, rng: random.Random, *, outcome_weights: dict[str, int] | None = None, **render_kwargs
) -> str:
    doc, payees = build_simulated_remits(original_text, rng, outcome_weights=outcome_weights)
    return render_835e(doc, payees, **render_kwargs)
