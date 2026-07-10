# Sample Data

These CSVs are **fictional data**, generated for demo purposes so the app has something to render out of the box.

| File | Purpose |
|---|---|
| `sample_transactions.csv` | Buy/Sell/Deposit/Withdrawal history, 4 tickers (FPT, VNM, HPG, MWG), Jan 2023 – Jun 2025 |
| `sample_dividends.csv` | Dividend payment events for the same tickers |
| `sample_prices.csv` | Daily close price history (synthetic random-walk, not real market data) for the same 4 tickers, Jan 2023 – present |

## Column mapping (matches typical SSI export headers)

**Transactions** (`Ngày GD, Mã CK, Loại GD, KL khớp, Giá khớp, Phí GD, Thuế, Giá trị, Số tài khoản`)
→ cleaned to `Date, Ticker, TransactionType, Quantity, Price, Fees, Tax, TotalAmount, BrokerID` by `src/data_loader.py`.

**Dividends** (`Ngày TT, Mã CK, Số tiền cổ tức, Loại cổ tức`)
→ cleaned to `Date, Ticker, DividendAmount, DividendType`.

**Prices** (`Ngày, Mã CK, Giá đóng cửa, Giá mở cửa, Giá cao nhất, Giá thấp nhất`)
→ cleaned to `Date, Ticker, ClosePrice, OpenPrice, HighPrice, LowPrice`.

## Using your real data

1. Export your real SSI transaction/dividend history to CSV.
2. Open it once and confirm the Vietnamese headers match the ones above — if SSI's actual export uses slightly different wording, edit the `rename_map` dictionaries at the top of the corresponding function in `src/data_loader.py` (this is the *only* place you should need to change).
3. In the running app, toggle **"Use sample data" off** in the sidebar and upload your 3 real CSVs — or replace the files in this `data/` folder directly and keep the toggle on.

⚠️ If you replace these with your real financial data, **do not commit that to a public GitHub repo** — see the root `.gitignore` and `docs/deployment-guide.md`.
