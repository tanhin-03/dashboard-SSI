import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

import metrics as m
import theme
from app_state import render_data_sidebar

st.set_page_config(page_title="Risk Dashboard", page_icon="⚠️", layout="wide")
theme.register_plotly_theme()
st.markdown(theme.inject_css(), unsafe_allow_html=True)

st.sidebar.title("📊 Investment Dashboard")
txn, div, prices = render_data_sidebar()
if txn.empty or prices.empty:
    st.warning("No data available.")
    st.stop()

as_of = min(txn["Date"].max(), prices["Date"].max())
st.title("Risk Dashboard")
st.caption(f"As of {as_of.strftime('%d %b %Y')}")

ts = m.build_daily_timeseries(txn, prices, div)
ti = m.total_investment(txn)

div_score = m.diversification_score(txn, prices)
largest_pos = m.largest_position_pct(txn, prices)
vol = m.volatility(ts)
mdd = m.max_drawdown(ts)
sharpe = m.sharpe_ratio(ts, ti)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Diversification Score", f"{div_score:,.0f} / 100" if div_score == div_score else "—")
c2.metric("Largest Position", theme.fmt_pct(largest_pos))
c3.metric("Volatility (annualized)", theme.fmt_pct(vol))
c4.metric("Max Drawdown", theme.fmt_pct(mdd))

c5, c6 = st.columns(2)
c5.metric("Sharpe Ratio", f"{sharpe:.2f}" if sharpe == sharpe else "—")
c6.metric("Number of Holdings", f"{len(m.current_shares(txn, as_of)[m.current_shares(txn, as_of) > 0])}")

st.caption("Note: Risk Score here is a simplified heuristic combining volatility, concentration, and "
           "diversification — not a regulatory or academically validated risk metric. Beta is omitted "
           "since it requires an external market-correlation data source not derivable from transaction history alone.")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Allocation Concentration")
    alloc = m.portfolio_allocation(txn, prices, as_of)
    fig = px.bar(alloc.sort_values("AllocationPct"), x="AllocationPct", y="Ticker", orientation="h",
                 color="AllocationPct", color_continuous_scale=["#00C896", "#F2C94C", "#FF4B4B"])
    fig.update_layout(height=380, xaxis_tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Per-Stock Volatility")
    vol_rows = []
    for t in alloc["Ticker"]:
        p = prices[prices["Ticker"] == t].sort_values("Date").set_index("Date")["ClosePrice"].pct_change().dropna()
        vol_rows.append({"Ticker": t, "Volatility": p.std() * (252 ** 0.5) if not p.empty else None})
    vol_df = pd.DataFrame(vol_rows).dropna().sort_values("Volatility")
    fig2 = px.bar(vol_df, x="Volatility", y="Ticker", orientation="h",
                  color_discrete_sequence=[theme.COLORS["purple"]])
    fig2.update_layout(height=380, xaxis_tickformat=".0%")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("Risk Heatmap — Stock x Volatility Band")
if not vol_df.empty:
    bins = [0, 0.15, 0.30, 0.50, 1, 100]
    labels = ["Low (<15%)", "Moderate (15-30%)", "High (30-50%)", "Very High (50-100%)", "Extreme (>100%)"]
    vol_df["Band"] = pd.cut(vol_df["Volatility"], bins=bins, labels=labels)
    heat = vol_df.pivot_table(index="Ticker", columns="Band", values="Volatility", aggfunc="count", fill_value=0)
    fig3 = px.imshow(heat, color_continuous_scale=["#161B22", "#FF4B4B"], aspect="auto")
    fig3.update_layout(height=320)
    st.plotly_chart(fig3, use_container_width=True)
