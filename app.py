from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_productivity_hub.config import AppConfig, load_config
from ai_productivity_hub.views import render_app


def main() -> None:
    st.set_page_config(
        page_title="AI Productivity Hub",
        page_icon="AI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    config: AppConfig = load_config()
    render_app(config)


if __name__ == "__main__":
    main()
