"""
get_token.py — Daily access-token helper for Morning Movers Dashboard
----------------------------------------------------------------------
Run once each morning before starting the dashboard:

    python get_token.py

What it does:
  1. Reads your KITE_API_KEY and KITE_API_SECRET from .env
  2. Opens the Kite login page in your browser
  3. Asks you to paste the redirect URL after you log in
  4. Exchanges the request_token for today's access_token
  5. Writes KITE_ACCESS_TOKEN back into your .env automatically

Requires: pip install kiteconnect python-dotenv
"""

import re
import sys
import webbrowser
from pathlib import Path

from dotenv import dotenv_values, set_key
from kiteconnect import KiteConnect

_HERE = Path(__file__).parent
ENV_PATH = _HERE / ".env"


def main():
    # ── Load credentials ──────────────────────────────────────────────────
    env = dotenv_values(ENV_PATH)
    api_key = env.get("KITE_API_KEY", "").strip()
    api_secret = env.get("KITE_API_SECRET", "").strip()

    missing = [k for k, v in (("KITE_API_KEY", api_key), ("KITE_API_SECRET", api_secret)) if not v]
    if missing:
        print(f"[ERROR] Missing in .env: {', '.join(missing)}")
        print(f"        Edit {ENV_PATH} and try again.")
        sys.exit(1)

    # ── Open login URL ────────────────────────────────────────────────────
    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()
    print(f"\nOpening Kite login page in your browser...")
    print(f"  {login_url}\n")
    webbrowser.open(login_url)

    print("After you log in, Zerodha will redirect you to a URL that looks like:")
    print("  https://127.0.0.1/?request_token=XXXXXXXXXXXXXXXX&action=login&status=success\n")
    redirect = input("Paste that full redirect URL here and press Enter:\n> ").strip()

    # ── Extract request_token from the URL ────────────────────────────────
    match = re.search(r"[?&]request_token=([^&]+)", redirect)
    if not match:
        print("\n[ERROR] Could not find request_token in that URL. Please try again.")
        sys.exit(1)

    request_token = match.group(1)
    print(f"\nRequest token: {request_token[:8]}…  (exchanging for access token)")

    # ── Generate session → access token ───────────────────────────────────
    try:
        session = kite.generate_session(request_token, api_secret=api_secret)
    except Exception as exc:
        print(f"\n[ERROR] Failed to generate session: {exc}")
        sys.exit(1)

    access_token = session["access_token"]

    # ── Write access token back to .env ───────────────────────────────────
    set_key(str(ENV_PATH), "KITE_ACCESS_TOKEN", access_token)
    print(f"\n✅  Access token saved to {ENV_PATH}")
    print(f"   Token: {access_token[:8]}…")
    print("\nYou can now run:  streamlit run dashboard.py")


if __name__ == "__main__":
    main()
