import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import metrics as m
import theme
from app_state import render_data_sidebar

st.set_page_config(page_title="Portfolio Analysis", page_icon="🧩", layout="wide")
theme.register_plotly_theme()
st.markdown(theme.inject_css(), unsafe_allow_html=True)

st.sidebar.title("📊 Investment Dashboard")
txn, div, prices = render_data_sidebar()
if txn.empty or prices.empty:
    st.warning("No data available.")
    st.stop()

as_of = min(txn["Date"].max(), prices["Date"].max())
st.title("Portfolio Analysis")
st.caption(f"As of {as_of.strftime('%d %b %Y')}")

alloc = m.portfolio_allocation(txn, prices, as_of)
contrib = m.contribution_by_stock(txn, prices, div)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Allocation Treemap")
    fig = px.treemap(
        alloc, path=["Ticker"], values="MarketValue",
        color="AllocationPct", color_continuous_scale=["#FF4B4B", "#F2C94C", "#00C896"],
    )
    fig.update_layout(height=400, margin=dict(t=30, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Allocation Share (%)")
    fig2 = px.bar(
        alloc.sort_values("AllocationPct"), x="AllocationPct", y="Ticker",
        orientation="h", color_discrete_sequence=[theme.COLORS["blue"]],
    )
    fig2.update_layout(height=400, xaxis_tickformat=".0%", xaxis_title="", yaxis_title="")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

col3, col4 = st.columns(2)
with col3:
    st.subheader("Risk vs Return (Bubble Chart)")
    bubble_rows = []
    for t in alloc["Ticker"]:
        sub_txn = txn[txn["Ticker"] == t]
        sub_prices = prices[prices["Ticker"] == t]
        avg_cost = m.average_buy_price(txn, t)
        cur_price = m.latest_price(prices, t, as_of)
        profit_pct_t = (cur_price - avg_cost) / avg_cost if avg_cost else None
        # simple per-stock volatility proxy from its own price series returns
        p = sub_prices.sort_values("Date").set_index("Date")["ClosePrice"].pct_change().dropna()
        vol = p.std() * (252 ** 0.5) if not p.empty else None
        mv_t = alloc.set_index("Ticker").loc[t, "MarketValue"]
        bubble_rows.append({"Ticker": t, "Volatility": vol, "ProfitPct": profit_pct_t, "MarketValue": mv_t})
    bubble_df = pd.DataFrame(bubble_rows).dropna()
    fig3 = px.scatter(
        bubble_df, x="Volatility", y="ProfitPct", size="MarketValue", color="Ticker",
        color_discrete_sequence=theme.CATEGORICAL_PALETTE, size_max=60,
        labels={"Volatility": "Volatility (annualized)", "ProfitPct": "Profit %"},
    )
    fig3.update_layout(height=380, yaxis_tickformat=".0%", xaxis_tickformat=".0%")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Top / Bottom Contributors")
    top_n = contrib.head(3).copy()
    bottom_n = contrib.tail(3).copy()
    combined = pd.concat([top_n, bottom_n]).drop_duplicates(subset="Ticker")
    colors = [theme.COLORS["green"] if v >= 0 else theme.COLORS["red"] for v in combined["Profit"]]
    fig4 = go.Figure(go.Bar(x=combined["Profit"], y=combined["Ticker"], orientation="h", marker_color=colors))
    fig4.update_layout(height=380, xaxis_title="Profit Contribution (₫)")
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")
st.subheader("Profit Contribution Waterfall")
waterfall_df = contrib.sort_values("Profit", ascending=False)
fig5 = go.Figure(go.Waterfall(
    x=list(waterfall_df["Ticker"]) + ["Total"],
    y=list(waterfall_df["Profit"]) + [0],
    measure=["relative"] * len(waterfall_df) + ["total"],
    increasing=dict(marker=dict(color=theme.COLORS["green"])),
    decreasing=dict(marker=dict(color=theme.COLORS["red"])),
    totals=dict(marker=dict(color=theme.COLORS["blue"])),
))
fig5.update_layout(height=380)
st.plotly_chart(fig5, use_container_width=True)
