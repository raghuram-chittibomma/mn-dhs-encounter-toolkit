"""HTML view of an X12 837, 835, or 999 file."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("render_edi_html", ROOT / "scripts" / "render_edi_html.py")
assert _SPEC is not None and _SPEC.loader is not None
render_edi_html = importlib.util.module_from_spec(_SPEC)
sys.modules["render_edi_html"] = render_edi_html
_SPEC.loader.exec_module(render_edi_html)


def test_clean_batch_html_names_loops_and_stays_offline():
    source = ROOT / "examples" / "clean_batch.x12"
    html = render_edi_html.render_html(source.read_text(encoding="utf-8"), filename=source.name)
    assert "Loop 2300" in html
    assert "Billing provider" in html
    assert "http://" not in html
    assert "https://" not in html
    assert "NM1" in html


def test_835_and_999_loops_are_labeled():
    isa = (
        "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       "
        "*260101*0800*[*00501*000000001*0*T*:~"
    )
    remittance = (
        isa
        + "GS*HP*SENDER*RECEIVER*20260101*0800*1*X*005010X221A1~"
        + "ST*835*0001*005010X221A1~"
        + "BPR*H*10.00*C*NON~"
        + "TRN*1*TRACE*PAYERID~"
        + "N1*PR*PAYER*PI*PAYERID~"
        + "N1*PE*PAYEE*XX*1234567893~"
        + "CLP*CLAIM1*1*10.00*10.00*0*MC*CLAIM1~"
        + "SVC*HC:99213*10.00*10.00~"
        + "SE*8*0001~"
        + "GE*1*1~"
        + "IEA*1*000000001~"
    )
    ack = (
        isa
        + "GS*FA*RECEIVER*SENDER*20260101*0800*1*X*005010X231A1~"
        + "ST*999*0001*005010X231A1~"
        + "AK1*HC*1~"
        + "AK2*837*0001~"
        + "AK5*A~"
        + "AK9*A*1*1*1~"
        + "SE*6*0001~"
        + "GE*1*1~"
        + "IEA*1*000000001~"
    )
    remittance_html = render_edi_html.render_html(remittance, filename="remit.x12")
    ack_html = render_edi_html.render_html(ack, filename="ack.x12")
    assert "Loop 2100" in remittance_html
    assert "Loop 2110" in remittance_html
    payment = remittance_html.find("Claim payment CLAIM1")
    assert payment >= 0
    assert "Loop 2110" in remittance_html[payment:payment + 4000]
    assert "AK2" in ack_html
    assert "Acknowledged transaction 0001" in ack_html
    assert "Functional group acknowledgment" in ack_html
    assert "Collapse all" in remittance_html
    assert "Expand all" in remittance_html


def test_claim_is_its_own_collapsible_and_keeps_error_color():
    source = ROOT / "examples" / "clean_batch.x12"
    text = source.read_text(encoding="utf-8")
    separators = render_edi_html.detect_separators(text)
    segments = render_edi_html.parse_segments(text, separators)
    amount = next(segment for segment in segments if segment.raw.startswith("AMT*D*"))
    claim = next(segment for segment in segments if segment.seg_id == "CLM")
    claim_id = next(value for position, value in claim.elements if position == "01")
    page = render_edi_html.render_html(
        text,
        filename=source.name,
        findings=[
            {
                "severity": "error",
                "rule_id": "L2-AMT02-MONEY-FORMAT",
                "message": "AMT02 is not a two-decimal amount.",
                "segment_id": "AMT",
                "line_number": amount.line_number,
            }
        ],
    )
    title = f"Claim {claim_id}"
    start = page.find(title)
    assert start > page.find("Billing provider")
    details_at = page.rfind("<details", 0, start)
    summary = page[details_at:page.find("</summary>", start)]
    assert 'class="loop claim has-error"' in summary
    assert "1 error" in summary
    loop_2300 = page.find("Loop 2300", start)
    loop_2400 = page.find("Loop 2400", start)
    next_claim = page.find('class="loop claim', start)
    assert loop_2300 > start
    assert loop_2400 > loop_2300
    if next_claim >= 0:
        assert loop_2400 < next_claim
    assert 'class="fold"' in page


def _between(page: str, start: str, end: str) -> str:
    begin = page.find(start)
    assert begin >= 0, start
    finish = page.find(end, begin + len(start))
    assert finish >= 0, end
    return page[begin:finish]


def test_line_finding_marks_the_amt_segment():
    source = ROOT / "examples" / "clean_batch.x12"
    text = source.read_text(encoding="utf-8")
    separators = render_edi_html.detect_separators(text)
    segments = render_edi_html.parse_segments(text, separators)
    amount = next(segment for segment in segments if segment.raw.startswith("AMT*D*"))
    page = render_edi_html.render_html(
        text,
        filename=source.name,
        findings=[
            {
                "severity": "error",
                "rule_id": "L2-AMT02-MONEY-FORMAT",
                "message": "AMT02 is not a two-decimal amount.",
                "segment_id": "AMT",
                "line_number": amount.line_number,
            }
        ],
    )
    raw_at = page.find(amount.raw)
    article = page[page.rfind("<article", 0, raw_at) : page.find("</article>", raw_at)]
    assert "L2-AMT02-MONEY-FORMAT" in article
    window = article
    assert "not in the file" not in window
    assert "http://" not in page
    assert "https://" not in page
    assert 'id="walk"' in page


def test_missing_umpi_marks_billing_loop_or_its_parent():
    source = ROOT / "examples" / "clean_batch.x12"
    text = source.read_text(encoding="utf-8")
    finding = {
        "severity": "error",
        "rule_id": "L3-BILLING-UMPI-REQUIRED",
        "message": "Billing provider for claim under subscriber HL 2 is missing a REF*G2 (UMPI) secondary identifier.",
        "segment_id": "REF",
        "line_number": None,
    }
    marked = render_edi_html.render_html(text, filename=source.name, findings=[finding])
    billing = _between(marked, "Loop 2010AA", "Loop 2000B")
    assert "L3-BILLING-UMPI-REQUIRED" in billing
    assert "Reported segment is not in the file." in billing

    removed = text.replace(
        "NM1*85*1*Lindqvist*Quinn****XX*1654235112~\n"
        "N3*850 River Rd~\n"
        "N4*Bloomington*MN*55431~\n"
        "REF*EI*906184959~\n"
        "REF*G2*61559407~\n",
        "",
    )
    fallback = render_edi_html.render_html(removed, filename=source.name, findings=[finding])
    parent = _between(fallback, "Loop 2000A", "Loop 2000B")
    assert "L3-BILLING-UMPI-REQUIRED" in parent
    assert "Reported segment is not in the file." in parent
    assert "http://" not in fallback
    assert "https://" not in fallback
