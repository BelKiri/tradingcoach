# Runbook 001: Deploy TradingCoach backend to VPS

Server: `<SERVER_HOST>` (VPS provider, EU region)  
Project dir: `~/tradingcoach`  
Git remote: `https://github.com/BelKiri/tradingcoach.git` (public, no auth)  
Backend bind: `localhost:8000` (loopback via Docker Compose)  
Public HTTP: nginx on `:80` → `localhost:8000`

## Server git safety

- Never run `git clean -fd` on the server. It can delete a local `venv/` or other untracked files you rely on.
- Before every pull, reset tracked files to the last commit, then pull:

```bash
cd ~/tradingcoach
git checkout -- .
git pull
```

## First-time setup

From your Mac:

```bash
ssh tradingcoach
```

On the server:

```bash
git clone https://github.com/BelKiri/tradingcoach.git ~/tradingcoach
cd ~/tradingcoach
```

Create production `.env` from the example template (not committed to git):

```bash
cp .env.example .env
nano .env  # fill in real values per .env.example
```

Build and start the API container:

```bash
cd ~/tradingcoach
docker compose up -d --build
```

## Deploy update (after code changes)

```bash
ssh tradingcoach
cd ~/tradingcoach
git checkout -- .
git pull
docker compose up -d --build
```

## Verify health

On the server (direct loopback to the API container):

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok","version":"0.1.0"}
```

After nginx is configured, from your Mac:

```bash
curl http://<SERVER_HOST>/health
```

## View logs

```bash
ssh tradingcoach
cd ~/tradingcoach
docker compose logs -f api
```

## Stop / restart

```bash
ssh tradingcoach
cd ~/tradingcoach
docker compose down
docker compose restart api
```

## Rollback

```bash
ssh tradingcoach
cd ~/tradingcoach
git checkout -- .
git checkout <prev-sha>
docker compose up -d --build
```

Replace `<prev-sha>` with the last known good commit (for example `git log --oneline -n 5`).

## Initial nginx + firewall setup (run once)

Run on the server before the first nginx-fronted request.

```bash
ssh tradingcoach
sudo apt update && sudo apt install -y nginx
```

```bash
sudo tee /etc/nginx/sites-available/tradingcoach <<'EOF'
server {
    listen 80 default_server;
    server_name <SERVER_HOST>;

    client_max_body_size 20M;

    location / {
        proxy_pass http://localhost:8000;
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
