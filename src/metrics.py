"""
metrics.py
Python equivalent of the DAX measure library from the Power BI version of this project.
All functions take cleaned DataFrames (from data_loader.py) and return either a single
number or a small DataFrame, mirroring: Total Investment, Portfolio Value, ROI, CAGR,
XIRR, Max Drawdown, Volatility, Sharpe Ratio, Dividend metrics, Allocation, etc.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from datetime import date


# ---------------------------------------------------------------------------
# Basic holdings & cost
# ---------------------------------------------------------------------------

def current_shares(txn: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
    """Net shares held per ticker as of a given date (default: latest)."""
    df = txn[txn["Ticker"].notna()]
    if as_of is not None:
        df = df[df["Date"] <= as_of]
    return df.groupby("Ticker")["SignedQuantity"].sum()


def total_investment(txn: pd.DataFrame) -> float:
    """Cumulative gross cost of everything ever bought (incl. fees)."""
    buys = txn[txn["TransactionType"] == "Buy"]
    return float((buys["Quantity"] * buys["Price"] + buys["Fees"]).sum())


def average_buy_price(txn: pd.DataFrame, ticker: str | None = None) -> float:
    df = txn[txn["TransactionType"] == "Buy"]
    if ticker:
        df = df[df["Ticker"] == ticker]
    cost = (df["Quantity"] * df["Price"]).sum()
    qty = df["Quantity"].sum()
    return float(cost / qty) if qty else np.nan


def average_sell_price(txn: pd.DataFrame, ticker: str | None = None) -> float:
    df = txn[txn["TransactionType"] == "Sell"]
    if ticker:
        df = df[df["Ticker"] == ticker]
    val = (df["Quantity"] * df["Price"]).sum()
    qty = df["Quantity"].sum()
    return float(val / qty) if qty else np.nan


def cost_basis(txn: pd.DataFrame, ticker: str | None = None) -> float:
    """Average-cost-based remaining cost of open position (per ticker or whole portfolio)."""
    if ticker:
        shares = current_shares(txn).get(ticker, 0)
        avg_cost = average_buy_price(txn, ticker)
        return float(shares * avg_cost) if not np.isnan(avg_cost) else 0.0
    shares_by_ticker = current_shares(txn)
    total = 0.0
    for t, sh in shares_by_ticker.items():
        avg_cost = average_buy_price(txn, t)
        if not np.isnan(avg_cost):
            total += sh * avg_cost
    return float(total)


def realized_gain(txn: pd.DataFrame, ticker: str | None = None) -> float:
    """Average-cost approximation of profit already locked in from sells."""
    tickers = [ticker] if ticker else txn["Ticker"].dropna().unique()
    total = 0.0
    for t in tickers:
        avg_cost = average_buy_price(txn, t)
        if np.isnan(avg_cost):
            continue
        sells = txn[(txn["Ticker"] == t) & (txn["TransactionType"] == "Sell")]
        total += float((sells["Quantity"] * (sells["Price"] - avg_cost) - sells["Fees"] - sells["Tax"]).sum())
    return total


# ---------------------------------------------------------------------------
# Prices & market value
# ---------------------------------------------------------------------------

def latest_price(prices: pd.DataFrame, ticker: str, as_of: pd.Timestamp | None = None) -> float:
    df = prices[prices["Ticker"] == ticker]
    if as_of is not None:
        df = df[df["Date"] <= as_of]
    if df.empty:
        return np.nan
    return float(df.sort_values("Date").iloc[-1]["ClosePrice"])


def market_value(txn: pd.DataFrame, prices: pd.DataFrame, as_of: pd.Timestamp | None = None) -> float:
    shares = current_shares(txn, as_of=as_of)
    total = 0.0
    for ticker, sh in shares.items():
        if sh == 0:
            continue
        px = latest_price(prices, ticker, as_of=as_of)
        if not np.isnan(px):
            total += sh * px
    return float(total)


def market_value_by_stock(txn: pd.DataFrame, prices: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    shares = current_shares(txn, as_of=as_of)
    rows = []
    for ticker, sh in shares.items():
        px = latest_price(prices, ticker, as_of=as_of)
        mv = sh * px if not np.isnan(px) else 0.0
        rows.append({"Ticker": ticker, "Shares": sh, "Price": px, "MarketValue": mv})
    return pd.DataFrame(rows)


def cash_balance(txn: pd.DataFrame, div: pd.DataFrame, as_of: pd.Timestamp | None = None) -> float:
    df = txn
    if as_of is not None:
        df = df[df["Date"] <= as_of]
    cash_from_txn = float(df["TotalAmount"].sum())
    d = div
    if as_of is not None:
        d = d[d["Date"] <= as_of]
    return cash_from_txn + float(d["DividendAmount"].sum())


def portfolio_value(txn: pd.DataFrame, prices: pd.DataFrame, div: pd.DataFrame,
                     as_of: pd.Timestamp | None = None) -> float:
    return market_value(txn, prices, as_of) + cash_balance(txn, div, as_of)


def portfolio_allocation(txn: pd.DataFrame, prices: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    mv_df = market_value_by_stock(txn, prices, as_of)
    total_mv = mv_df["MarketValue"].sum()
    mv_df["AllocationPct"] = mv_df["MarketValue"] / total_mv if total_mv else 0
    return mv_df.sort_values("MarketValue", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Dividends
# ---------------------------------------------------------------------------

def dividend_income(div: pd.DataFrame, ticker: str | None = None, as_of: pd.Timestamp | None = None) -> float:
    df = div
    if ticker:
        df = df[df["Ticker"] == ticker]
    if as_of is not None:
        df = df[df["Date"] <= as_of]
    return float(df["DividendAmount"].sum())


def dividend_yield(div: pd.DataFrame, txn: pd.DataFrame, prices: pd.DataFrame, ticker: str | None = None) -> float:
    mv = market_value(txn, prices) if not ticker else market_value_by_stock(txn, prices).set_index("Ticker").get("MarketValue", {}).get(ticker, 0)
    div_income = dividend_income(div, ticker)
    return float(div_income / mv) if mv else np.nan


def dividend_growth_yoy(div: pd.DataFrame, as_of: pd.Timestamp) -> float:
    this_year = div[div["Date"].dt.year == as_of.year]["DividendAmount"].sum()
    last_year = div[div["Date"].dt.year == as_of.year - 1]["DividendAmount"].sum()
    return float((this_year - last_year) / last_year) if last_year else np.nan


# ---------------------------------------------------------------------------
# Profit & returns
# ---------------------------------------------------------------------------

def total_profit(txn: pd.DataFrame, prices: pd.DataFrame, div: pd.DataFrame) -> float:
    mv = market_value(txn, prices)
    cb = cost_basis(txn)
    unrealized = mv - cb
    realized = realized_gain(txn)
    div_income = dividend_income(div)
    return float(unrealized + realized + div_income)


def profit_pct(txn: pd.DataFrame, prices: pd.DataFrame, div: pd.DataFrame) -> float:
    ti = total_investment(txn)
    return float(total_profit(txn, prices, div) / ti) if ti else np.nan


# ---------------------------------------------------------------------------
# Portfolio value time series (for charts & time-based metrics)
# ---------------------------------------------------------------------------

def build_daily_timeseries(txn: pd.DataFrame, prices: pd.DataFrame, div: pd.DataFrame) -> pd.DataFrame:
    """Builds a daily DataFrame: Date, MarketValue, CashBalance, PortfolioValue."""
    if txn.empty or prices.empty:
        return pd.DataFrame(columns=["Date", "MarketValue", "CashBalance", "PortfolioValue"])

    start = txn["Date"].min()
    end = prices["Date"].max()
    all_dates = pd.date_range(start, end, freq="D")

    tickers = txn["Ticker"].dropna().unique()

    # Holdings per ticker per day (cumulative signed quantity, forward filled)
    holdings = pd.DataFrame(index=all_dates)
    for t in tickers:
        daily_delta = (
            txn[txn["Ticker"] == t]
            .groupby("Date")["SignedQuantity"].sum()
            .reindex(all_dates, fill_value=0)
        )
        holdings[t] = daily_delta.cumsum()

    # Price per ticker per day (forward filled from last known close)
    price_grid = pd.DataFrame(index=all_dates)
    for t in tickers:
        p = prices[prices["Ticker"] == t].set_index("Date")["ClosePrice"]
        p = p.reindex(all_dates).ffill()
        price_grid[t] = p

    market_value_series = (holdings * price_grid).sum(axis=1)

    # Cash flow per day, cumulative
    daily_cash = txn.groupby("Date")["TotalAmount"].sum().reindex(all_dates, fill_value=0)
    daily_div = div.groupby("Date")["DividendAmount"].sum().reindex(all_dates, fill_value=0) if not div.empty else pd.Series(0, index=all_dates)
    cash_balance_series = (daily_cash + daily_div).cumsum()

    out = pd.DataFrame({
        "Date": all_dates,
        "MarketValue": market_value_series.values,
        "CashBalance": cash_balance_series.values,
    })
    out["PortfolioValue"] = out["MarketValue"] + out["CashBalance"]
    return out.reset_index(drop=True)


def daily_return_series(ts: pd.DataFrame) -> pd.Series:
    return ts.set_index("Date")["PortfolioValue"].pct_change()


def cagr(ts: pd.DataFrame, total_investment_value: float) -> float:
    if ts.empty:
        return np.nan
    first_date = ts["Date"].iloc[0]
    last_date = ts["Date"].iloc[-1]
    years = (last_date - first_date).days / 365.25
    end_value = ts["PortfolioValue"].iloc[-1]
    begin_value = total_investment_value
    if years <= 0 or begin_value <= 0 or end_value <= 0:
        return np.nan
    return float((end_value / begin_value) ** (1 / years) - 1)


def max_drawdown(ts: pd.DataFrame) -> float:
    if ts.empty:
        return np.nan
    values = ts["PortfolioValue"]
    running_peak = values.cummax()
    drawdown = (values - running_peak) / running_peak
    return float(drawdown.min())


def volatility(ts: pd.DataFrame, annualize: bool = True) -> float:
    returns = daily_return_series(ts).dropna()
    if returns.empty:
        return np.nan
    vol = returns.std()
    return float(vol * np.sqrt(252)) if annualize else float(vol)


def sharpe_ratio(ts: pd.DataFrame, total_investment_value: float, risk_free_rate: float = 0.03) -> float:
    ann_return = cagr(ts, total_investment_value)
    vol = volatility(ts)
    if vol in (0, None) or np.isnan(vol) or np.isnan(ann_return):
        return np.nan
    return float((ann_return - risk_free_rate) / vol)


def rolling_return(ts: pd.DataFrame, window_days: int = 30) -> pd.Series:
    values = ts.set_index("Date")["PortfolioValue"]
    return values.pct_change(periods=window_days)


def moving_average(ts: pd.DataFrame, window_days: int = 30) -> pd.Series:
    values = ts.set_index("Date")["PortfolioValue"]
    return values.rolling(window=window_days).mean()


def period_return(ts: pd.DataFrame, periods: int, freq: str = "D") -> float:
    """Generic helper: return over the trailing N periods (days/months/years)."""
    if ts.empty:
        return np.nan
    s = ts.set_index("Date")["PortfolioValue"]
    if freq == "M":
        s = s.resample("ME").last()
    elif freq == "Y":
        s = s.resample("YE").last()
    if len(s) <= periods:
        return np.nan
    end_v = s.iloc[-1]
    start_v = s.iloc[-1 - periods]
    return float((end_v - start_v) / start_v) if start_v else np.nan


# ---------------------------------------------------------------------------
# XIRR (handles irregular cash flow timing correctly, unlike simple CAGR)
# ---------------------------------------------------------------------------

def xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float:
    """
    cashflows: list of (date, amount) tuples.
      Buys / Withdrawals of capital into the investment = negative
      Sells / Dividends / final liquidation value = positive
    Solves for the rate r such that NPV = 0 using Brent's method.
    """
    if len(cashflows) < 2:
        return np.nan
    dates = [c[0] for c in cashflows]
    amounts = np.array([c[1] for c in cashflows], dtype=float)
    t0 = min(dates)
    years = np.array([(d - t0).days / 365.0 for d in dates])

    def npv(rate):
        return np.sum(amounts / (1 + rate) ** years)

    try:
        return float(brentq(npv, -0.9999, 10, maxiter=1000))
    except ValueError:
        return np.nan


def build_xirr_cashflows(txn: pd.DataFrame, div: pd.DataFrame, prices: pd.DataFrame,
                          as_of: pd.Timestamp | None = None) -> list[tuple[pd.Timestamp, float]]:
    """Builds the cash flow list for XIRR: buys negative, sells/dividends positive,
    plus a synthetic final 'liquidate everything at current market value' inflow."""
    as_of = as_of or txn["Date"].max()
    flows = []
    buys = txn[(txn["TransactionType"] == "Buy") & (txn["Date"] <= as_of)]
    for _, r in buys.iterrows():
        flows.append((r["Date"], -(r["Quantity"] * r["Price"] + r["Fees"])))
    sells = txn[(txn["TransactionType"] == "Sell") & (txn["Date"] <= as_of)]
    for _, r in sells.iterrows():
        flows.append((r["Date"], r["Quantity"] * r["Price"] - r["Fees"] - r["Tax"]))
    d = div[div["Date"] <= as_of]
    for _, r in d.iterrows():
        flows.append((r["Date"], r["DividendAmount"]))
    mv = market_value(txn, prices, as_of)
    if mv > 0:
        flows.append((as_of, mv))
    return flows


# ---------------------------------------------------------------------------
# Risk & diversification
# ---------------------------------------------------------------------------

def diversification_score(txn: pd.DataFrame, prices: pd.DataFrame) -> float:
    """1 - Herfindahl index of allocation weights, scaled 0-100."""
    alloc = portfolio_allocation(txn, prices)
    if alloc.empty:
        return np.nan
    hhi = (alloc["AllocationPct"] ** 2).sum()
    return float((1 - hhi) * 100)


def largest_position_pct(txn: pd.DataFrame, prices: pd.DataFrame) -> float:
    alloc = portfolio_allocation(txn, prices)
    return float(alloc["AllocationPct"].max()) if not alloc.empty else np.nan


# ---------------------------------------------------------------------------
# Top/bottom contributors
# ---------------------------------------------------------------------------

def contribution_by_stock(txn: pd.DataFrame, prices: pd.DataFrame, div: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for t in txn["Ticker"].dropna().unique():
        mv = market_value_by_stock(txn, prices).set_index("Ticker")["MarketValue"].get(t, 0)
        cb = cost_basis(txn, t)
        unreal = mv - cb
        real = realized_gain(txn, t)
        div_income = dividend_income(div, t)
        profit = unreal + real + div_income
        rows.append({"Ticker": t, "Profit": profit, "MarketValue": mv,
                     "UnrealizedGain": unreal, "RealizedGain": real, "DividendIncome": div_income})
    df = pd.DataFrame(rows)
    total_profit_sum = df["Profit"].sum()
    df["ContributionPct"] = df["Profit"] / total_profit_sum if total_profit_sum else 0
    df["ProfitPct"] = df.apply(
        lambda r: r["Profit"] / (cost_basis(txn, r["Ticker"]) or average_buy_price(txn, r["Ticker"]) * 1)
        if cost_basis(txn, r["Ticker"]) else np.nan, axis=1
    )
    return df.sort_values("Profit", ascending=False).reset_index(drop=True)
