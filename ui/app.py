"""MN DHS Encounter Toolkit — web UI entry point.

Run with:
    streamlit run ui/app.py
or:
    mn-encounter-ui
"""

from __future__ import annotations

import streamlit as st

from mn_encounter_toolkit.web.views import (
    page_gen835e,
    page_gen999,
    page_scenario_lab,
    page_validate,
    page_validation_layers,
)

st.set_page_config(
    page_title="MN DHS Encounter Toolkit",
    page_icon="📋",
    layout="wide",
)

PAGES = {
    "Validate 837": page_validate,
    "Validation layers": page_validation_layers,
    "Generate 999": page_gen999,
    "Generate 835E": page_gen835e,
    "Scenario lab": page_scenario_lab,
}


def main() -> None:
    st.sidebar.title("MN DHS Encounter")
    st.sidebar.caption(
        "Runs locally on your machine. Files are processed in memory only—"
        "nothing is stored on disk or sent over the internet."
    )
    choice = st.sidebar.radio("Go to", list(PAGES.keys()))
    PAGES[choice]()


if __name__ == "__main__":
    main()
