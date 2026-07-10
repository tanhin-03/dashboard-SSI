import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import metrics as m
import theme
from app_state import render_data_sidebar

st.set_page_config(page_title="Dividend Dashboard", page_icon="💰", layout="wide")
theme.register_plotly_theme()
st.markdown(theme.inject_css(), unsafe_allow_html=True)

st.sidebar.title("📊 Investment Dashboard")
txn, div, prices = render_data_sidebar()
if div.empty:
    st.info("No dividend records found in the current data.")
    st.stop()

as_of = min(txn["Date"].max(), prices["Date"].max())
st.title("Dividend Dashboard")
st.caption(f"As of {as_of.strftime('%d %b %Y')}")

total_div = m.dividend_income(div, as_of=as_of)
yoy = m.dividend_growth_yoy(div, as_of)
mv = m.market_value(txn, prices, as_of)
yld = total_div / mv if mv else float("nan")

c1, c2, c3 = st.columns(3)
c1.metric("Total Dividend Received", theme.fmt_vnd(total_div))
c2.metric("Dividend Growth (YoY)", theme.fmt_pct(yoy))
c3.metric("Portfolio Dividend Yield", theme.fmt_pct(yld))

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Dividend Timeline")
    div_by_month = div.set_index("Date")["DividendAmount"].resample("ME").sum()
    cum_div = div_by_month.cumsum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=div_by_month.index, y=div_by_month.values, name="Monthly",
                          marker_color=theme.COLORS["blue"]))
    fig.add_trace(go.Scatter(x=cum_div.index, y=cum_div.values, name="Cumulative",
                              yaxis="y2", line=dict(color=theme.COLORS["green"], width=2)))
    fig.update_layout(
        height=380,
        yaxis=dict(title="Monthly (₫)"),
        yaxis2=dict(title="Cumulative (₫)", overlaying="y", side="right"),
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Dividend by Stock")
    div_by_stock = div.groupby("Ticker")["DividendAmount"].sum().reset_index().sort_values("DividendAmount")
    fig2 = px.bar(div_by_stock, x="DividendAmount", y="Ticker", orientation="h",
                  color_discrete_sequence=[theme.COLORS["gold"]])
    fig2.update_layout(height=380, xaxis_title="Total Dividend (₫)")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

col3, col4 = st.columns(2)
with col3:
    st.subheader("Yield Analysis by Stock")
    yield_rows = []
    for t in div["Ticker"].unique():
        mv_t = m.market_value_by_stock(txn, prices, as_of).set_index("Ticker")["MarketValue"].get(t, 0)
        div_t = m.dividend_income(div, t, as_of)
        yield_rows.append({"Ticker": t, "Yield": div_t / mv_t if mv_t else 0})
    yield_df = pd.DataFrame(yield_rows).sort_values("Yield")
    fig3 = px.bar(yield_df, x="Yield", y="Ticker", orientation="h",
                  color_discrete_sequence=[theme.COLORS["purple"]])
    fig3.update_layout(height=340, xaxis_tickformat=".1%")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Projected Dividend (Next 12M)")
    last_12m = div[div["Date"] > as_of - pd.Timedelta(days=365)]["DividendAmount"].sum()
    st.metric("Naive run-rate projection", theme.fmt_vnd(last_12m))
    st.caption("Simple projection: assumes next 12 months mirrors trailing 12 months of dividend cash received. "
               "For a more precise estimate, weight by current shares held × last known dividend-per-share.")
