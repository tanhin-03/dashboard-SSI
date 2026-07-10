"""
data_loader.py
Loads and cleans SSI-exported CSVs into standardized DataFrames.
This mirrors the Power Query (M) cleaning logic from the Power BI version of this project:
- rename raw Vietnamese SSI headers -> standardized English columns
- standardize ticker symbols (trim, uppercase)
- standardize transaction types (Mua/Bán/Nộp/Rút -> Buy/Sell/Deposit/Withdrawal)
- handle nulls, drop exact duplicates
- recompute TotalAmount defensively rather than trusting the source column
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import streamlit as st


TXN_TYPE_MAP = {
    "Mua": "Buy",
    "Bán": "Sell",
    "Nộp": "Deposit",
    "Rút": "Withdrawal",
}

DIV_TYPE_MAP = {
    "Tiền": "Cash",
    "Cổ phiếu": "Stock",
}


def _standardize_ticker(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().replace({"NAN": np.nan, "": np.nan})


@st.cache_data(show_spinner=False)
def load_transactions(path_or_buffer) -> pd.DataFrame:
    """Load and clean the SSI transaction export into Fact_Transactions-equivalent DataFrame."""
    df = pd.read_csv(path_or_buffer)

    rename_map = {
        "Ngày GD": "Date",
        "Mã CK": "Ticker",
        "Loại GD": "TransactionType",
        "KL khớp": "Quantity",
        "Giá khớp": "Price",
        "Phí GD": "Fees",
        "Thuế": "Tax",
        "Giá trị": "TotalAmount",
        "Số tài khoản": "BrokerID",
    }
    df = df.rename(columns=rename_map)

    # Type conversions
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Ticker"] = _standardize_ticker(df["Ticker"])
    df["TransactionType"] = df["TransactionType"].map(TXN_TYPE_MAP).fillna(df["TransactionType"])
    for col in ["Quantity", "Price", "Fees", "Tax", "TotalAmount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Nulls: Fees/Tax -> 0 ; drop rows missing Date or TransactionType
    df["Fees"] = df["Fees"].fillna(0)
    df["Tax"] = df["Tax"].fillna(0)
    df = df.dropna(subset=["Date", "TransactionType"])

    # Remove exact duplicate rows
    df = df.drop_duplicates()

    # Signed quantity: Sell = negative, Buy = positive, Deposit/Withdrawal = 0 shares
    df["Quantity"] = df["Quantity"].fillna(0)
    df["SignedQuantity"] = np.where(
        df["TransactionType"] == "Sell", -df["Quantity"],
        np.where(df["TransactionType"] == "Buy", df["Quantity"], 0)
    )

    # Recompute TotalAmount defensively (don't trust the raw column blindly)
    def calc_total(row):
        if row["TransactionType"] == "Buy":
            return -(row["Quantity"] * row["Price"]) - row["Fees"]
        elif row["TransactionType"] == "Sell":
            return (row["Quantity"] * row["Price"]) - row["Fees"] - row["Tax"]
        else:
            return row["TotalAmount"]  # Deposit / Withdrawal: trust source value

    df["TotalAmount"] = df.apply(calc_total, axis=1)

    # Stable surrogate transaction id
    df = df.reset_index(drop=True)
    df["TransactionID"] = (
        df["Date"].dt.strftime("%Y%m%d") + "-" + df["Ticker"].fillna("CASH") + "-" + df.index.astype(str)
    )

    cols = ["TransactionID", "Date", "Ticker", "TransactionType", "Quantity",
            "SignedQuantity", "Price", "Fees", "Tax", "TotalAmount", "BrokerID"]
    return df[cols].sort_values("Date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_dividends(path_or_buffer) -> pd.DataFrame:
    """Load and clean the SSI dividend export into Fact_Dividends-equivalent DataFrame."""
    df = pd.read_csv(path_or_buffer)
    rename_map = {
        "Ngày TT": "Date",
        "Mã CK": "Ticker",
        "Số tiền cổ tức": "DividendAmount",
        "Loại cổ tức": "DividendType",
    }
    df = df.rename(columns=rename_map)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Ticker"] = _standardize_ticker(df["Ticker"])
    df["DividendAmount"] = pd.to_numeric(df["DividendAmount"], errors="coerce")
    df["DividendType"] = df["DividendType"].map(DIV_TYPE_MAP).fillna(df["DividendType"])
    df = df.dropna(subset=["Date", "Ticker", "DividendAmount"])
    df = df[df["DividendAmount"] > 0]
    df = df.drop_duplicates()
    return df.sort_values("Date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_prices(path_or_buffer) -> pd.DataFrame:
    """Load and clean daily close price history into Fact_Prices-equivalent DataFrame."""
    df = pd.read_csv(path_or_buffer)
    rename_map = {
        "Ngày": "Date",
        "Mã CK": "Ticker",
        "Giá đóng cửa": "ClosePrice",
        "Giá mở cửa": "OpenPrice",
        "Giá cao nhất": "HighPrice",
        "Giá thấp nhất": "LowPrice",
    }
    df = df.rename(columns=rename_map)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Ticker"] = _standardize_ticker(df["Ticker"])
    for col in ["ClosePrice", "OpenPrice", "HighPrice", "LowPrice"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Date", "Ticker", "ClosePrice"])
    df = df.drop_duplicates(subset=["Date", "Ticker"])
    return df.sort_values(["Ticker", "Date"]).reset_index(drop=True)


def load_all(txn_path, div_path, price_path):
    """Convenience loader returning all three cleaned DataFrames."""
    return (
        load_transactions(txn_path),
        load_dividends(div_path),
        load_prices(price_path),
    )
