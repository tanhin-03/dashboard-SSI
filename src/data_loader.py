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

import os
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
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

ENCODINGS_TO_TRY = (
    "utf-8-sig",
    "utf-8",
    "cp1258",
    "cp1252",
    "latin-1",
    "utf-16",
    "utf-16-le",
    "utf-16-be",
)
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb", ".ods", ".odf"}


def _standardize_ticker(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().replace({"NAN": np.nan, "": np.nan})


def _read_dataframe(path_or_buffer: Any) -> pd.DataFrame:
    """Read CSV-like or Excel-like data with encoding and format fallbacks."""
    source_name = ""
    if hasattr(path_or_buffer, "name"):
        source_name = str(path_or_buffer.name)
    elif isinstance(path_or_buffer, (str, os.PathLike)):
        source_name = str(path_or_buffer)

    suffix = Path(source_name).suffix.lower()

    if hasattr(path_or_buffer, "read"):
        if hasattr(path_or_buffer, "seek"):
            current_pos = path_or_buffer.tell() if hasattr(path_or_buffer, "tell") else None
            path_or_buffer.seek(0)
        raw_bytes = path_or_buffer.read()
        if hasattr(path_or_buffer, "seek"):
            if current_pos is None:
                path_or_buffer.seek(0)
            else:
                path_or_buffer.seek(current_pos)
    else:
        with open(path_or_buffer, "rb") as fh:
            raw_bytes = fh.read()

    if not raw_bytes:
        raise ValueError("The uploaded file is empty.")

    if suffix in EXCEL_EXTENSIONS:
        for engine in (None, "openpyxl", "calamine"):
            try:
                if engine is None:
                    return pd.read_excel(BytesIO(raw_bytes))
                return pd.read_excel(BytesIO(raw_bytes), engine=engine)
            except ImportError:
                continue
            except Exception:
                continue

    for encoding in ENCODINGS_TO_TRY:
        for kwargs in (
            {"encoding": encoding},
            {"encoding": encoding, "sep": ","},
            {"encoding": encoding, "sep": ";"},
            {"encoding": encoding, "sep": "\t"},
            {"encoding": encoding, "engine": "python", "sep": None},
        ):
            try:
                return pd.read_csv(BytesIO(raw_bytes), **kwargs)
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                continue

    raise ValueError(
        "Unable to read the uploaded data. Please upload a UTF-8/UTF-8-BOM/Windows-1258 CSV-like file or a supported Excel file."
    )


@st.cache_data(show_spinner=False)
def load_transactions(path_or_buffer) -> pd.DataFrame:
    """Load and clean the SSI transaction export into Fact_Transactions-equivalent DataFrame."""
    df = _read_dataframe(path_or_buffer)

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
    df = _read_dataframe(path_or_buffer)
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
    df = _read_dataframe(path_or_buffer)
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
