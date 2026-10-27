#!/usr/bin/env python3
"""Render an X12 837, 835, or 999 file as a self-contained HTML page.

Stdlib only. Delimiters are read from the ISA segment. Loop names and
hints are a reading aid for the segments these transactions usually
carry, not a full implementation-guide data dictionary.

    python scripts/render_edi_html.py --in claim.x12 --out claim.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Separators:
    segment_terminator: str
    element_separator: str
    sub_element_separator: str
    repetition_separator: str


@dataclass
class ParsedSegment:
    seg_id: str
    elements: list[tuple[str, str]]
    raw: str
    line_number: int

    def value(self, position: str) -> str:
        for pos, value in self.elements:
            if pos == position:
                return value
        return ""

    @property
    def qualifier(self) -> str:
        if not self.elements:
            return ""
        return self.elements[0][1]


@dataclass
class ShownSegment:
    segment: ParsedSegment
    hint: str
    loop_id: str
    loop_title: str
    loop_hint: str
    markers: list[dict] = field(default_factory=list)


@dataclass
class LoopBlock:
    loop_id: str
    title: str
    hint: str
    segments: list[ShownSegment] = field(default_factory=list)
    markers: list[dict] = field(default_factory=list)


@dataclass
class TransactionView:
    label: str
    guide: str
    note: str
    blocks: list[LoopBlock] = field(default_factory=list)
    markers: list[dict] = field(default_factory=list)


@dataclass
class GroupView:
    label: str
    kind: str = ""
    header: list[ShownSegment] = field(default_factory=list)
    transactions: list[TransactionView] = field(default_factory=list)
    trailer: list[ShownSegment] = field(default_factory=list)


# Segment id -> one-line meaning. Qualified entries override this.
SEGMENT_HINTS: dict[str, str] = {
    "ISA": "Interchange control header. Names the sender, receiver, date, and the delimiters used in this file.",
    "IEA": "Interchange trailer. Closes the ISA and reports how many functional groups were inside it.",
    "GS": "Functional group header. Groups transaction sets of one implementation guide version.",
    "GE": "Functional group trailer. Closes the GS and reports how many transaction sets were inside it.",
    "ST": "Transaction set header. Starts one 837, 835, or 999.",
    "SE": "Transaction set trailer. Closes the ST and reports the segment count.",
    "BHT": "Beginning of hierarchical transaction. States the purpose and creation time of this transaction set.",
    "HL": "Hierarchical level. Connects billing provider and subscriber (or patient) levels.",
    "PRV": "Provider specialty information.",
    "NM1": "Individual or organization name, plus an identifier such as an NPI or member id.",
    "N3": "Street address for the party named just above.",
    "N4": "City, state, and ZIP for the party named just above.",
    "PER": "Contact information (name, phone, email) for the party named just above.",
    "REF": "Reference identifier. The qualifier in the first element says what the number means.",
    "SBR": "Subscriber information: payer responsibility, relationship, and claim filing indicator.",
    "DMG": "Subscriber demographics: date of birth and gender.",
    "CLM": "Claim header. Claim id, total charge, place of service, and frequency (original, replacement, or void).",
    "DTP": "Date or date range. The qualifier says which date (service, statement, admission, and so on).",
    "CL1": "Institutional claim codes: admission type, source, and patient status (837I).",
    "NTE": "Note. On 837I encounters, NTE*UPI carries the patient account number.",
    "HI": "Diagnosis or other health-care code. ABK is the principal ICD-10 diagnosis; ABF is an additional diagnosis.",
    "CRC": "Condition indicator, including EPSDT / Teen Checkup referral answers.",
    "LX": "Service line number. Starts one service line under the claim.",
    "SV1": "Professional service line: procedure, charge, units, and diagnosis pointers (837P).",
    "SV2": "Institutional service line: revenue code, charge, and units (837I).",
    "AMT": "Monetary amount. The qualifier says which amount (paid, remaining liability, tax, and so on).",
    "BPR": "Financial information for an 835: payment amount, credit/debit, and payment method.",
    "TRN": "Trace number that identifies this remittance.",
    "DTM": "Date. On an 835, qualifier 405 is the production date and 472 is the service date.",
    "N1": "Party name on an 835. PR is the payer; PE is the payee.",
    "CLP": "Claim payment. Charge, paid amount, patient responsibility, and claim status.",
    "SVC": "Service payment line under a claim on an 835.",
    "CAS": "Claim or line adjustment. Group code, reason code, and amount.",
    "AK1": "Functional group response header. Points back to the GS being acknowledged.",
    "AK2": "Transaction set response header. Points back to one ST in the submitted file.",
    "AK3": "Segment error inside the acknowledged transaction set.",
    "IK3": "Implementation segment error (same role as AK3 on a 999).",
    "AK4": "Element error inside the segment named by the preceding AK3/IK3.",
    "IK4": "Implementation element error (same role as AK4 on a 999).",
    "AK5": "Transaction set response trailer. Accept, accept with errors, or reject for that ST.",
    "AK9": "Functional group response trailer. Counts accepted and rejected transaction sets.",
}

QUALIFIED_HINTS: dict[tuple[str, str], str] = {
    ("NM1", "41"): "Submitter name. On an encounter file this is the MCO, not the rendering provider.",
    ("NM1", "40"): "Receiver name. For Minnesota encounters this is Minnesota DHS.",
    ("NM1", "85"): "Billing provider name. NM109 is usually the NPI (qualifier XX).",
    ("NM1", "IL"): "Subscriber (member) name. NM109 with qualifier MI is the member id.",
    ("NM1", "PR"): "Payer name for this claim.",
    ("NM1", "82"): "Rendering provider. The person or organization that performed the service.",
    ("NM1", "DN"): "Referring provider.",
    ("NM1", "77"): "Service facility. Where the service was performed, when it is not the billing address.",
    ("NM1", "71"): "Attending provider on an institutional claim.",
    ("NM1", "QC"): "Patient on an 835 remittance.",
    ("N1", "PR"): "Payer on the 835 (Loop 1000A).",
    ("N1", "PE"): "Payee on the 835 (Loop 1000B). Corresponds to the billing provider on the 837.",
    ("REF", "EI"): "Employer identification number (TIN) for the billing provider.",
    ("REF", "G2"): "Secondary provider identifier. On Minnesota encounters this is the DHS UMPI.",
    ("REF", "F8"): "Original claim reference (ICN) used on a void or replacement.",
    ("REF", "9A"): "Claim-level allowed amount on an 837I.",
    ("REF", "9B"): "Line-level allowed amount on an 837I.",
    ("REF", "9C"): "Claim-level paid amount on an 837I.",
    ("REF", "9D"): "Line-level paid amount. On 837P this is the MCO-paid amount for the line.",
    ("REF", "Y4"): "Additional claim reference carried in this file.",
    ("REF", "EV"): "Receiver identification on an 835.",
    ("AMT", "D"): "Payer paid amount (what the MCO paid the provider).",
    ("AMT", "EAF"): "Remaining patient liability.",
    ("AMT", "A8"): "Non-covered charges.",
    ("AMT", "T"): "Tax amount.",
    ("DTP", "434"): "Statement from-through dates for an institutional claim.",
    ("DTP", "435"): "Admission date (and time, when the format is DT).",
    ("DTP", "096"): "Discharge time.",
    ("DTP", "472"): "Service date.",
    ("DTM", "405"): "835 production date.",
    ("DTM", "472"): "Service date on an 835 line.",
    ("NTE", "UPI"): "Patient account note. Encounter 837I files send the account number here.",
    ("HL", "20"): "Billing provider hierarchical level.",
    ("HL", "22"): "Subscriber hierarchical level.",
}

ELEMENT_HINTS: dict[tuple[str, str], str] = {
    ("ISA", "06"): "Interchange sender id (MCO trading partner id on an encounter file).",
    ("ISA", "08"): "Interchange receiver id.",
    ("ISA", "13"): "Interchange control number. Must match IEA02.",
    ("ISA", "15"): "Usage indicator. T = test, P = production.",
    ("GS", "02"): "Application sender. Must match ISA06 without trailing spaces.",
    ("GS", "03"): "Application receiver.",
    ("GS", "06"): "Group control number. Must match GE02.",
    ("GS", "08"): "Implementation guide version (837P, 837I, 835, or 999).",
    ("ST", "01"): "Transaction set id: 837, 835, or 999.",
    ("ST", "02"): "Transaction set control number. Must match SE02.",
    ("ST", "03"): "Implementation convention reference.",
    ("SE", "01"): "Segment count from ST through SE, inclusive.",
    ("BHT", "02"): "Transaction set purpose. 00 = original.",
    ("BHT", "06"): "Transaction type. RP = reporting.",
    ("HL", "01"): "Hierarchical id of this level.",
    ("HL", "02"): "Parent hierarchical id.",
    ("HL", "03"): "Level code. 20 = billing provider, 22 = subscriber.",
    ("NM1", "01"): "Entity identifier (who this name is).",
    ("NM1", "02"): "Entity type. 1 = person, 2 = organization.",
    ("NM1", "03"): "Last name or organization name.",
    ("NM1", "04"): "First name, when the entity is a person.",
    ("NM1", "08"): "Identification qualifier (XX = NPI, MI = member id, PI = payer id, 46 = trading partner id).",
    ("NM1", "09"): "Identification code (NPI, member id, payer id, or trading partner id).",
    ("N1", "01"): "Entity identifier. PR = payer, PE = payee.",
    ("N1", "02"): "Name.",
    ("N1", "03"): "Identification qualifier.",
    ("N1", "04"): "Identification code.",
    ("SBR", "01"): "Payer responsibility. P = primary, S = secondary, U = unknown.",
    ("SBR", "02"): "Individual relationship code. 18 = self.",
    ("SBR", "09"): "Claim filing indicator. MC = Medicaid.",
    ("DMG", "02"): "Date of birth (CCYYMMDD when the qualifier is D8).",
    ("DMG", "03"): "Gender. M, F, or U.",
    ("CLM", "01"): "Patient account or claim id.",
    ("CLM", "02"): "Total claim charge amount.",
    ("CLM", "05-1"): "Facility type or place of service.",
    ("CLM", "05-2"): "Facility code qualifier. A or B.",
    ("CLM", "05-3"): "Claim frequency. 1 = original, 7 = replacement, 8 = void.",
    ("DTP", "01"): "Date qualifier.",
    ("DTP", "02"): "Date format. D8 = CCYYMMDD, RD8 = range, DT = date and time, TM = time.",
    ("DTP", "03"): "Date value.",
    ("DTM", "01"): "Date qualifier.",
    ("DTM", "02"): "Date value.",
    ("REF", "01"): "Reference qualifier.",
    ("REF", "02"): "Reference value.",
    ("AMT", "01"): "Amount qualifier.",
    ("AMT", "02"): "Monetary amount.",
    ("HI", "01-1"): "Diagnosis qualifier. ABK = principal ICD-10, ABF = other ICD-10.",
    ("HI", "01-2"): "Diagnosis code, without a decimal point.",
    ("SV1", "01-1"): "Product qualifier. HC = HCPCS / CPT.",
    ("SV1", "01-2"): "Procedure code.",
    ("SV1", "02"): "Line charge amount.",
    ("SV1", "03"): "Unit of measure. UN = units.",
    ("SV1", "04"): "Service unit count.",
    ("SV1", "07"): "Diagnosis pointer (which HI codes this line supports).",
    ("SV2", "01"): "Revenue code.",
    ("SV2", "03"): "Line charge amount.",
    ("SV2", "04"): "Unit of measure.",
    ("SV2", "05"): "Service unit count.",
    ("LX", "01"): "Line number.",
    ("CL1", "01"): "Admission type.",
    ("CL1", "02"): "Admission source.",
    ("CL1", "03"): "Patient status.",
    ("NTE", "01"): "Note qualifier.",
    ("NTE", "02"): "Note text.",
    ("BPR", "01"): "Transaction handling code. H = notification only.",
    ("BPR", "02"): "Total payment amount for this 835.",
    ("BPR", "03"): "Credit or debit. C = credit.",
    ("BPR", "04"): "Payment method. NON = no payment, ACH, CHK, or FWT.",
    ("BPR", "16"): "Payment or production date.",
    ("TRN", "01"): "Trace type. 1 = current transaction.",
    ("TRN", "02"): "Trace number.",
    ("CLP", "01"): "Patient control number (the claim id from the 837).",
    ("CLP", "02"): "Claim status. 1 = processed as primary, 4 = denied, 22 = reversal.",
    ("CLP", "03"): "Submitted charge.",
    ("CLP", "04"): "Paid amount.",
    ("CLP", "05"): "Patient responsibility.",
    ("CLP", "06"): "Claim filing indicator.",
    ("CLP", "07"): "Payer claim control number.",
    ("SVC", "01-1"): "Product qualifier.",
    ("SVC", "01-2"): "Procedure or revenue code.",
    ("SVC", "02"): "Submitted line charge.",
    ("SVC", "03"): "Paid line amount.",
    ("CAS", "01"): "Adjustment group. CO = contractual, PR = patient responsibility.",
    ("CAS", "02"): "Adjustment reason code (CARC).",
    ("CAS", "03"): "Adjustment amount.",
    ("AK1", "01"): "Functional identifier from the submitted GS01.",
    ("AK1", "02"): "Group control number from the submitted GS06.",
    ("AK2", "01"): "Transaction set id being acknowledged.",
    ("AK2", "02"): "Transaction set control number from the submitted ST02.",
    ("AK3", "01"): "Segment id that was in error.",
    ("AK3", "04"): "Segment syntax error code.",
    ("IK3", "01"): "Segment id that was in error.",
    ("IK3", "04"): "Segment syntax error code.",
    ("AK5", "01"): "Transaction acknowledgment. A = accepted, E = accepted with errors, R = rejected.",
    ("AK9", "01"): "Functional group acknowledgment. A, E, P (partial), or R.",
    ("AK9", "02"): "Number of transaction sets included.",
    ("AK9", "03"): "Number of transaction sets received.",
    ("AK9", "04"): "Number of transaction sets accepted.",
}

LOOP_HINTS: dict[str, str] = {
    "Envelope": "Interchange and functional-group wrappers. They identify who sent the file and which guide version is inside.",
    "Header": "Transaction header. Identifies this ST and why it was created.",
    "Trailer": "Transaction trailer. The segment count must include every segment from ST through SE.",
    "1000A": "Submitter. On an encounter file this is the MCO.",
    "1000B": "Receiver. Minnesota DHS for encounter submissions.",
    "2000A": "Billing provider hierarchical level.",
    "2010AA": "Billing provider name, address, TIN, and UMPI.",
    "2000B": "Subscriber hierarchical level and responsibility.",
    "2010BA": "Subscriber (member) name and demographics.",
    "2010BB": "Payer name for this claim.",
    "2300": "Claim information: charges, dates, diagnoses, and claim notes.",
    "2310": "Claim-level provider (referring, rendering, attending, or service facility).",
    "2320": "Other subscriber / COB. Includes the MCO paid amount on encounter claims.",
    "2330A": "Other subscriber name inside the COB loop.",
    "2330B": "Other payer name inside the COB loop.",
    "2400": "One service line: procedure or revenue code, charge, and line-level amounts.",
    "835-Header": "835 payment header: amount, method, and trace number.",
    "835-1000A": "Payer identification on the remittance.",
    "835-1000B": "Payee identification. This is the billing provider from the 837.",
    "835-2000": "Header number for a group of claims, when LX is present.",
    "835-2100": "One claim payment: status, charge, paid amount, and adjustments.",
    "835-2110": "One service line payment under the claim.",
    "999-Header": "999 transaction header.",
    "999-AK1": "Which functional group this 999 is answering.",
    "999-AK2": "Which transaction set inside that group is being answered.",
    "999-AK3": "A segment that failed syntax checks.",
    "999-AK4": "A data element inside that segment that failed.",
    "999-AK5": "Accept or reject result for the transaction set.",
    "999-AK9": "Accept or reject result for the whole functional group.",
    "Body": "Segments in an unrecognized transaction. Loop names are not assigned.",
}

GUIDE_LABELS = {
    "005010X222A1": ("837P", "837P professional encounter (005010X222A1)"),
    "005010X223A2": ("837I", "837I institutional encounter (005010X223A2)"),
    "005010X221A1": ("835", "835 health care claim payment (005010X221A1)"),
    "005010X231": ("999", "999 implementation acknowledgment (005010X231)"),
    "005010X231A1": ("999", "999 implementation acknowledgment (005010X231A1)"),
}


def detect_separators(text: str) -> Separators:
    if not text.startswith("ISA"):
        raise ValueError("Cannot detect separators: input does not start with an ISA segment.")
    element_sep = text[3]
    fields = text.split(element_sep)
    if len(fields) < 17:
        raise ValueError(
            f"Malformed ISA segment: expected at least 16 elements after ISA, got {len(fields) - 1}."
        )
    repetition_sep = fields[11][:1]
    tail = fields[16]
    if len(tail) < 2:
        raise ValueError("Malformed ISA segment: ISA16 must contain the component separator and segment terminator.")
    return Separators(
        segment_terminator=tail[1],
        element_separator=element_sep,
        sub_element_separator=tail[0],
        repetition_separator=repetition_sep,
    )


def parse_segments(text: str, separators: Separators) -> list[ParsedSegment]:
    segments: list[ParsedSegment] = []
    current_line = 1
    buf: list[str] = []
    i = 0
    n = len(text)
    term = separators.segment_terminator
    while i < n:
        ch = text[i]
        if ch == term:
            seg_text = "".join(buf).strip("\r\n")
            buf = []
            i += 1
            if seg_text.strip():
                seg_id, elements = _split_elements(seg_text, separators)
                segments.append(
                    ParsedSegment(
                        seg_id=seg_id,
                        elements=elements,
                        raw=seg_text + term,
                        line_number=current_line,
                    )
                )
            while i < n and text[i] in "\r\n":
                if text[i] == "\n":
                    current_line += 1
                i += 1
        else:
            buf.append(ch)
            i += 1
    leftover = "".join(buf).strip()
    if leftover:
        raise ValueError(
            f"Trailing content after the last segment terminator was not empty: {leftover!r}."
        )
    return segments


def _split_elements(seg_text: str, separators: Separators) -> tuple[str, list[tuple[str, str]]]:
    parts = seg_text.split(separators.element_separator)
    seg_id = parts[0].strip()
    elements: list[tuple[str, str]] = []
    for index, raw in enumerate(parts[1:], start=1):
        if separators.sub_element_separator in raw:
            for sub_index, sub in enumerate(raw.split(separators.sub_element_separator), start=1):
                elements.append((f"{index:02d}-{sub_index}", sub))
        else:
            elements.append((f"{index:02d}", raw))
    return seg_id, elements


def _kind_from_guide(guide: str) -> str:
    label, _ = GUIDE_LABELS.get(guide, ("", ""))
    return label


def _segment_hint(segment: ParsedSegment) -> str:
    qualifier = segment.qualifier
    if segment.seg_id == "HL":
        level = segment.value("03")
        qualified = QUALIFIED_HINTS.get(("HL", level))
        if qualified:
            return qualified
    qualified = QUALIFIED_HINTS.get((segment.seg_id, qualifier))
    if qualified:
        return qualified
    return SEGMENT_HINTS.get(segment.seg_id, "No glossary entry for this segment.")


def _element_hint(seg_id: str, position: str) -> str:
    return ELEMENT_HINTS.get((seg_id, position), "")


class _Cursor:
    def __init__(self) -> None:
        self.kind = ""
        self.claim_open = False
        self.cob_open = False
        self.loop_id = "Envelope"
        self.loop_title = "Interchange"
        self.line_label = ""

    def set_loop(self, loop_id: str, title: str) -> None:
        self.loop_id = loop_id
        self.loop_title = title


def _apply_segment(cursor: _Cursor, segment: ParsedSegment) -> None:
    seg_id = segment.seg_id
    qualifier = segment.qualifier
    if seg_id == "GS":
        guide = segment.value("08")
        kind = _kind_from_guide(guide)
        if kind:
            cursor.kind = kind
        cursor.claim_open = False
        cursor.cob_open = False
        cursor.set_loop("Envelope", "Functional group")
        return
    if seg_id == "ST":
        guide = segment.value("03")
        kind = _kind_from_guide(guide) or {"837": "837", "835": "835", "999": "999"}.get(segment.value("01"), "")
        if kind:
            cursor.kind = kind
        cursor.claim_open = False
        cursor.cob_open = False
        if cursor.kind == "835":
            cursor.set_loop("835-Header", "Transaction header")
        elif cursor.kind == "999":
            cursor.set_loop("999-Header", "Transaction header")
        elif cursor.kind in {"837", "837P", "837I"}:
            cursor.set_loop("Header", "Transaction header")
        else:
            cursor.set_loop("Body", "Unrecognized transaction")
        return
    if seg_id in {"ISA", "IEA", "GE"}:
        cursor.claim_open = False
        cursor.cob_open = False
        cursor.set_loop("Envelope", "Interchange" if seg_id != "GE" else "Functional group trailer")
        return
    if seg_id == "SE":
        cursor.set_loop("Trailer", "Transaction trailer")
        return

    kind = cursor.kind
    if kind in {"837", "837P", "837I"}:
        _apply_837(cursor, seg_id, qualifier, segment)
    elif kind == "835":
        _apply_835(cursor, seg_id, qualifier, segment)
    elif kind == "999":
        _apply_999(cursor, seg_id)
    else:
        cursor.set_loop("Body", "Unrecognized transaction")


def _apply_837(cursor: _Cursor, seg_id: str, qualifier: str, segment: ParsedSegment) -> None:
    if seg_id == "NM1" and qualifier == "41":
        cursor.set_loop("1000A", "Loop 1000A — Submitter")
    elif seg_id == "NM1" and qualifier == "40":
        cursor.set_loop("1000B", "Loop 1000B — Receiver")
    elif seg_id == "HL" and segment.value("03") == "20":
        cursor.claim_open = False
        cursor.cob_open = False
        cursor.set_loop("2000A", "Loop 2000A — Billing provider")
    elif seg_id == "HL" and segment.value("03") == "22":
        cursor.claim_open = False
        cursor.cob_open = False
        cursor.set_loop("2000B", "Loop 2000B — Subscriber")
    elif seg_id == "NM1" and qualifier == "85":
        cursor.set_loop("2010AA", "Loop 2010AA — Billing provider name")
    elif seg_id == "NM1" and qualifier == "IL":
        if cursor.cob_open:
            cursor.set_loop("2330A", "Loop 2330A — Other subscriber")
        else:
            cursor.set_loop("2010BA", "Loop 2010BA — Subscriber name")
    elif seg_id == "NM1" and qualifier == "PR":
        if cursor.cob_open:
            cursor.set_loop("2330B", "Loop 2330B — Other payer")
        else:
            cursor.set_loop("2010BB", "Loop 2010BB — Payer")
    elif seg_id == "NM1" and qualifier == "DN":
        cursor.set_loop("2310", "Loop 2310A — Referring provider")
    elif seg_id == "NM1" and qualifier == "82":
        cursor.set_loop("2310", "Loop 2310B — Rendering provider")
    elif seg_id == "NM1" and qualifier == "77":
        cursor.set_loop("2310", "Loop 2310 — Service facility")
    elif seg_id == "NM1" and qualifier == "71":
        cursor.set_loop("2310", "Loop 2310A — Attending provider")
    elif seg_id == "CLM":
        cursor.claim_open = True
        cursor.cob_open = False
        cursor.set_loop("2300", "Loop 2300 — Claim information")
    elif seg_id == "SBR":
        if cursor.claim_open:
            cursor.cob_open = True
            cursor.set_loop("2320", "Loop 2320 — Other subscriber / COB")
        else:
            cursor.set_loop("2000B", "Loop 2000B — Subscriber")
    elif seg_id == "LX":
        cursor.cob_open = False
        cursor.line_label = segment.value("01")
        title = "Loop 2400 — Service line"
        if cursor.line_label:
            title += f" {cursor.line_label}"
        cursor.set_loop("2400", title)
    elif seg_id in {"ST", "BHT"}:
        cursor.set_loop("Header", "Transaction header")


def _apply_835(cursor: _Cursor, seg_id: str, qualifier: str, segment: ParsedSegment) -> None:
    if seg_id == "N1" and qualifier == "PR":
        cursor.set_loop("835-1000A", "Loop 1000A — Payer")
    elif seg_id == "N1" and qualifier == "PE":
        cursor.set_loop("835-1000B", "Loop 1000B — Payee")
    elif seg_id == "LX":
        cursor.set_loop("835-2000", "Loop 2000 — Header number")
    elif seg_id == "CLP":
        claim_id = segment.value("01")
        title = "Loop 2100 — Claim payment"
        if claim_id:
            title += f" {claim_id}"
        cursor.set_loop("835-2100", title)
    elif seg_id == "SVC":
        cursor.set_loop("835-2110", "Loop 2110 — Service payment")
    elif seg_id in {"BPR", "TRN", "REF", "DTM"} and cursor.loop_id in {"835-Header", "Header", "Envelope"}:
        cursor.set_loop("835-Header", "Transaction header")


def _apply_999(cursor: _Cursor, seg_id: str) -> None:
    if seg_id == "AK1":
        cursor.set_loop("999-AK1", "AK1 — Functional group response")
    elif seg_id == "AK2":
        cursor.set_loop("999-AK2", "AK2 — Transaction set response")
    elif seg_id in {"AK3", "IK3"}:
        cursor.set_loop("999-AK3", "AK3 — Segment error")
    elif seg_id in {"AK4", "IK4"}:
        cursor.set_loop("999-AK4", "AK4 — Element error")
    elif seg_id == "AK5":
        cursor.set_loop("999-AK5", "AK5 — Transaction acknowledgment")
    elif seg_id == "AK9":
        cursor.set_loop("999-AK9", "AK9 — Functional group acknowledgment")


def _show(segment: ParsedSegment, cursor: _Cursor) -> ShownSegment:
    return ShownSegment(
        segment=segment,
        hint=_segment_hint(segment),
        loop_id=cursor.loop_id,
        loop_title=cursor.loop_title,
        loop_hint=LOOP_HINTS.get(cursor.loop_id, ""),
    )


def _transaction_label(kind: str, guide: str) -> tuple[str, str, str]:
    if guide in GUIDE_LABELS:
        short, label = GUIDE_LABELS[guide]
        return short, label, ""
    if kind in {"837", "837P", "837I"}:
        return kind, f"{kind} encounter", ""
    if kind == "835":
        return "835", "835 payment", ""
    if kind == "999":
        return "999", "999 acknowledgment", ""
    return "Unknown", "Unrecognized transaction", "Loop names are generic because the implementation guide version was not recognized."


def build_groups(segments: list[ParsedSegment]) -> tuple[list[ShownSegment], list[GroupView], list[ShownSegment]]:
    cursor = _Cursor()
    shown = [_annotate(cursor, segment) for segment in segments]
    preamble: list[ShownSegment] = []
    groups: list[GroupView] = []
    trailer: list[ShownSegment] = []
    current: GroupView | None = None
    transaction: TransactionView | None = None
    block: LoopBlock | None = None

    def flush_block() -> None:
        nonlocal block
        if transaction is not None and block is not None and block.segments:
            transaction.blocks.append(block)
        block = None

    def flush_transaction() -> None:
        nonlocal transaction
        flush_block()
        if current is not None and transaction is not None and (transaction.blocks or transaction.label):
            current.transactions.append(transaction)
        transaction = None

    for item in shown:
        seg_id = item.segment.seg_id
        if seg_id == "ISA":
            preamble.append(item)
            continue
        if seg_id == "IEA":
            flush_transaction()
            trailer.append(item)
            continue
        if seg_id == "GS":
            flush_transaction()
            if current is not None:
                groups.append(current)
            guide = item.segment.value("08")
            kind = _kind_from_guide(guide)
            _short, label, _note = _transaction_label(kind, guide)
            current = GroupView(label=label or kind or guide or "Functional group", kind=kind)
            current.header.append(item)
            continue
        if current is None:
            preamble.append(item)
            continue
        if seg_id == "GE":
            flush_transaction()
            current.trailer.append(item)
            continue
        if seg_id == "ST":
            flush_transaction()
            guide = item.segment.value("03") or ""
            kind = _kind_from_guide(guide) or {"837": "837", "835": "835", "999": "999"}.get(
                item.segment.value("01"), current.kind
            )
            _short, label, note = _transaction_label(kind, guide)
            transaction = TransactionView(label=label, guide=guide, note=note)
            block = LoopBlock(item.loop_id, item.loop_title, item.loop_hint, [item])
            continue
        if transaction is None:
            current.header.append(item)
            continue
        if block is None or block.loop_id != item.loop_id or block.title != item.loop_title:
            flush_block()
            block = LoopBlock(item.loop_id, item.loop_title, item.loop_hint, [item])
        else:
            block.segments.append(item)
        if seg_id == "SE":
            flush_transaction()
    flush_transaction()
    if current is not None:
        groups.append(current)
    return preamble, groups, trailer


_HL_SUBSCRIBER_RE = re.compile(r"subscriber HL (\S+)")

# Where a missing segment would have lived. Parent links are the next higher loop.
_RULE_LOOP = {
    "L3-BILLING-UMPI-REQUIRED": "2010AA",
    "L3-BILLING-TIN-REQUIRED": "2010AA",
    "L3-SERVICE-FACILITY-UMPI-REQUIRED": "2310",
    "L3-837I-ATTENDING-UMPI-REQUIRED": "2310",
    "L3-REFERRING-UMPI-REQUIRED": "2310",
    "L3-RENDERING-UMPI-REQUIRED": "2310",
    "L3-SUBSCRIBER-DMG-REQUIRED": "2010BA",
    "L3-837I-CL1-REQUIRED": "2300",
    "L3-837I-NTE-PATIENT-ACCOUNT-REQUIRED": "2300",
    "L3-837I-STATEMENT-DATES-REQUIRED": "2300",
    "L3-LINE-PAID-AMOUNT-REQUIRED-837P": "2400",
    "L3-LINE-PAID-AMOUNT-REQUIRED-837I": "2400",
}

_LOOP_PARENT = {
    "2010AA": "2000A",
    "2010BA": "2000B",
    "2010BB": "2000B",
    "2310": "2300",
    "2320": "2300",
    "2330A": "2320",
    "2330B": "2320",
    "2400": "2300",
    "2300": "2000B",
    "2000B": "2000A",
    "2000A": "Header",
    "1000A": "Header",
    "1000B": "Header",
    "Header": "Envelope",
}

_ENVELOPE_SEGMENTS = {"ISA", "IEA", "GS", "GE"}


def _finding_dict(raw: dict) -> dict | None:
    severity = str(raw.get("severity") or "error")
    if severity not in {"error", "warning"}:
        return None
    line = raw.get("line_number")
    return {
        "severity": severity,
        "rule_id": str(raw.get("rule_id") or ""),
        "message": str(raw.get("message") or ""),
        "segment_id": raw.get("segment_id"),
        "line_number": int(line) if isinstance(line, int) else None,
        "missing": False,
        "anchor_line": 0,
        "number": 0,
    }


def _expected_loop(finding: dict) -> str:
    rule_id = finding["rule_id"]
    if rule_id in _RULE_LOOP:
        return _RULE_LOOP[rule_id]
    segment_id = finding.get("segment_id") or ""
    if segment_id in _ENVELOPE_SEGMENTS or rule_id.startswith("L1-"):
        return "Envelope"
    return "Header"


def _segments_in(blocks: list[LoopBlock]) -> list[ShownSegment]:
    found: list[ShownSegment] = []
    for block in blocks:
        found.extend(block.segments)
    return found


def _claim_blocks(transaction: TransactionView, hl_id: str | None) -> list[LoopBlock]:
    if not hl_id:
        return transaction.blocks
    target_line = None
    for item in _segments_in(transaction.blocks):
        segment = item.segment
        if segment.seg_id == "HL" and segment.value("03") == "22" and segment.value("01") == hl_id:
            target_line = segment.line_number
            break
    if target_line is None:
        return []
    start = target_line
    for item in _segments_in(transaction.blocks):
        segment = item.segment
        if segment.seg_id == "HL" and segment.value("03") == "20" and segment.line_number <= target_line:
            start = segment.line_number
    end = None
    for item in _segments_in(transaction.blocks):
        segment = item.segment
        if segment.seg_id == "HL" and segment.value("03") == "20" and segment.line_number > target_line:
            end = segment.line_number
            break
    selected: list[LoopBlock] = []
    for block in transaction.blocks:
        lines = [item.segment.line_number for item in block.segments]
        if lines and min(lines) >= start and (end is None or min(lines) < end):
            selected.append(block)
    return selected


def _loop_or_ancestor(blocks: list[LoopBlock], loop_id: str) -> LoopBlock | None:
    current: str | None = loop_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        for block in blocks:
            if block.loop_id == current:
                return block
        current = _LOOP_PARENT.get(current)
    return None


def _place_findings(
    interchange: LoopBlock | None,
    groups: list[GroupView],
    trailer: list[ShownSegment],
    findings: list[dict],
) -> None:
    by_line: dict[int, ShownSegment] = {}
    if interchange is not None:
        for item in interchange.segments:
            by_line[item.segment.line_number] = item
    transactions: list[TransactionView] = []
    for group in groups:
        for item in group.header:
            by_line[item.segment.line_number] = item
        transactions.extend(group.transactions)
        for transaction in group.transactions:
            for block in transaction.blocks:
                for item in block.segments:
                    by_line[item.segment.line_number] = item
        for item in group.trailer:
            by_line[item.segment.line_number] = item
    for item in trailer:
        by_line[item.segment.line_number] = item

    for raw in findings:
        finding = _finding_dict(raw)
        if finding is None:
            continue
        line_number = finding["line_number"]
        if line_number is not None and line_number in by_line:
            host = by_line[line_number]
            finding["anchor_line"] = line_number
            host.markers.append(finding)
            continue
        finding["missing"] = True
        expected = _expected_loop(finding)
        if expected == "Envelope" and interchange is not None:
            finding["anchor_line"] = interchange.segments[0].segment.line_number if interchange.segments else 0
            interchange.markers.append(finding)
            continue
        hl_match = _HL_SUBSCRIBER_RE.search(finding["message"])
        hl_id = hl_match.group(1) if hl_match else None
        placed = False
        candidates = transactions
        if hl_id:
            scoped = [tx for tx in transactions if _claim_blocks(tx, hl_id)]
            if scoped:
                candidates = scoped
        for transaction in candidates:
            blocks = _claim_blocks(transaction, hl_id) if hl_id else transaction.blocks
            if not blocks:
                blocks = transaction.blocks
            block = _loop_or_ancestor(blocks, expected)
            if block is None:
                continue
            lines = [item.segment.line_number for item in block.segments]
            finding["anchor_line"] = min(lines) if lines else 0
            block.markers.append(finding)
            placed = True
            break
        if placed:
            continue
        if transactions:
            finding["anchor_line"] = 0
            transactions[0].markers.append(finding)
        elif interchange is not None:
            finding["anchor_line"] = 0
            interchange.markers.append(finding)


def _number_markers(
    interchange: LoopBlock | None,
    groups: list[GroupView],
    trailer: list[ShownSegment],
) -> int:
    collected: list[dict] = []
    if interchange is not None:
        collected.extend(interchange.markers)
        for item in interchange.segments:
            collected.extend(item.markers)
    for group in groups:
        for item in group.header:
            collected.extend(item.markers)
        for transaction in group.transactions:
            collected.extend(transaction.markers)
            for block in transaction.blocks:
                collected.extend(block.markers)
                for item in block.segments:
                    collected.extend(item.markers)
        for item in group.trailer:
            collected.extend(item.markers)
    for item in trailer:
        collected.extend(item.markers)
    collected.sort(key=lambda marker: (marker["anchor_line"], marker["rule_id"]))
    for number, marker in enumerate(collected, start=1):
        marker["number"] = number
    return len(collected)


def _annotate(cursor: _Cursor, segment: ParsedSegment) -> ShownSegment:
    _apply_segment(cursor, segment)
    return _show(segment, cursor)


def render_html(text: str, filename: str = "edi.x12", findings: list[dict] | None = None) -> str:
    separators = detect_separators(text)
    segments = parse_segments(text, separators)
    preamble, groups, trailer = build_groups(segments)
    interchange = LoopBlock("Envelope", "Interchange header", LOOP_HINTS["Envelope"], preamble) if preamble else None
    _place_findings(interchange, groups, trailer, findings or [])
    marker_count = _number_markers(interchange, groups, trailer)
    kinds = []
    for group in groups:
        if group.label and group.label not in kinds:
            kinds.append(group.label)
    banner = ", ".join(kinds) if kinds else "Unrecognized transaction"
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>EDI view — {_esc(filename)}</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        "<header>",
        f"<h1>{_esc(filename)}</h1>",
        f"<p class=\"banner\">{_esc(banner)}</p>",
        "<p class=\"fine\">Hints explain the loops and segments used on 837, 835, and 999 files. They are a reading aid, not a full implementation guide.</p>",
        '<label class="filter">Filter <input id="q" type="search" placeholder="segment, loop, or text"></label>',
        "</header>",
    ]
    walk_buttons = (
        '<button type="button" id="collapse-all">Collapse all</button>'
        '<button type="button" id="expand-all">Expand all</button>'
    )
    if marker_count:
        walk_buttons += (
            '<button type="button" id="prev">Previous</button>'
            f'<span id="walk-pos">1 of {marker_count}</span>'
            '<button type="button" id="next">Next</button>'
        )
    parts.append(f'<nav id="walk">{walk_buttons}</nav>')
    parts.append("<main>")
    if interchange is not None:
        parts.append(_render_outline(_outline_block(interchange)))
    for index, group in enumerate(groups, start=1):
        group_body: list[str] = []
        group_errors = 0
        group_warnings = 0
        if group.header:
            group_body.append(_render_loose("Group header", group.header))
        for tx_index, transaction in enumerate(group.transactions, start=1):
            nodes = _outline_blocks(transaction.blocks)
            tx_errors = sum(1 for marker in transaction.markers if marker["severity"] == "error")
            tx_warnings = sum(1 for marker in transaction.markers if marker["severity"] == "warning")
            for node in nodes:
                child_errors, child_warnings = _outline_counts(node)
                tx_errors += child_errors
                tx_warnings += child_warnings
            group_errors += tx_errors
            group_warnings += tx_warnings
            note = f'<p class="note">{_esc(transaction.note)}</p>' if transaction.note else ""
            tx_body = note + _render_markers(transaction.markers) + "".join(_render_outline(node) for node in nodes)
            group_body.append(
                _details_shell(
                    "tx",
                    f"Transaction set {tx_index} — {transaction.label}",
                    tx_body,
                    tx_errors,
                    tx_warnings,
                    str(len(nodes)),
                    start_open=True,
                )
            )
        if group.trailer:
            group_body.append(_render_loose("Group trailer", group.trailer))
        parts.append(
            _details_shell(
                "group",
                f"Functional group {index} — {group.label}",
                "".join(group_body),
                group_errors,
                group_warnings,
                str(len(group.transactions)),
                start_open=True,
            )
        )
    if trailer:
        parts.append(_render_loose("Interchange trailer", trailer))
    parts.append("</main>")
    parts.append(f"<script>{_JS}</script>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


@dataclass
class Outline:
    title: str
    hint: str
    role: str
    block: LoopBlock | None = None
    children: list[Outline] = field(default_factory=list)


_CLAIM_CHILD_LOOPS = {"2010BA", "2010BB", "2300", "2310", "2320", "2330A", "2330B", "2400", "835-2110", "999-AK3", "999-AK4", "999-AK5"}
_BILLING_CHILD_LOOPS = {"2010AA"}


def _outline_block(block: LoopBlock) -> Outline:
    return Outline(block.title, block.hint, "loop", block)


def _claim_title(block: LoopBlock) -> str:
    for item in block.segments:
        segment = item.segment
        if segment.seg_id == "HL" and segment.value("03") == "22":
            return f"Subscriber HL {segment.value('01')}"
        if segment.seg_id == "CLP" and segment.value("01"):
            return f"Claim payment {segment.value('01')}"
        if segment.seg_id == "AK2":
            return f"Acknowledged transaction {segment.value('02') or segment.value('01')}"
    return "Claim"


def _apply_claim_identity(claim: Outline, block: LoopBlock) -> None:
    for item in block.segments:
        segment = item.segment
        if segment.seg_id == "CLM" and segment.value("01"):
            claim.title = f"Claim {segment.value('01')}"
        if segment.seg_id == "NM1" and segment.qualifier == "IL" and segment.value("03"):
            if not claim.title.startswith("Claim "):
                claim.title = f"Subscriber {segment.value('03')}"


def _apply_billing_identity(billing: Outline, block: LoopBlock) -> None:
    for item in block.segments:
        segment = item.segment
        if segment.seg_id == "NM1" and segment.qualifier == "85" and segment.value("03"):
            billing.title = f"Billing provider {segment.value('03')}"


def _outline_blocks(blocks: list[LoopBlock]) -> list[Outline]:
    roots: list[Outline] = []
    billing: Outline | None = None
    claim: Outline | None = None
    for block in blocks:
        loop_id = block.loop_id
        if loop_id == "2000A":
            claim = None
            billing = Outline(block.title, "Billing provider and the claims reported under it.", "billing", children=[_outline_block(block)])
            roots.append(billing)
            continue
        if loop_id in {"2000B", "835-2100", "999-AK2"}:
            claim = Outline(_claim_title(block), "One claim. Collapse this to hide its loops and service lines.", "claim", children=[_outline_block(block)])
            if billing is not None and loop_id == "2000B":
                billing.children.append(claim)
            else:
                billing = None
                roots.append(claim)
            continue
        if claim is not None and loop_id in _CLAIM_CHILD_LOOPS:
            _apply_claim_identity(claim, block)
            claim.children.append(_outline_block(block))
            continue
        if billing is not None and loop_id in _BILLING_CHILD_LOOPS:
            _apply_billing_identity(billing, block)
            billing.children.append(_outline_block(block))
            continue
        claim = None
        billing = None
        roots.append(_outline_block(block))
    return roots


def format_plain_edi(text: str) -> str:
    """One segment per line, indented by the same hierarchy as the annotated view.

    A file with no line breaks is split on the segment terminator first.
    """
    try:
        separators = detect_separators(text)
        segments = parse_segments(text, separators)
    except ValueError:
        return _plain_fallback(text)
    preamble, groups, trailer = build_groups(segments)
    lines: list[str] = []
    lines.extend(_plain_segments(preamble, 0))
    for group in groups:
        lines.extend(_plain_segments(group.header, 1))
        for transaction in group.transactions:
            lines.extend(_plain_outline(_outline_blocks(transaction.blocks), 2))
        lines.extend(_plain_segments(group.trailer, 1))
    lines.extend(_plain_segments(trailer, 0))
    if not lines:
        return _plain_fallback(text)
    return "\n".join(lines) + "\n"


def _plain_segments(segments: list[ShownSegment], depth: int) -> list[str]:
    indent = "  " * depth
    return [f"{indent}{item.segment.raw.strip()}" for item in segments]


def _plain_outline(nodes: list[Outline], depth: int) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        if node.role == "loop" and node.block is not None:
            lines.extend(_plain_segments(node.block.segments, depth))
        else:
            lines.extend(_plain_outline(node.children, depth + 1))
    return lines


def _plain_fallback(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if "~" in stripped:
        parts = [part.strip() for part in stripped.split("~") if part.strip()]
        return "\n".join(f"{part}~" for part in parts) + "\n"
    return stripped + "\n"


def _outline_counts(node: Outline) -> tuple[int, int]:
    errors = 0
    warnings = 0
    if node.block is not None:
        markers = list(node.block.markers)
        for item in node.block.segments:
            markers.extend(item.markers)
        errors += sum(1 for marker in markers if marker["severity"] == "error")
        warnings += sum(1 for marker in markers if marker["severity"] == "warning")
    for child in node.children:
        child_errors, child_warnings = _outline_counts(child)
        errors += child_errors
        warnings += child_warnings
    return errors, warnings


def _details_shell(
    role: str,
    title: str,
    body: str,
    errors: int,
    warnings: int,
    count_label: str,
    start_open: bool = False,
) -> str:
    severity = " has-error" if errors else (" has-warning" if warnings else "")
    badge = ""
    if errors:
        label = "error" if errors == 1 else "errors"
        badge = f'<span class="badge error">{errors} {label}</span>'
    elif warnings:
        label = "warning" if warnings == 1 else "warnings"
        badge = f'<span class="badge warning">{warnings} {label}</span>'
    opened = " open" if start_open else ""
    return (
        f'<details class="loop {role}{severity}"{opened}>'
        f"<summary><span class=\"loop-id\">{_esc(title)}</span>"
        f'<span class="count">{count_label}</span>{badge}</summary>'
        f'<div class="fold">{body}</div></details>'
    )


def _render_outline(node: Outline) -> str:
    errors, warnings = _outline_counts(node)
    if node.role == "loop" and node.block is not None:
        body = (
            f'<p class="loop-hint">{_esc(node.block.hint)}</p>'
            f"{_render_markers(node.block.markers)}"
            + "".join(_render_segment(item) for item in node.block.segments)
        )
        count = str(len(node.block.segments))
    else:
        body = "".join(_render_outline(child) for child in node.children)
        count = str(len(node.children))
    return _details_shell(node.role, node.title, body, errors, warnings, count, start_open=node.role == "billing")


def _render_loose(title: str, segments: list[ShownSegment]) -> str:
    block = LoopBlock("Envelope", title, LOOP_HINTS["Envelope"], segments)
    return _render_outline(_outline_block(block))


def _render_markers(markers: list[dict]) -> str:
    parts = []
    for marker in markers:
        number = marker["number"]
        severity = marker["severity"] if marker["severity"] in {"error", "warning"} else "error"
        missing = ""
        if marker.get("missing"):
            missing = '<p class="missing">Reported segment is not in the file.</p>'
        parts.append(
            f'<aside class="marker {severity}" id="marker-{number}" data-marker="{number}">'
            f"<strong>{_esc(marker['rule_id'])}</strong>"
            f"<p>{_esc(marker['message'])}</p>"
            f"{missing}</aside>"
        )
    return "".join(parts)


def _render_segment(item: ShownSegment) -> str:
    segment = item.segment
    element_rows = []
    for position, value in segment.elements:
        hint = _element_hint(segment.seg_id, position)
        element_rows.append(
            "<tr>"
            f"<td>{_esc(position)}</td>"
            f"<td><code>{_esc(value) if value else '—'}</code></td>"
            f"<td>{_esc(hint) if hint else ''}</td>"
            "</tr>"
        )
    searchable = " ".join(
        [
            segment.seg_id,
            item.hint,
            item.loop_title,
            segment.raw,
            " ".join(value for _pos, value in segment.elements),
        ]
    )
    flagged = " has-marker" if item.markers else ""
    return (
        f'<article class="seg{flagged}" data-text="{_esc(searchable.lower())}">'
        f'<div class="seg-head"><code>{_esc(segment.seg_id)}</code>'
        f'<span class="line">line {segment.line_number}</span></div>'
        f'<p class="hint">{_esc(item.hint)}</p>'
        f"{_render_markers(item.markers)}"
        f'<pre class="raw">{_esc(segment.raw)}</pre>'
        '<table><thead><tr><th>Pos</th><th>Value</th><th>Hint</th></tr></thead>'
        f"<tbody>{''.join(element_rows)}</tbody></table>"
        "</article>"
    )


def _esc(value: str) -> str:
    return html.escape(value, quote=True)


_CSS = """
:root { color-scheme: light; --ink: #1c2430; --muted: #5c6b7a; --line: #d5dde6; --paper: #f6f8fb; --card: #fff; --accent: #1f4e79; }
* { box-sizing: border-box; }
body { margin: 0; font: 15px/1.45 "Segoe UI", sans-serif; color: var(--ink); background: var(--paper); }
header { padding: 1.25rem 1.5rem 1rem; background: var(--accent); color: #fff; }
h1 { margin: 0 0 .25rem; font-size: 1.35rem; }
h2, h3 { margin: 1.25rem 0 .5rem; }
.banner { margin: 0; font-weight: 600; }
.fine { margin: .4rem 0 0; color: #d6e4f2; font-size: .9rem; }
.filter { display: block; margin-top: .8rem; }
.filter input { margin-left: .4rem; padding: .35rem .5rem; width: min(28rem, 100%); border: 0; border-radius: 4px; }
main { padding: 1rem 1.5rem 2rem; }
.group, .tx { margin-bottom: 1rem; }
.loop { background: var(--card); border: 1px solid var(--line); border-radius: 8px; margin: .45rem 0; padding: .15rem .7rem .35rem; }
summary { cursor: pointer; font-weight: 650; padding: .45rem .2rem; list-style-position: outside; }
.fold { margin-left: 1.15rem; }
.loop-id { margin-right: .5rem; }
.count { color: var(--muted); font-weight: 500; font-size: .85rem; }
.badge { margin-left: .55rem; font-size: .75rem; font-weight: 700; padding: .05rem .45rem; border-radius: 999px; vertical-align: middle; }
.badge.error { background: #b42318; color: #fff; }
.badge.warning { background: #b54708; color: #fff; }
details.has-error { border-color: #e7b3b3; background: #fff8f8; }
details.has-warning { border-color: #f0d090; background: #fffdf6; }
details.has-error > summary { background: #fde8e8; color: #7a1c14; border-radius: 6px; }
details.has-warning > summary { background: #fff6e0; color: #7a4b08; border-radius: 6px; }
.loop-hint, .hint, .note { color: var(--muted); }
.note { background: #fff8e8; color: #6a4b00; padding: .5rem .7rem; border-radius: 6px; }
.seg { border-top: 1px solid var(--line); padding: .7rem 0; }
.seg-head { display: flex; gap: .8rem; align-items: baseline; }
.seg-head code { font-size: 1rem; color: var(--accent); }
.line { color: var(--muted); font-size: .85rem; }
.raw { background: #eef3f8; padding: .45rem .6rem; overflow-x: auto; border-radius: 4px; }
table { width: 100%; border-collapse: collapse; font-size: .92rem; }
th, td { text-align: left; padding: .25rem .4rem; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 600; }
.hidden { display: none; }
#walk { position: sticky; top: 0; z-index: 2; display: flex; gap: .6rem; align-items: center; padding: .55rem 1.5rem; background: #fff; border-bottom: 1px solid var(--line); }
#walk button { background: var(--accent); color: #fff; border: 0; border-radius: 4px; padding: .35rem .7rem; cursor: pointer; }
.marker { margin: .45rem 0; padding: .45rem .65rem; border-left: 4px solid #b42318; border-radius: 4px; background: #fde8e8; }
.marker.warning { border-left-color: #b54708; background: #fff6e0; }
.marker p { margin: .2rem 0 0; }
.missing { font-style: italic; }
.marker.current { outline: 2px solid var(--accent); }
.seg.has-marker { background: #fff8f8; }
"""

_JS = """
const input = document.getElementById("q");
input.addEventListener("input", () => {
  const query = input.value.trim().toLowerCase();
  document.querySelectorAll(".seg").forEach((node) => {
    const haystack = node.getAttribute("data-text") || "";
    node.classList.toggle("hidden", query.length > 0 && !haystack.includes(query));
  });
  document.querySelectorAll(".loop").forEach((loop) => {
    const visible = loop.querySelector(".seg:not(.hidden)");
    loop.classList.toggle("hidden", query.length > 0 && !visible);
  });
});

const markers = [...document.querySelectorAll("[data-marker]")].sort(
  (left, right) => Number(left.getAttribute("data-marker")) - Number(right.getAttribute("data-marker"))
);
let markerIndex = 0;
function showMarker(nextIndex) {
  if (!markers.length) return;
  markerIndex = (nextIndex + markers.length) % markers.length;
  markers.forEach((node) => node.classList.remove("current"));
  const node = markers[markerIndex];
  node.classList.add("current");
  openAncestors(node);
  node.scrollIntoView({behavior: "smooth", block: "center"});
  const label = document.getElementById("walk-pos");
  if (label) label.textContent = (markerIndex + 1) + " of " + markers.length;
}
function openAncestors(node) {
  let parent = node.parentElement;
  while (parent) {
    if (parent.tagName === "DETAILS") parent.open = true;
    parent = parent.parentElement;
  }
}
const previous = document.getElementById("prev");
const next = document.getElementById("next");
if (previous && next && markers.length) {
  previous.addEventListener("click", () => showMarker(markerIndex - 1));
  next.addEventListener("click", () => showMarker(markerIndex + 1));
  showMarker(0);
}
document.getElementById("collapse-all").addEventListener("click", () => {
  document.querySelectorAll("details.loop").forEach((node) => { node.open = false; });
});
document.getElementById("expand-all").addEventListener("click", () => {
  document.querySelectorAll("details.loop").forEach((node) => { node.open = true; });
});
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an X12 837, 835, or 999 file as readable HTML.")
    parser.add_argument("--in", dest="source", required=True, help="Input .x12 file")
    parser.add_argument("--out", dest="destination", required=True, help="Output .html file")
    parser.add_argument(
        "--findings",
        dest="findings",
        help="JSON report from mn-encounter validate --format json",
    )
    args = parser.parse_args()
    source = Path(args.source)
    text = source.read_text(encoding="utf-8")
    findings = None
    if args.findings:
        payload = json.loads(Path(args.findings).read_text(encoding="utf-8"))
        findings = payload.get("findings", payload if isinstance(payload, list) else [])
    html_text = render_html(text, filename=source.name, findings=findings)
    destination = Path(args.destination)
    destination.write_text(html_text, encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
