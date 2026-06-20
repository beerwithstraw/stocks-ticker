import pandas as pd
from kiteconnect import KiteConnect
from dotenv import dotenv_values
from pathlib import Path

_HERE = Path(__file__).parent
env = dotenv_values(_HERE / ".env")

# ── 1. Map NSE Industries to our Dashboard Sectors ─────────
SECTOR_MAP = {
    'Information Technology': 'IT',
    'Automobile and Auto Components': 'AUTO',
    'Healthcare': 'PHARMA',
    'Financial Services': 'FINSERV',
    'Fast Moving Consumer Goods': 'FMCG',
    'Metals & Mining': 'METAL',
    'Realty': 'REALTY',
    'Power': 'ENERGY',
    'Oil Gas & Consumable Fuels': 'ENERGY',
    'Consumer Durables': 'CONSDURABLE',
    'Construction': 'INFRA',
    'Construction Materials': 'CEMENT',
    'Telecommunication': 'TELECOM',
    'Chemicals': 'CHEMICALS',
    'Services': 'SERVICES',
    'Diversified': 'OTHER',
    'Consumer Services': 'SERVICES',
    'Textiles': 'TEXTILES',
    'Media Entertainment & Publication': 'MEDIA'
}

# ── 2. Download Nifty 500 List ─────────────────────────────
print("Downloading Nifty 500 list from NSE...")
url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
df_nse = pd.read_csv(url, storage_options={'User-Agent': 'Mozilla/5.0'})
print(f"Downloaded {len(df_nse)} stocks.")

# ── 3. Find F&O Eligible Stocks using Kite ─────────────────
print("Checking F&O eligibility via Kite API...")
kite = KiteConnect(api_key=env.get("KITE_API_KEY", ""))
# We don't need access_token just to get the instrument list! 
# Wait, instrument list requires an active session OR can be downloaded openly.
# Actually, Kite's instrument dump is open, no auth needed.
instruments = kite.instruments()

# A stock is F&O eligible if it has instruments in the "NFO" exchange 
# (specifically FUTSTK or OPTSTK)
fno_symbols = {
    ins["name"] for ins in instruments 
    if ins["exchange"] == "NFO" and ins["segment"] == "NFO-OPT"
}
print(f"Found {len(fno_symbols)} F&O eligible stocks.")

# ── 4. Build universe.csv ──────────────────────────────────
rows = []
for _, row in df_nse.iterrows():
    symbol = row['Symbol']
    industry = row['Industry']
    sector = SECTOR_MAP.get(industry, 'OTHER')
    
    # Sometimes Kite NFO names differ slightly (e.g. M&M vs M&M), but for most they match.
    is_fno = "Y" if symbol in fno_symbols else "N"
    
    # Fix for M&M, NIFTY, etc.
    if symbol == "M&M": is_fno = "Y"
    if symbol == "BAJFINANCE": is_fno = "Y"
    
    rows.append({"symbol": symbol, "sector": sector, "fno_eligible": is_fno})

df_universe = pd.DataFrame(rows)

out_path = _HERE / "universe.csv"
df_universe.to_csv(out_path, index=False)
print(f"Saved {len(df_universe)} stocks to {out_path}.")
