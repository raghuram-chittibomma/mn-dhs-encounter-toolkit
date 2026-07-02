"""Add highlight annotations to the DHS 837 Encounter Companion Guide PDF.

Maps Layer 1 and Layer 3 rules (plus ISA11 default separators) to highlighted
passages. Requires: pip install pymupdf

Run from repo root:
    python scripts/annotate_dhs_companion_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SRC_PDF = ROOT / "docs" / "reference" / "dhs_837_encounter_companion_guide.pdf"
OUT_PDF = ROOT / "docs" / "reference" / "annotated" / "dhs_837_encounter_companion_guide_annotated.pdf"

from mn_encounter_toolkit.validator.layer1_envelope import LAYER1  # noqa: E402
from mn_encounter_toolkit.validator.layer3_dhs_rules import LAYER3  # noqa: E402
from mn_encounter_toolkit.validator.rule_registry import RuleInfo  # noqa: E402

# Extra highlight not on a @register citation.
EXTRA_HIGHLIGHTS: list[dict] = [
    {
        "rule_id": "DEFAULT-SEPARATORS-ISA11",
        "source_citation": "dhs_837_encounter_companion_guide.pdf p.35 (ISA11)",
        "terms": ["REPETITION SEPARATOR", "PLEASE SEND DHS", "ISA11"],
    },
]


def _pages_1_indexed(citation: str) -> list[int]:
    pages: set[int] = set()
    for start, end in re.findall(r"p\.(\d+)-(\d+)", citation):
        pages.update(range(int(start), int(end) + 1))
    for page in re.findall(r"p\.(\d+)", citation):
        pages.add(int(page))
    return sorted(pages)


def _tokens_from_quote(text: str) -> list[str]:
    """Pull short, distinctive tokens likely to appear in PDF text."""
    tokens: list[str] = []
    for match in re.findall(r"[A-Z]{2,}[0-9]*(?:-[0-9]+)?", text):
        if len(match) >= 3:
            tokens.append(match)
    for match in re.findall(r"REF0[12]=[A-Z0-9]+", text, flags=re.I):
        tokens.append(match.upper())
    for match in re.findall(r"NM10[89]", text, flags=re.I):
        tokens.append(match.upper())
    for match in re.findall(r"ISA0[678]", text, flags=re.I):
        tokens.append(match.upper())
    for match in re.findall(r"GS0[23]", text, flags=re.I):
        tokens.append(match.upper())
    for phrase in (
        "EMPLOYER IDENTIFICATION",
        "FIRST OCCURRENCE",
        "TRAILING SPACES",
        "line level",
        "paid amounts",
        "Paid Amount",
        "MN DEPT OF HUMAN SERVICES",
        "41-1674742",
        "411674742",
        "ABK",
        "ABF",
        "CLM05",
        "VOID",
        "Original",
    ):
        if phrase.lower() in text.lower():
            tokens.append(phrase)
    return tokens


def _search_terms(citation: str, rule_id: str) -> list[str]:
    terms: list[str] = []
    for match in re.findall(r"'([^']{4,})'", citation):
        terms.extend(_tokens_from_quote(match))
        # Also try a medium substring without ellipsis gaps.
        compact = re.sub(r"\s+", " ", match).strip()
        if 12 <= len(compact) <= 48:
            terms.append(compact)
    if "--" in citation:
        terms.extend(_tokens_from_quote(citation.split("--", 1)[1]))
    fallback = {
        "L3-BILLING-TIN-REQUIRED": ["EMPLOYER IDENTIFICATION", "REF01", "EI"],
        "L3-BILLING-UMPI-REQUIRED": ["REF01=G2", "UMPI", "G2"],
        "L3-MCO-ADJUDICATION-REQUIRED": ["2320", "FIRST OCCURRENCE", "MCO"],
        "L3-PAYER-NAME-FIXED": ["MN DEPT OF HUMAN SERVICES", "411674742"],
        "L3-LINE-PAID-AMOUNT-REQUIRED-837P": ["837P", "line level", "paid amounts"],
        "L3-LINE-PAID-AMOUNT-REQUIRED-837I": ["837I", "line level", "paid amounts", "9D", "9C"],
        "L3-837I-AMOUNT-REF-PLACEMENT": ["9A", "9B", "9C", "9D", "line level"],
        "L1-ONE-ISA-PER-FILE": ["ONE INTERCHANGE PER FILE"],
        "L3-SENDER-ID-MATCHES-SUBMITTER": ["ISA06", "GS02", "TRAILING SPACES"],
        "L3-ISA-RECEIVER-FIXED": ["ISA07", "ISA08", "41-1674742", "GS03"],
        "L3-DIAGNOSIS-PRINCIPAL-QUALIFIER": ["ABK", "PRINCIPAL DIAGNOSIS"],
        "L3-DIAGNOSIS-SUBSEQUENT-QUALIFIER": ["ABF", "OTHER DIAGNOSIS"],
        "L3-CLM05-3-FREQUENCY-CODE-DOCUMENTED": ["CLM05", "Void", "Original"],
    }
    terms.extend(fallback.get(rule_id, []))
    # De-dupe preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        key = term.upper()
        if key not in seen and len(term) >= 3:
            seen.add(key)
            out.append(term)
    return out[:6]


def _pdf_page_indices(doc, page_1_indexed: int) -> list[int]:
    """Citation pages are usually printed page numbers; allow small offset."""
    candidates = [page_1_indexed + offset for offset in (-2, -1, 0, 1, 2)]
    valid = [i for i in candidates if 0 <= i < doc.page_count]
    return valid


def _highlight_on_page(page, rect, rule_id: str, note: str) -> None:
    annot = page.add_highlight_annot(rect)
    annot.set_info(title=rule_id, content=note[:500])
    annot.set_colors(stroke=(1, 1, 0))
    annot.update()


def _collect_jobs() -> list[dict]:
    jobs: list[dict] = []
    for registry in (LAYER1, LAYER3):
        for rule in registry.rules():
            if not rule.source_citation or "dhs_837" not in rule.source_citation.lower():
                continue
            jobs.append(
                {
                    "rule_id": rule.rule_id,
                    "pages": _pages_1_indexed(rule.source_citation),
                    "terms": _search_terms(rule.source_citation, rule.rule_id),
                    "citation": rule.source_citation,
                }
            )
    for extra in EXTRA_HIGHLIGHTS:
        jobs.append(
            {
                "rule_id": extra["rule_id"],
                "pages": _pages_1_indexed(extra["source_citation"]),
                "terms": extra["terms"],
                "citation": extra["source_citation"],
            }
        )
    return jobs


def main() -> int:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Install PyMuPDF: pip install pymupdf", file=sys.stderr)
        return 1

    if not SRC_PDF.is_file():
        print(f"Missing source PDF: {SRC_PDF}", file=sys.stderr)
        return 1

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(SRC_PDF)
    stats = {"rules": 0, "highlights": 0, "misses": []}

    for job in _collect_jobs():
        if not job["pages"] or not job["terms"]:
            stats["misses"].append((job["rule_id"], "no pages or search terms"))
            continue
        rule_hits = 0
        for page_num in job["pages"]:
            for page_idx in _pdf_page_indices(doc, page_num):
                page = doc[page_idx]
                for term in job["terms"]:
                    rects = page.search_for(term, flags=fitz.TEXT_DEHYPHENATE)
                    if not rects and len(term) > 20:
                        rects = page.search_for(term[:20], flags=fitz.TEXT_DEHYPHENATE)
                    for rect in rects:
                        _highlight_on_page(page, rect, job["rule_id"], job["citation"])
                        rule_hits += 1
        if rule_hits:
            stats["rules"] += 1
            stats["highlights"] += rule_hits
        else:
            stats["misses"].append((job["rule_id"], f"no matches on pages {job['pages']}"))

    doc.save(OUT_PDF, deflate=True, garbage=4)
    doc.close()

    print(f"Wrote {OUT_PDF.relative_to(ROOT)}")
    print(f"Rules highlighted: {stats['rules']}, highlight rects: {stats['highlights']}")
    if stats["misses"]:
        print("No highlight found for:")
        for rule_id, reason in stats["misses"]:
            print(f"  - {rule_id}: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
