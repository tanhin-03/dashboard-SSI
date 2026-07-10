"""
app.py — Executive Summary (Page 1)
Run with: streamlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import metrics as m
import theme
from app_state import render_data_sidebar

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Portfolio Overview | Investment Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.register_plotly_theme()
st.markdown(theme.inject_css(), unsafe_allow_html=True)

st.sidebar.title("📊 Investment Dashboard")
st.sidebar.caption("Personal portfolio analytics — built with Python & Streamlit")
txn, div, prices = render_data_sidebar()

if txn.empty or prices.empty:
    st.warning("No transaction or price data available.")
    st.stop()

as_of = min(txn["Date"].max(), prices["Date"].max())

st.title("Portfolio Overview")
st.caption(f"As of {as_of.strftime('%d %b %Y')}")

# ---------------------------------------------------------------------------
# Compute core metrics
# ---------------------------------------------------------------------------
ti = m.total_investment(txn)
mv = m.market_value(txn, prices, as_of)
cash = m.cash_balance(txn, div, as_of)
pv = mv + cash
profit = m.total_profit(txn, prices, div)
profit_pct = m.profit_pct(txn, prices, div)
div_income = m.dividend_income(div, as_of=as_of)
ts = m.build_daily_timeseries(txn, prices, div)
cagr_val = m.cagr(ts, ti)
roi = profit_pct

# ---------------------------------------------------------------------------
# KPI Row
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Investment", theme.fmt_vnd(ti))
c2.metric("Portfolio Value", theme.fmt_vnd(pv))
c3.metric("Profit / Loss", theme.fmt_vnd(profit), delta=theme.fmt_pct(profit_pct))
c4.metric("Profit %", theme.fmt_pct(profit_pct))

c5, c6, c7, c8 = st.columns(4)
c5.metric("Dividend Received", theme.fmt_vnd(div_income))
c6.metric("CAGR", theme.fmt_pct(cagr_val))
c7.metric("ROI", theme.fmt_pct(roi))
c8.metric("Cash Balance", theme.fmt_vnd(cash))

st.markdown("---")

# ---------------------------------------------------------------------------
# Portfolio Value Over Time + Asset Allocation
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Portfolio Value Over Time")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ts["Date"], y=ts["PortfolioValue"],
        mode="lines", fill="tozeroy",
        line=dict(color=theme.COLORS["green"], width=2),
        fillcolor="rgba(0,200,150,0.12)",
        name="Portfolio Value",
    ))
    fig.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Asset Allocation")
    alloc = m.portfolio_allocation(txn, prices, as_of)
    fig2 = px.pie(alloc, names="Ticker", values="MarketValue", hole=0.55,
                  color_discrete_sequence=theme.CATEGORICAL_PALETTE)
    fig2.update_traces(textinfo="label+percent")
    fig2.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Monthly Performance + Top Holdings
# ---------------------------------------------------------------------------
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Monthly Performance")
    monthly = ts.set_index("Date")["PortfolioValue"].resample("ME").last()
    monthly_ret = monthly.pct_change().dropna() * 100
    colors = [theme.COLORS["green"] if v >= 0 else theme.COLORS["red"] for v in monthly_ret]
    fig3 = go.Figure(go.Bar(
        x=monthly_ret.index.strftime("%b %Y"), y=monthly_ret.values,
        marker_color=colors,
    ))
    fig3.update_layout(height=340, yaxis_title="Return %")
    st.plotly_chart(fig3, use_container_width=True)

with col_b:
    st.subheader("Top Holdings")
    top_holdings = alloc.sort_values("MarketValue", ascending=True).tail(8)
    fig4 = go.Figure(go.Bar(
        x=top_holdings["MarketValue"], y=top_holdings["Ticker"],
        orientation="h", marker_color=theme.COLORS["blue"],
    ))
    fig4.update_layout(height=340, xaxis_title="Market Value (₫)")
    st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------------------------
# Recent Transactions
# ---------------------------------------------------------------------------
st.subheader("Recent Transactions")
recent = txn.sort_values("Date", ascending=False).head(10)[
    ["Date", "Ticker", "TransactionType", "Quantity", "Price", "Fees", "Tax", "TotalAmount"]
].copy()
recent["Date"] = recent["Date"].dt.strftime("%Y-%m-%d")
for col in ["Price", "Fees", "Tax", "TotalAmount"]:
    recent[col] = recent[col].apply(lambda v: theme.fmt_vnd(v) if pd.notna(v) else "—")
st.dataframe(recent, use_container_width=True, hide_index=True)

st.caption("Navigate to the other pages via the sidebar: Portfolio Analysis, Performance, Dividends, "
           "Transaction History, Stock Detail, Risk Dashboard.")
