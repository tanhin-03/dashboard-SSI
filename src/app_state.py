"""
app_state.py
Shared sidebar controls for data source selection, used identically on every page
so the same transaction/dividend/price data is available across the whole app.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import data_loader as dl

SAMPLE_TXN = os.path.join(os.path.dirname(__file__), "..", "data", "sample_transactions.csv")
SAMPLE_DIV = os.path.join(os.path.dirname(__file__), "..", "data", "sample_dividends.csv")
SAMPLE_PRICES = os.path.join(os.path.dirname(__file__), "..", "data", "sample_prices.csv")


def render_data_sidebar():
    """Renders the sidebar data source picker and returns cleaned (txn, div, prices) DataFrames."""
    st.sidebar.markdown("### 📁 Data Source")
    use_sample = st.sidebar.toggle("Use sample data", value=True,
                                    help="Turn off to upload your own SSI export CSVs")

    if use_sample:
        txn = dl.load_transactions(SAMPLE_TXN)
        div = dl.load_dividends(SAMPLE_DIV)
        prices = dl.load_prices(SAMPLE_PRICES)
        st.sidebar.caption("Using bundled sample data (fictional).")
    else:
        txn_file = st.sidebar.file_uploader("Transactions CSV (SSI export)", type=["csv"], key="txn_upload")
        div_file = st.sidebar.file_uploader("Dividends CSV", type=["csv"], key="div_upload")
        price_file = st.sidebar.file_uploader("Price history CSV", type=["csv"], key="price_upload")

        if not (txn_file and div_file and price_file):
            st.sidebar.warning("Upload all 3 files, or switch back to sample data.")
            st.info("👈 Upload your Transactions, Dividends, and Price history CSVs in the sidebar to see your real portfolio, or turn 'Use sample data' back on.")
            st.stop()

        txn = dl.load_transactions(txn_file)
        div = dl.load_dividends(div_file)
        prices = dl.load_prices(price_file)
        st.sidebar.success("Custom data loaded.")

    st.sidebar.markdown("---")
    st.sidebar.caption("💡 Column mapping expected: see `data/README.md` for the exact SSI export format.")

    return txn, div, prices
