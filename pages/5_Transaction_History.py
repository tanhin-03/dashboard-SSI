import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.express as px

import theme
from app_state import render_data_sidebar

st.set_page_config(page_title="Transaction History", page_icon="🧾", layout="wide")
theme.register_plotly_theme()
st.markdown(theme.inject_css(), unsafe_allow_html=True)

st.sidebar.title("📊 Investment Dashboard")
txn, div, prices = render_data_sidebar()
if txn.empty:
    st.warning("No transaction data available.")
    st.stop()

st.title("Transaction History")

# --- Filters ---
col1, col2, col3 = st.columns(3)
with col1:
    date_range = st.date_input(
        "Date range",
        value=(txn["Date"].min().date(), txn["Date"].max().date()),
    )
with col2:
    tickers = sorted(txn["Ticker"].dropna().unique())
    selected_tickers = st.multiselect("Ticker", tickers, default=tickers)
with col3:
    txn_types = sorted(txn["TransactionType"].unique())
    selected_types = st.multiselect("Transaction Type", txn_types, default=txn_types)

filtered = txn[
    (txn["Date"].dt.date >= date_range[0]) & (txn["Date"].dt.date <= date_range[1]) &
    (txn["TransactionType"].isin(selected_types))
]
filtered = filtered[filtered["Ticker"].isin(selected_tickers) | filtered["Ticker"].isna()]

st.markdown("---")
st.subheader("Interactive Transaction Table")
display_df = filtered.sort_values("Date", ascending=False).copy()
display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
for col in ["Price", "Fees", "Tax", "TotalAmount"]:
    display_df[col] = display_df[col].apply(lambda v: theme.fmt_vnd(v) if pd.notna(v) else "—")
st.dataframe(
    display_df[["Date", "Ticker", "TransactionType", "Quantity", "Price", "Fees", "Tax", "TotalAmount", "BrokerID"]],
    use_container_width=True, hide_index=True, height=350,
)

st.markdown("---")
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Transaction Timeline")
    plot_df = filtered.dropna(subset=["Ticker"])
    fig = px.scatter(
        plot_df, x="Date", y="Ticker", size=plot_df["TotalAmount"].abs(),
        color="TransactionType", color_discrete_map={"Buy": theme.COLORS["blue"], "Sell": theme.COLORS["gold"]},
    )
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Broker Summary")
    broker_summary = txn.groupby("BrokerID").agg(
        Transactions=("TransactionID", "count"),
        TotalFees=("Fees", "sum"),
        TotalTax=("Tax", "sum"),
    ).reset_index()
    broker_summary["TotalFees"] = broker_summary["TotalFees"].apply(theme.fmt_vnd)
    broker_summary["TotalTax"] = broker_summary["TotalTax"].apply(theme.fmt_vnd)
    st.dataframe(broker_summary, use_container_width=True, hide_index=True)

st.markdown("---")
col_c, col_d = st.columns(2)
with col_c:
    st.subheader("Fees Analysis Over Time")
    fees_monthly = txn.set_index("Date")["Fees"].resample("ME").sum()
    fig2 = px.bar(x=fees_monthly.index, y=fees_monthly.values, color_discrete_sequence=[theme.COLORS["red"]])
    fig2.update_layout(height=320, xaxis_title="", yaxis_title="Fees (₫)")
    st.plotly_chart(fig2, use_container_width=True)

with col_d:
    st.subheader("Tax Analysis Over Time")
    tax_monthly = txn.set_index("Date")["Tax"].resample("ME").sum()
    fig3 = px.bar(x=tax_monthly.index, y=tax_monthly.values, color_discrete_sequence=[theme.COLORS["purple"]])
    fig3.update_layout(height=320, xaxis_title="", yaxis_title="Tax (₫)")
    st.plotly_chart(fig3, use_container_width=True)
