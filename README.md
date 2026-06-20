# Morning Movers Dashboard

Minimal setup. Four files, no folders, no database.

## Files
- `dashboard.py` — the whole app
- `universe.csv` — your stock list + sector tags (starter list of ~60 liquid
  large/mid-caps included — replace with the full Nifty 100 + Midcap 150
  list from niftyindices.com whenever you want the full universe)
- `.env.example` — copy to `.env`, fill in your real Kite credentials
- this README

## Setup

```bash
pip install streamlit kiteconnect pandas python-dotenv --break-system-packages
cp .env.example .env
# edit .env with your real KITE_API_KEY and today's KITE_ACCESS_TOKEN
streamlit run dashboard.py
```

It'll open in your browser automatically (usually http://localhost:8501).

## Daily use

Your Kite `access_token` expires every day — regenerate it through your usual
login flow each morning (same one you use for nifty-option-edge) and update
`.env` before running. Everything else just works — hit Refresh whenever
you want a new snapshot.

## Extending the universe

`universe.csv` is a plain two-column file: `symbol,sector`. Add rows to
expand it. If you add a sector that isn't in `SECTOR_INDEX` at the top of
`dashboard.py`, add its NSE index tradingsymbol there too, or that sector's
tile just won't get an index row.

## Known trade-offs (intentional, given "keep it minimal")

- No live ticking clock — shows "last refreshed at" instead, anchored to
  when the data was actually pulled, not your system clock.
- 52-week high/low and 20-day average volume are cached for 24 hours, not
  recomputed on every refresh click — they don't move intraday, and
  recomputing them on every click would mean ~60+ historical_data calls
  every time you hit Refresh, which is slow and unnecessary.
- No colored gradient cells yet — Move % and Rel. Vol are plain numbers,
  52w Position uses Streamlit's built-in progress-bar column. Polished
  color gradients are doable later via pandas Styler if you want them, but
  add real code for a cosmetic win — skipped for v1.
