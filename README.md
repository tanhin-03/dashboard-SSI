# 📊 Investment Portfolio Dashboard — Python + Streamlit

A working, deployable investment analytics dashboard for a personal SSI Securities portfolio — same scope as the Power BI version of this project (7 pages, ~40 metrics), built entirely in Python so it can run as a **live website** and be pushed straight to GitHub.

**This one actually runs on the web** (unlike the Power BI version, which needs Power BI Desktop/Service) — deploy it for free on Streamlit Community Cloud in about 5 minutes. See "Deploy" below.

---

## What's inside

```
portfolio-dashboard-python/
├── app.py                      ← Page 1: Executive Summary (entry point)
├── pages/
│   ├── 2_Portfolio_Analysis.py     ← Treemap, bubble chart, waterfall, contributors
│   ├── 3_Performance_Analysis.py   ← Returns, rolling return, drawdown, moving average
│   ├── 4_Dividend_Dashboard.py     ← Dividend timeline, yield, growth, projection
│   ├── 5_Transaction_History.py    ← Interactive filterable transaction table
│   ├── 6_Stock_Detail.py           ← Per-stock deep dive with price/buy-sell markers
│   └── 7_Risk_Dashboard.py         ← Volatility, drawdown, diversification, risk heatmap
├── src/
│   ├── data_loader.py           ← Cleans raw SSI export CSVs (rename, dedupe, type-cast)
│   ├── metrics.py                ← ~30 financial calculations (ROI, CAGR, XIRR, Sharpe, etc.)
│   ├── theme.py                  ← Dark Finance color palette + Plotly template + CSS
│   └── app_state.py              ← Shared sidebar data-source picker (sample vs. upload)
├── data/                        ← Sample (fictional) CSVs + column-mapping README
├── .streamlit/config.toml        ← Dark theme config
├── requirements.txt
└── docs/deployment-guide.md
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`. Sample data loads automatically — toggle it off in the sidebar to upload your own SSI export CSVs (see `data/README.md` for the exact column mapping).

## Deploy for free (so you have a real live link for your CV/portfolio)

1. Push this folder to a **public GitHub repo** (see `docs/deployment-guide.md` for exact git commands and what to keep out of the repo).
2. Go to **share.streamlit.io** → sign in with GitHub → "New app" → select your repo, branch `main`, main file `app.py`.
3. Deploy. You'll get a public URL like `https://your-app-name.streamlit.app` — put this link directly in your CV/LinkedIn/portfolio.

Full details, including how to keep your **real** financial data private while still showcasing the project publicly, are in `docs/deployment-guide.md`.

## What this demonstrates (for a Data Analyst CV)

- **pandas**: data cleaning, aggregation, time-series resampling
- **NumPy / SciPy**: XIRR via Brent's method root-finding, statistical measures (volatility, Sharpe ratio)
- **Plotly**: interactive charts (treemap, waterfall, bubble chart, gauges, heatmaps)
- **Streamlit**: multi-page app architecture, caching, file uploads, session state
- **Financial domain knowledge**: cost basis, realized/unrealized gains, CAGR vs XIRR, drawdown, risk-adjusted return

## Known simplifications (be upfront about these if asked in an interview)

- `Realized Gain` uses **average cost basis**, not FIFO/LIFO lot accounting — documented in `src/metrics.py`.
- `sample_prices.csv` is a **synthetic random walk**, not real market data — swap in your own price history or wire up a live price API (see `docs/deployment-guide.md` for an API integration pattern).
- Risk scoring is a simplified heuristic, not a validated financial risk model.

