"""MN DHS Encounter Toolkit — web UI entry point.

Run with:
    streamlit run ui/app.py
or:
    mn-encounter-ui
"""

from __future__ import annotations

import streamlit as st

from mn_encounter_toolkit.web.views import page_gen835e, page_gen999, page_scenario_lab, page_validate

st.set_page_config(
    page_title="MN DHS Encounter Toolkit",
    page_icon="📋",
    layout="wide",
)

PAGES = {
    "Validate 837": page_validate,
    "Generate 999": page_gen999,
    "Generate 835E": page_gen835e,
    "Scenario lab": page_scenario_lab,
}


def main() -> None:
    st.sidebar.title("MN DHS Encounter")
    st.sidebar.caption("Files are processed in memory and are not stored on disk.")
    choice = st.sidebar.radio("Go to", list(PAGES.keys()))
    PAGES[choice]()


if __name__ == "__main__":
    main()
