import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import metrics as m
import theme
from app_state import render_data_sidebar

st.set_page_config(page_title="Stock Detail", page_icon="🔎", layout="wide")
theme.register_plotly_theme()
st.markdown(theme.inject_css(), unsafe_allow_html=True)

st.sidebar.title("📊 Investment Dashboard")
txn, div, prices = render_data_sidebar()
if txn.empty:
    st.warning("No data available.")
    st.stop()

as_of = min(txn["Date"].max(), prices["Date"].max())
tickers = sorted(txn["Ticker"].dropna().unique())
selected = st.selectbox("Select a stock", tickers)

st.title(f"Stock Detail — {selected}")
st.caption(f"As of {as_of.strftime('%d %b %Y')}")

shares = m.current_shares(txn, as_of).get(selected, 0)
avg_cost = m.average_buy_price(txn, selected)
cur_price = m.latest_price(prices, selected, as_of)
mv = shares * cur_price if cur_price == cur_price else 0
cb = shares * avg_cost if avg_cost == avg_cost else 0
unrealized = mv - cb
realized = m.realized_gain(txn, selected)
div_income = m.dividend_income(div, selected, as_of)
total_profit_stock = unrealized + realized + div_income
profit_pct_stock = total_profit_stock / cb if cb else float("nan")
alloc_pct = mv / m.market_value(txn, prices, as_of) if m.market_value(txn, prices, as_of) else float("nan")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Current Holding", f"{shares:,.0f} shares")
c2.metric("Average Cost", theme.fmt_vnd(avg_cost))
c3.metric("Current Price", theme.fmt_vnd(cur_price))
c4.metric("Profit", theme.fmt_vnd(total_profit_stock))
c5.metric("Profit %", theme.fmt_pct(profit_pct_stock))

c6, c7 = st.columns(2)
c6.metric("Dividend Received", theme.fmt_vnd(div_income))
c7.metric("Allocation % of Portfolio", theme.fmt_pct(alloc_pct))

st.markdown("---")

st.subheader("Price Trend with Buy/Sell Markers")
stock_prices = prices[prices["Ticker"] == selected].sort_values("Date")
stock_txn = txn[txn["Ticker"] == selected]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=stock_prices["Date"], y=stock_prices["ClosePrice"], name="Close Price",
    line=dict(color=theme.COLORS["blue"], width=1.5),
))
buys = stock_txn[stock_txn["TransactionType"] == "Buy"]
sells = stock_txn[stock_txn["TransactionType"] == "Sell"]
fig.add_trace(go.Scatter(
    x=buys["Date"], y=buys["Price"], mode="markers", name="Buy",
    marker=dict(color=theme.COLORS["green"], size=10, symbol="triangle-up"),
))
fig.add_trace(go.Scatter(
    x=sells["Date"], y=sells["Price"], mode="markers", name="Sell",
    marker=dict(color=theme.COLORS["red"], size=10, symbol="triangle-down"),
))
fig.update_layout(height=420)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Historical Performance (Indexed to 100)")
    if not stock_prices.empty:
        base_price = stock_prices["ClosePrice"].iloc[0]
        indexed = stock_prices["ClosePrice"] / base_price * 100
        fig2 = go.Figure(go.Scatter(x=stock_prices["Date"], y=indexed, line=dict(color=theme.COLORS["gold"])))
        fig2.update_layout(height=340, yaxis_title="Indexed (base=100)")
        st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.subheader("Allocation Gauge")
    fig3 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(alloc_pct or 0) * 100,
        number={"suffix": "%"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": theme.COLORS["green"]},
            "bgcolor": theme.COLORS["surface2"],
            "borderwidth": 1,
            "bordercolor": theme.COLORS["border"],
        },
    ))
    fig3.update_layout(height=340, paper_bgcolor=theme.COLORS["surface"], font_color=theme.COLORS["text"])
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")
st.subheader(f"Transaction History for {selected}")
disp = stock_txn.sort_values("Date", ascending=False).copy()
disp["Date"] = disp["Date"].dt.strftime("%Y-%m-%d")
for col in ["Price", "Fees", "Tax", "TotalAmount"]:
    disp[col] = disp[col].apply(theme.fmt_vnd)
st.dataframe(disp[["Date", "TransactionType", "Quantity", "Price", "Fees", "Tax", "TotalAmount"]],
             use_container_width=True, hide_index=True)
