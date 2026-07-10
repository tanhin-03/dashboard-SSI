# Deployment Guide

## Local run

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
pip install -r requirements.txt
streamlit run app.py
```

## Push to GitHub

```bash
cd portfolio-dashboard-python
git init
git add .
git commit -m "Initial commit: Python portfolio dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

**Before pushing, decide what to do about real financial data:**

- If you're only using the bundled sample data (fictional) → nothing to worry about, push everything.
- If you replaced `data/*.csv` with your **real** SSI transaction history → do NOT push those files. Add to `.gitignore`:
  ```
  data/sample_transactions.csv
  data/sample_dividends.csv
  data/sample_prices.csv
  ```
  (only if you overwrote them with real data — if they're still the fictional samples, it's fine to keep them tracked)
- Better pattern: keep the fictional samples in the repo as-is (so the public demo works), and use the in-app **file uploader** (sidebar → toggle "Use sample data" off) to load your real data locally without ever writing it into the repo folder.

## Deploy to Streamlit Community Cloud (free, public URL)

1. Push the repo to GitHub (public repo required for the free tier).
2. Go to **share.streamlit.io**, sign in with your GitHub account.
3. Click **"New app"** → choose your repo → branch `main` → main file path `app.py`.
4. Click **Deploy**. First deploy takes 1-3 minutes to install dependencies from `requirements.txt`.
5. You get a URL like `https://<your-app-name>.streamlit.app` — this is a genuinely live, running dashboard, safe to put in a CV since it only ever serves the fictional sample data (visitors can optionally upload their own CSV to try it with different numbers, but your real data never touches the deployed server unless you explicitly upload it there yourself).

## Keeping your real portfolio private while still having a public demo

This is the key difference from the Power BI version: because this is a **web app**, "public repo" and "public data" are two separate concerns:

- The **code** (this repo) can be fully public — it contains no real financial data if you keep the fictional samples in `data/`.
- Your **real data** only ever exists: (a) locally on your machine when you run `streamlit run app.py` yourself and upload your real CSVs through the sidebar, or (b) temporarily in server memory if you upload it to the *deployed* Streamlit Cloud app in your own browser session — it is not written back into the GitHub repo either way.
- If you want a persistent private version with your real data always loaded (not just sample data with an upload option), deploy a **second, private** Streamlit Cloud app pointed at a **private** GitHub repo containing your real CSVs in `data/`, and don't share that URL.

## Automatic daily price updates (optional, for genuine "real-time")

The current `src/data_loader.py` reads static CSVs. To make prices update automatically:

1. Pick a price data API (see the Power BI version's `docs/06-api-integration-guide.md` for provider options and caveats — same considerations apply here).
2. Add a function in `src/data_loader.py` using the `requests` library to pull the latest daily close for each ticker in `Dim_Stock`-equivalent (i.e., the unique tickers in your transactions).
3. Cache it with `st.cache_data(ttl=3600)` (refresh at most once per hour) instead of `st.cache_data` (permanent cache) to keep it reasonably current without hammering the API on every page interaction.
4. Streamlit Cloud apps stay "alive" and re-run on each visit / periodically wake from sleep — for a strictly scheduled daily refresh independent of visits, you'd add a small **GitHub Actions cron job** that calls your price API and commits an updated `sample_prices.csv` (or a real prices file) to the repo on a schedule, which the app then reads on its next run. This is one legitimate way GitHub *can* participate in automation — via GitHub Actions, not by "running" the dashboard itself.

## requirements.txt pinning

The bundled `requirements.txt` uses `>=` version floors for readability. For a production deploy where you want reproducible builds, consider pinning exact versions (`pip freeze > requirements.txt` after testing) so a future dependency update doesn't silently change behavior.
