#!/usr/bin/env python3
"""Record a black-box test execution result under qa-uat/results/executions/."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Record QA/UAT execution result")
    parser.add_argument("--case", required=True, help="Test case ID, e.g. TC-QA-001")
    parser.add_argument(
        "--status",
        required=True,
        choices=["pass", "fail", "blocked", "not_run"],
    )
    parser.add_argument("--notes", default="", help="Free-text notes")
    parser.add_argument(
        "--artifact",
        default="",
        help="Path to validate JSON or other output (relative to repo root)",
    )
    parser.add_argument(
        "--executor",
        default="",
        help="Who ran the test",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "results" / "executions"
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    record = {
        "case_id": args.case,
        "status": args.status,
        "notes": args.notes,
        "artifact": args.artifact,
        "executor": args.executor,
        "recorded_at": ts,
    }
    out_file = out_dir / f"{args.case}_{ts}.json"
    out_file.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_file.relative_to(root.parent)}")


if __name__ == "__main__":
    main()
