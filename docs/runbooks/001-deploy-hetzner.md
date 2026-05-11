# Runbook 001: Deploy TradingCoach backend to Hetzner

Server: `46.224.52.73` (Hetzner CPX22, Falkenstein)  
User: `deploy`  
Project dir: `/home/deploy/tradingcoach`  
Git remote: `https://github.com/BelKiri/tradingcoach.git` (public, no auth)  
Backend bind: `127.0.0.1:8000` (loopback via Docker Compose)  
Public HTTP: nginx on `:80` → `127.0.0.1:8000`

## Server git safety

- Never run `git clean -fd` on the server. It can delete a local `venv/` or other untracked files you rely on.
- Before every pull, reset tracked files to the last commit, then pull:

```bash
cd /home/deploy/tradingcoach
git checkout -- .
git pull
```

## First-time setup

From your Mac:

```bash
ssh deploy@46.224.52.73
```

On the server:

```bash
git clone https://github.com/BelKiri/tradingcoach.git /home/deploy/tradingcoach
cd /home/deploy/tradingcoach
```

Create production `.env` manually (not committed to git):

```bash
nano /home/deploy/tradingcoach/.env
```

Paste and fill real values:

```env
SUPABASE_URL=<REAL>
SUPABASE_KEY=<REAL>
SUPABASE_SERVICE_ROLE_KEY=<REAL>
ANTHROPIC_API_KEY=<REAL>
TWELVEDATA_API_KEY=<REAL>
FINNHUB_API_KEY=<REAL>
OPENAI_API_KEY=
TELEGRAM_BOT_TOKEN=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
```

Build and start the API container:

```bash
cd /home/deploy/tradingcoach
docker compose up -d --build
```

## Deploy update (after code changes)

```bash
ssh deploy@46.224.52.73
cd /home/deploy/tradingcoach
git checkout -- .
git pull
docker compose up -d --build
```

## Verify health

On the server (direct loopback to the API container):

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","version":"0.1.0"}
```

After nginx is configured, from your Mac:

```bash
curl http://46.224.52.73/health
```

## View logs

```bash
ssh deploy@46.224.52.73
cd /home/deploy/tradingcoach
docker compose logs -f api
```

## Stop / restart

```bash
ssh deploy@46.224.52.73
cd /home/deploy/tradingcoach
docker compose down
docker compose restart api
```

## Rollback

```bash
ssh deploy@46.224.52.73
cd /home/deploy/tradingcoach
git checkout -- .
git checkout <prev-sha>
docker compose up -d --build
```

Replace `<prev-sha>` with the last known good commit (for example `git log --oneline -n 5`).

## Initial nginx + firewall setup (run once)

Run on the server before the first nginx-fronted request.

```bash
ssh deploy@46.224.52.73
sudo apt update && sudo apt install -y nginx
```

```bash
sudo tee /etc/nginx/sites-available/tradingcoach <<'EOF'
server {
    listen 80 default_server;
    server_name 46.224.52.73;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF
```

```bash
sudo ln -sf /etc/nginx/sites-available/tradingcoach /etc/nginx/sites-enabled/tradingcoach
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
sudo ufw status verbose
```
