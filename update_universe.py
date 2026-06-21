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

# Known bank symbols that may not have 'Bank' in their company name
BANK_SYMBOLS = {"SBIN", "PNB", "IOB", "CANFINHOME"}

# ── Manual overrides for badly auto-bucketed stocks ────────────────────────────
# Capital Goods / Industrial / Engineering
_CAPGOODS = {"ABB", "SIEMENS", "SCHNEIDER", "CGPOWER", "BHEL", "THERMAX",
              "CUMMINSIND", "KIRLOSENG", "TIMKEN", "ELGIEQUIP", "ELECON",
              "HONAUT", "ABB", "POLYCAB", "KEI", "FINCABLES", "RRKABEL",
              "GVT&D", "POWERINDIA", "3MINDIA", "AIAENG", "CARBORUNIV",
              "JYOTICNC", "USHAMART", "HBLENGINE", "PTCIL"}

# Defence & Shipbuilding → keep under INFRA
_DEFENCE   = {"HAL", "BEL", "BDL", "BEML", "COCHINSHIP", "GRSE",
              "MAZDOCK", "TITAGARH"}

# Auto stocks missed by NSE classification
_AUTO_EXTRA = {"ASHOKLEY", "ESCORTS", "TMCV"}

# Renewable energy / energy equipment
_ENERGY_EXTRA = {"SUZLON", "INOXWIND", "WAAREEENER", "EMMVEE",
                 "PREMIERENE", "TRITURBINE", "ACUTAAS"}

# Metals & Mining missed by NSE
_METAL_EXTRA = {"GRAPHITE", "HEG", "SHYAMMETL", "APLAPOLLO",
                "WELCORP", "JINDALSAW", "GALLANTT", "GPIL"}

# IT / Electronics / Tech
_IT_EXTRA    = {"KAYNES", "SYRMA", "DATAPATTNS", "ZENTEC", "CPPLUS",
                "NAUKRI", "INDIAMART", "CARTRADE", "TBOTEK", "ECLERX"}

# Food & Retail → FMCG
_FMCG_EXTRA  = {"SWIGGY", "ETERNAL", "JUBLFOOD", "DEVYANI", "SAPPHIRE",
                "TRENT", "ABFRL", "ABLBL", "DMART", "TRAVELFOOD", "ACE"}

# Chemicals / Materials
_CHEM_EXTRA  = {"SUPREMEIND", "ASTRAL", "AEGISLOG", "AEGISVOPAK", "RHIM",
                "TEGA", "DCMSHRIRAM"}

# Logistics & Transport (keep under SERVICES)
_SERV_KEEP   = {"IRCTC", "INDIGO", "GMRAIRPORT", "ADANIPORTS", "CONCOR",
                "BLUEDART", "DELHIVERY", "GESHIP", "SCI", "JSWINFRA",
                "REDINGTON", "MMTC", "FSL", "BLS"}

# Hospitality → SERVICES fine
# Internet platforms → IT
_IT_INTERNET = {"NYKAA", "FIRSTCRY", "MEESHO", "LENSKART", "PAYTM",
                "POLICYBZR", "ANGELONE", "CARTRADE"}

SYMBOL_OVERRIDES = {}
for sym in _CAPGOODS:   SYMBOL_OVERRIDES[sym] = "CAPGOODS"
for sym in _DEFENCE:    SYMBOL_OVERRIDES[sym] = "INFRA"
for sym in _AUTO_EXTRA: SYMBOL_OVERRIDES[sym] = "AUTO"
for sym in _ENERGY_EXTRA: SYMBOL_OVERRIDES[sym] = "ENERGY"
for sym in _METAL_EXTRA:  SYMBOL_OVERRIDES[sym] = "METAL"
for sym in _IT_EXTRA:     SYMBOL_OVERRIDES[sym] = "IT"
for sym in _IT_INTERNET:  SYMBOL_OVERRIDES[sym] = "IT"
for sym in _FMCG_EXTRA:   SYMBOL_OVERRIDES[sym] = "FMCG"
for sym in _CHEM_EXTRA:   SYMBOL_OVERRIDES[sym] = "CHEMICALS"

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
    company_name = row['Company Name']
    sector = SECTOR_MAP.get(industry, 'OTHER')

    # Override: detect banking stocks by company name or known symbols
    if 'bank' in company_name.lower() or symbol in BANK_SYMBOLS:
        sector = 'BANK'

    # Apply manual overrides for badly auto-bucketed stocks
    if symbol in SYMBOL_OVERRIDES:
        sector = SYMBOL_OVERRIDES[symbol]

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

print("\n=== Final sector distribution ===")
print(df_universe['sector'].value_counts().to_string())
