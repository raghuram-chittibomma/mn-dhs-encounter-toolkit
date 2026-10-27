"""Bridge from the web UI to the standalone EDI HTML renderer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_MODULE: ModuleType | None = None


def render_edi_html(text: str, filename: str, findings: list[dict] | None = None) -> str:
    module = _renderer()
    return module.render_html(text, filename=filename, findings=findings)


def _renderer() -> ModuleType:
    global _MODULE
    if _MODULE is not None:
        return _MODULE
    script = Path(__file__).resolve().parents[3] / "scripts" / "render_edi_html.py"
    if not script.is_file():
        raise FileNotFoundError(f"EDI HTML renderer not found at {script}")
    spec = importlib.util.spec_from_file_location("render_edi_html", script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load EDI HTML renderer from {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["render_edi_html"] = module
    spec.loader.exec_module(module)
    _MODULE = module
    return module
