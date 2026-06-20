# Morning Movers — Server Deployment Guide

## What you need

- A VPS (DigitalOcean, Hetzner, AWS Lightsail — any Ubuntu 22.04 machine)
- Your domain thelocalbeacon.in with DNS access (Netlify DNS or wherever it's managed)
- ~15 minutes

The Netlify site stays as-is. You're just adding a subdomain that points
to the VPS where Streamlit runs.

---

## Step 1 — Point a subdomain to your VPS

In your DNS settings (Netlify DNS → "Add new record"):

| Type | Name              | Value         |
|------|-------------------|---------------|
| A    | stocks            | <VPS_IP>      |

This makes `stocks.thelocalbeacon.in` point to your server.

---

## Step 2 — Set up the VPS

SSH into your server and run:

```bash
# Install Python, nginx, git
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx git

# Clone / upload your project
git clone https://github.com/YOUR_USERNAME/stocks-ticker.git /opt/stocks-ticker
# OR use scp from your Mac:
# scp -r /Users/pulkit/Desktop/App/stocks-ticker user@VPS_IP:/opt/stocks-ticker

cd /opt/stocks-ticker
python3 -m venv .venv
.venv/bin/pip install streamlit kiteconnect pandas python-dotenv

# Create .env on the server
cp env.example .env
nano .env   # fill in KITE_API_KEY and KITE_API_SECRET
            # leave KITE_ACCESS_TOKEN blank for now — renew via the dashboard UI
```

---

## Step 3 — Run as a systemd service (always-on)

```bash
sudo cp deploy/morning-movers.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable morning-movers
sudo systemctl start morning-movers

# Check it's running
sudo systemctl status morning-movers
```

---

## Step 4 — Configure nginx reverse proxy

```bash
sudo cp deploy/nginx-stocks.conf /etc/nginx/sites-available/stocks
sudo ln -s /etc/nginx/sites-available/stocks /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Step 5 — SSL (HTTPS) — free via Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d stocks.thelocalbeacon.in
```

---

## Step 6 — Renew your token each morning

1. Open `https://stocks.thelocalbeacon.in` in your browser
2. Toggle **🔑 Token** in the top-right of the dashboard
3. Click "Open Kite Login →", log in to Zerodha
4. Copy the redirect URL, paste it back, hit **Save Token**
5. Hit **⟳ Refresh** — done

No SSH, no terminal needed after initial setup.

---

## Updating the dashboard

```bash
cd /opt/stocks-ticker
git pull
sudo systemctl restart morning-movers
```
