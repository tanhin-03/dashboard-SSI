import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import metrics as m
import theme
from app_state import render_data_sidebar

st.set_page_config(page_title="Performance Analysis", page_icon="📈", layout="wide")
theme.register_plotly_theme()
st.markdown(theme.inject_css(), unsafe_allow_html=True)

st.sidebar.title("📊 Investment Dashboard")
txn, div, prices = render_data_sidebar()
if txn.empty or prices.empty:
    st.warning("No data available.")
    st.stop()

as_of = min(txn["Date"].max(), prices["Date"].max())
st.title("Performance Analysis")
st.caption(f"As of {as_of.strftime('%d %b %Y')}")

ts = m.build_daily_timeseries(txn, prices, div)
ti = m.total_investment(txn)

window = st.select_slider("Rolling window (days)", options=[7, 30, 90, 180, 365], value=30)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rolling Return", theme.fmt_pct(m.rolling_return(ts, window).iloc[-1] if len(ts) > window else float("nan")))
c2.metric("CAGR", theme.fmt_pct(m.cagr(ts, ti)))
c3.metric("Volatility (annualized)", theme.fmt_pct(m.volatility(ts)))
c4.metric("Max Drawdown", theme.fmt_pct(m.max_drawdown(ts)))

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.subheader(f"Monthly / Quarterly / Yearly Return")
    period_choice = st.radio("Granularity", ["Monthly", "Quarterly", "Yearly"], horizontal=True)
    freq_map = {"Monthly": "ME", "Quarterly": "QE", "Yearly": "YE"}
    resampled = ts.set_index("Date")["PortfolioValue"].resample(freq_map[period_choice]).last()
    returns = resampled.pct_change().dropna() * 100
    colors = [theme.COLORS["green"] if v >= 0 else theme.COLORS["red"] for v in returns]
    fig = go.Figure(go.Bar(x=returns.index.strftime("%Y-%m"), y=returns.values, marker_color=colors))
    fig.update_layout(height=360, yaxis_title="Return %")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Rolling Return & Moving Average")
    roll = m.rolling_return(ts, window) * 100
    mavg = m.moving_average(ts, window)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=roll.index, y=roll.values, name=f"{window}D Rolling Return (%)",
                               line=dict(color=theme.COLORS["gold"])))
    fig2.update_layout(height=360, yaxis_title="Rolling Return %")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")
st.subheader("Portfolio Value with Moving Average")
mavg_full = m.moving_average(ts, window)
fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=ts["Date"], y=ts["PortfolioValue"], name="Portfolio Value",
                           line=dict(color=theme.COLORS["blue"], width=1.5)))
fig3.add_trace(go.Scatter(x=mavg_full.index, y=mavg_full.values, name=f"{window}D Moving Average",
                           line=dict(color=theme.COLORS["gold"], width=2, dash="dot")))
fig3.update_layout(height=380)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
st.subheader("Drawdown Analysis")
running_peak = ts.set_index("Date")["PortfolioValue"].cummax()
drawdown = (ts.set_index("Date")["PortfolioValue"] - running_peak) / running_peak * 100
fig4 = go.Figure(go.Scatter(x=drawdown.index, y=drawdown.values, fill="tozeroy",
                             line=dict(color=theme.COLORS["red"]), fillcolor="rgba(255,75,75,0.15)"))
fig4.update_layout(height=320, yaxis_title="Drawdown %")
st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")
st.subheader("Performance Table by Stock")
rows = []
for t in txn["Ticker"].dropna().unique():
    avg_cost = m.average_buy_price(txn, t)
    cur_price = m.latest_price(prices, t, as_of)
    shares = m.current_shares(txn, as_of).get(t, 0)
    if shares == 0:
        continue
    profit_pct_t = (cur_price - avg_cost) / avg_cost if avg_cost else float("nan")
    rows.append({"Ticker": t, "Shares": shares, "Avg Cost": avg_cost, "Current Price": cur_price,
                 "Profit %": profit_pct_t})
perf_df = pd.DataFrame(rows).sort_values("Profit %", ascending=False)
perf_df["Avg Cost"] = perf_df["Avg Cost"].apply(theme.fmt_vnd)
perf_df["Current Price"] = perf_df["Current Price"].apply(theme.fmt_vnd)
perf_df["Profit %"] = perf_df["Profit %"].apply(theme.fmt_pct)
st.dataframe(perf_df, use_container_width=True, hide_index=True)
