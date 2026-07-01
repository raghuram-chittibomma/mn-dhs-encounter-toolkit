"""Launch the Streamlit validation UI."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    import streamlit.web.cli as stcli

    app_path = Path(__file__).resolve().parents[3] / "ui" / "app.py"
    sys.argv = ["streamlit", "run", str(app_path), "--server.headless", "true"]
    sys.exit(stcli.main())
