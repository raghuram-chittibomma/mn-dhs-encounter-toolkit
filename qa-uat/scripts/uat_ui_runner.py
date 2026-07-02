#!/usr/bin/env python3
"""Black-box UAT runner for Streamlit UI at localhost:8501."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
QA_UAT = ROOT / "qa-uat"
INPUTS = QA_UAT / "test-data" / "inputs"
RESULTS = QA_UAT / "results" / "executions"
BASE_URL = "http://localhost:8501"


def _wait_ready(page) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)


def _ensure_sidebar(page) -> None:
    expand = page.locator('button[data-testid="stExpandSidebarButton"]')
    if expand.count():
        expand.click()
        page.wait_for_timeout(500)


def _select_page(page, label: str) -> None:
    _ensure_sidebar(page)
    label_loc = page.locator("section[data-testid='stSidebar'] label").filter(has_text=label)
    if label_loc.count():
        label_loc.first.click(force=True)
    else:
        page.get_by_text(label, exact=True).first.click(force=True)
    _wait_ready(page)


def _upload_837(page, file_path: Path) -> None:
    page.locator('input[type="file"]').first.set_input_files(str(file_path))
    _wait_ready(page)
    page.wait_for_timeout(2500)


def _page_text(page) -> str:
    return page.locator("body").inner_text()


def _metric_value(text: str, label: str) -> int | None:
    m = re.search(rf"{re.escape(label)}\s+(\d+)", text, re.I)
    return int(m.group(1)) if m else None


def _download_button(page, label: str, out_path: Path) -> bool:
    btn = page.get_by_role("button", name=re.compile(re.escape(label), re.I))
    if not btn.count():
        return False
    with page.expect_download(timeout=20000) as dl_info:
        btn.first.click(force=True)
    dl_info.value.save_as(str(out_path))
    return out_path.exists() and out_path.stat().st_size > 0


def run_uat_001(page) -> dict:
    _select_page(page, "Validate 837")
    _upload_837(page, INPUTS / "qa_clean_mixed_seed42.x12")
    text = _page_text(page)
    errors = _metric_value(text, "Errors")
    out_json = RESULTS / "TC-UAT-001_ui.json"
    exported = _download_button(page, "Download JSON report", out_json)
    if not exported:
        out_csv = RESULTS / "TC-UAT-001_ui.csv"
        exported = _download_button(page, "Download CSV report", out_csv)
    privacy = "processed in memory" in text.lower() or "nothing is stored" in text.lower()
    clean = errors == 0 and "no error-level findings" in text.lower()
    return {
        "case": "TC-UAT-001",
        "status": "pass" if clean and privacy else "fail",
        "errors": errors,
        "exported_json": out_json.exists(),
        "privacy_caption": privacy,
        "artifact": str((out_json if out_json.exists() else RESULTS / "TC-UAT-001_ui.csv").relative_to(ROOT))
        if exported
        else "",
        "notes": (
            f"errors={errors}, clean={clean}, privacy={privacy}; "
            "JSON export only offered when findings exist — used CSV/claims export for clean batch"
            if not out_json.exists()
            else f"errors={errors}, json_export=True, privacy={privacy}"
        ),
    }


def run_uat_002(page) -> dict:
    _select_page(page, "Validate 837")
    _upload_837(page, INPUTS / "qa_err_missing_umpi_seed42.x12")
    text = _page_text(page)
    errors = _metric_value(text, "Errors")
    has_umpi = bool(re.search(r"UMPI|REF\*G2|billing provider.*missing", text, re.I))
    has_citation = bool(re.search(r"companion_guide|guide\.pdf|p\.\d+", text, re.I))
    out_json = RESULTS / "TC-UAT-002_ui.json"
    exported = _download_button(page, "Download JSON report", out_json)
    return {
        "case": "TC-UAT-002",
        "status": "pass" if errors and errors > 0 and has_umpi and has_citation else "fail",
        "errors": errors,
        "umpi_finding": has_umpi,
        "guide_citation": has_citation,
        "artifact": str(out_json.relative_to(ROOT)) if exported else "",
        "notes": f"errors={errors}, umpi={has_umpi}, citation={has_citation}, json={exported}",
    }


def _generate_then_download(page, generate_label: str, download_label: str, out_path: Path) -> bool:
    page.get_by_role("button", name=generate_label).click(force=True)
    page.wait_for_timeout(3000)
    return _download_button(page, download_label, out_path)


def run_uat_003(page) -> dict:
    _select_page(page, "Generate 999")
    page.locator('input[type="file"]').first.set_input_files(
        str(INPUTS / "qa_clean_mixed_seed42.x12")
    )
    _wait_ready(page)
    out = INPUTS / "uat_999_from_ui_seed42.x12"
    downloaded = _generate_then_download(page, "Generate 999", "Download 999 file", out)
    return {
        "case": "TC-UAT-003",
        "status": "pass" if downloaded else "fail",
        "artifact": str(out.relative_to(ROOT)) if downloaded else "",
        "notes": f"downloaded={downloaded}, local_preview_only=True",
    }


def run_uat_004(page) -> dict:
    _select_page(page, "Generate 835E")
    page.locator('input[type="file"]').first.set_input_files(
        str(INPUTS / "qa_clean_mixed_seed42.x12")
    )
    _wait_ready(page)
    out = INPUTS / "uat_835e_from_ui_seed42.x12"
    downloaded = _generate_then_download(page, "Generate 835E", "Download 835E file", out)
    content_ok = False
    if downloaded:
        body = out.read_text(encoding="utf-8", errors="ignore")
        content_ok = "CLP" in body and "SVC" in body
    return {
        "case": "TC-UAT-004",
        "status": "pass" if downloaded and content_ok else "fail",
        "artifact": str(out.relative_to(ROOT)) if downloaded else "",
        "notes": f"downloaded={downloaded}, clp_svc={content_ok}, local_echo_only=True",
    }


def run_uat_005(page) -> dict:
    _select_page(page, "Scenario lab")
    page.locator("[data-baseweb=select]").first.click(force=True)
    page.wait_for_timeout(500)
    page.get_by_role("option", name="epsdt_teen_checkup").click(force=True)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    seed_input = page.locator("section[data-testid='stMain'] input[type='number']").first
    if seed_input.count():
        seed_input.fill("99")
    out = INPUTS / "uat_scenario_lab_seed99.x12"
    downloaded = _generate_then_download(page, "Generate 837 batch", "Download 837 file", out)
    validate_status = "not_run"
    if downloaded:
        _select_page(page, "Validate 837")
        _upload_837(page, out)
        vtext = _page_text(page)
        validate_status = "pass" if _metric_value(vtext, "Errors") == 0 else "fail"
    return {
        "case": "TC-UAT-005",
        "status": "pass" if downloaded and validate_status == "pass" else "fail",
        "artifact": str(out.relative_to(ROOT)) if downloaded else "",
        "notes": f"scenario=epsdt_teen_checkup seed=99 downloaded={downloaded} validate={validate_status}",
    }


def run_uat_006(page) -> dict:
    _select_page(page, "Validate 837")
    _upload_837(page, INPUTS / "qa_void_encounter_seed42.x12")
    text = _page_text(page)
    errors = _metric_value(text, "Errors")
    file_body = (INPUTS / "qa_void_encounter_seed42.x12").read_text(encoding="utf-8", errors="ignore")
    has_void = "CLM05-3=8" in file_body or ":8:" in file_body or "REF*F8" in file_body
    return {
        "case": "TC-UAT-006",
        "status": "pass" if errors == 0 else "fail",
        "errors": errors,
        "void_icn_in_file": has_void,
        "notes": f"errors={errors}, void_icn_segments={has_void}",
    }


def run_uat_007(page) -> dict:
    _select_page(page, "Validate 837")
    _upload_837(page, INPUTS / "qa_professional_tpl_seed42.x12")
    text = _page_text(page)
    errors = _metric_value(text, "Errors")
    file_body = (INPUTS / "qa_professional_tpl_seed42.x12").read_text(encoding="utf-8", errors="ignore")
    has_tpl = "SBR*P" in file_body or "SBR01*P" in file_body
    return {
        "case": "TC-UAT-007",
        "status": "pass" if errors == 0 and has_tpl else "fail",
        "errors": errors,
        "tpl_structure": has_tpl,
        "notes": f"errors={errors}, tpl_cob_structure={has_tpl}",
    }


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    runners = [
        run_uat_001,
        run_uat_002,
        run_uat_003,
        run_uat_004,
        run_uat_005,
        run_uat_006,
        run_uat_007,
    ]
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 2000})
        page.goto(BASE_URL)
        _wait_ready(page)
        for runner in runners:
            try:
                results.append(runner(page))
            except Exception as exc:
                case_id = re.search(r"run_uat_(\d+)", runner.__name__)
                cid = f"TC-UAT-{case_id.group(1).zfill(3)}" if case_id else runner.__name__
                results.append({"case": cid, "status": "fail", "notes": f"exception: {exc}"})
        browser.close()

    out_file = RESULTS / "TC-UAT_ui_batch_results.json"
    out_file.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0 if all(r.get("status") == "pass" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
