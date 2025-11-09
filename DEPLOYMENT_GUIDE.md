# DigitalOcean Production Deployment Guide

## Setup Instructions

### 1. Prerequisites

- DigitalOcean Droplet with Docker and Docker Compose installed
- SSH access to your droplet
- Your domain name (or use droplet IP)

### 2. Local Development (Testing Before Production)

**Build and run locally:**

```bash
# Clone/pull your repository
cd Team31-CS-6440

# Start all services with local configuration
docker compose -f docker-compose.yml up --build

# Access the UI at http://localhost:5173
# MS1 API at http://localhost:8001/docs
# MS2 API at http://localhost:8002/docs
```

### 3. Deploy to DigitalOcean

**Step 1: SSH into your droplet**

```bash
ssh root@your-droplet-ip
```

**Step 2: Clone your repository**

```bash
cd /home
git clone https://github.com/yourusername/Team31-CS-6440.git
cd Team31-CS-6440
```

**Step 3: Create .env file for production**

```bash
cat > .env.production << EOF
# Production environment variables
DB_PASSWORD=your-secure-password-here
VITE_API_SEARCH_URL=https://your-domain.com/api/search-trials
VITE_API_DISPLAY_URL=https://your-domain.com/api/display
EOF
```

**Step 4: Build and start production services**

```bash
# Use the production docker-compose file with environment variables
export VITE_API_SEARCH_URL=https://your-domain.com/api/search-trials
export VITE_API_DISPLAY_URL=https://your-domain.com/api/display
docker compose -f docker-compose.production.yml up --build -d
```

**Step 5: Verify services are running**

```bash
docker compose -f docker-compose.production.yml ps
curl http://localhost:5173
curl http://localhost:8001/docs
curl http://localhost:8002/docs
```

### 4. Setup Reverse Proxy (Nginx) on DigitalOcean

Install Nginx on your droplet:

```bash
sudo apt update
sudo apt install nginx -y
```

Create Nginx configuration:

```bash
sudo cat > /etc/nginx/sites-available/default << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS (optional but recommended)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    # SSL certificates (set up with Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # MS1 API
    location /api/ms1/ {
        proxy_pass http://localhost:8001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # MS2 API
    location /api/ms2/ {
        proxy_pass http://localhost:8002/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    # MS4 API
    location /api/ms4/ {
        proxy_pass http://localhost:8004/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
EOF
```

Enable and restart Nginx:

```bash
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### 5. Setup SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot certonly --nginx -d your-domain.com
```

### 6. Update API URLs for Production

Once SSL is set up, update your UI environment variables:

```bash
export VITE_API_SEARCH_URL=https://your-domain.com/api/ms1/search-trials
export VITE_API_DISPLAY_URL=https://your-domain.com/api/ms2/display
docker compose -f docker-compose.production.yml up --build -d
```

### 7. Persistent Deployment with systemd

Create a systemd service to auto-restart Docker Compose on droplet reboot:

```bash
sudo cat > /etc/systemd/system/docker-compose-app.service << 'EOF'
[Unit]
Description=Docker Compose App
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/home/Team31-CS-6440
ExecStart=/usr/bin/docker compose -f docker-compose.production.yml up -d
RemainAfterExit=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable docker-compose-app.service
sudo systemctl start docker-compose-app.service
```

### 8. Monitoring and Logs

```bash
# View running services
docker compose -f docker-compose.production.yml ps

# View logs
docker compose -f docker-compose.production.yml logs -f ui
docker compose -f docker-compose.production.yml logs -f ms1
docker compose -f docker-compose.production.yml logs -f ms2

# Stop services
docker compose -f docker-compose.production.yml down

# Rebuild after code changes
docker compose -f docker-compose.production.yml up --build -d
```

## Key Differences: Local vs Production

| Aspect         | Local                            | Production                         |
| -------------- | -------------------------------- | ---------------------------------- |
| Dockerfile     | `Dockerfile.ui-dev` (dev server) | `Dockerfile.ui-production` (nginx) |
| API URLs       | `http://localhost:XXXX`          | `https://your-domain.com/api/...`  |
| Environment    | development                      | production                         |
| Volumes        | Source code mounted              | Only data volumes                  |
| Restart Policy | unless-stopped                   | always                             |
| Database       | `host.docker.internal`           | container network `ms1`            |
| SSL            | None                             | Let's Encrypt                      |

## Troubleshooting

**Services are unhealthy?**

```bash
docker compose -f docker-compose.production.yml logs ms1
docker compose -f docker-compose.production.yml logs ms2
```

**Port already in use?**

```bash
# Change ports in docker-compose.production.yml or kill existing services
docker ps -a
docker kill container-id
```

**Need to rebuild?**

```bash
docker compose -f docker-compose.production.yml down
docker compose -f docker-compose.production.yml up --build -d
```
