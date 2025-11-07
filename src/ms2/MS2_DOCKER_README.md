# MS2 Microservice - Docker Setup Guide

## Overview

MS2 (Microservice 2) is a Clinical Trial Criteria Parser that uses LLM (OpenAI GPT-4) to parse and structure eligibility criteria from clinical trials.

### Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   MS2 Service   │─────▶│   PostgreSQL    │      │   OpenAI API    │
│   (FastAPI)     │      │   Database      │      │   (GPT-4)       │
│   Port: 8002    │      │   Port: 5432    │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
         │                        
         │                        
         ▼                        
┌─────────────────┐               
│     Redis       │               
│   (Optional)    │               
│   Port: 6379    │               
└─────────────────┘               
```

## Prerequisites

- Docker (20.10+)
- Docker Compose (2.0+)
- OpenAI API Key

## Quick Start

### 1. Set Environment Variables

Create a `.env` file in the root directory:

```bash
# .env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 2. Build and Run

```bash
# Build the MS2 image
docker-compose build ms2

# Start all services (PostgreSQL + MS2 + Redis)
docker-compose up -d

# Check logs
docker-compose logs -f ms2
```

### 3. Verify Running Services

```bash
# Check service status
docker-compose ps

# Test MS2 health endpoint
curl http://localhost:8002/api/ms2/health

# Test MS2 root endpoint
curl http://localhost:8002/api/ms2/
```

## Service Endpoints

### MS2 Service
- **Base URL:** `http://localhost:8002`
- **API Prefix:** `/api/ms2`
- **Health Check:** `GET /api/ms2/health`
- **Root:** `GET /api/ms2/`
- **Parse Criteria:** `POST /api/ms2/parse-criteria/{nct_id}`

### PostgreSQL
- **Host:** localhost
- **Port:** 5432
- **Database:** ms2_db
- **User:** postgres
- **Password:** postgres

### Redis
- **Host:** localhost
- **Port:** 6379

## API Usage Examples

### 1. Health Check
```bash
curl http://localhost:8002/api/ms2/health
```

### 2. Parse Clinical Trial Criteria
```bash
curl -X POST "http://localhost:8002/api/ms2/parse-criteria/NCT05123456" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Inclusion Criteria:\n- Age 18 to 65 years\n- Type 2 Diabetes\n\nExclusion Criteria:\n- Pregnancy"
  }'
```

### 3. Parse with Reasoning
```bash
curl -X POST "http://localhost:8002/api/ms2/parse-criteria/NCT05123456?include_reasoning=true" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Inclusion: Age 18-65, HbA1c > 7%"
  }'
```

## Docker Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start only specific services
docker-compose up -d postgres ms2

# Start with logs
docker-compose up
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (delete all data)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ms2

# Last 100 lines
docker-compose logs --tail=100 ms2
```

### Rebuild
```bash
# Rebuild MS2 image
docker-compose build ms2

# Rebuild without cache
docker-compose build --no-cache ms2

# Rebuild and restart
docker-compose up -d --build ms2
```

### Execute Commands
```bash
# Access MS2 container shell
docker-compose exec ms2 /bin/bash

# Run Python command
docker-compose exec ms2 python -c "print('Hello from MS2')"

# Check MS2 logs
docker-compose exec ms2 cat /var/log/ms2.log
```

### Database Operations
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d ms2_db

# Backup database
docker-compose exec postgres pg_dump -U postgres ms2_db > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U postgres -d ms2_db
```

## Development Mode

For development, the source code is mounted as a volume so changes are reflected immediately:

```yaml
volumes:
  - ./src:/app/src  # Hot reload enabled
```

To disable hot reload for production:
```bash
# Comment out the volume in docker-compose.yml
# Then rebuild:
docker-compose build ms2
docker-compose up -d ms2
```

## Production Deployment

### 1. Environment Variables

Create a production `.env` file:
```bash
OPENAI_API_KEY=sk-prod-key-here
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/ms2_db
ENVIRONMENT=production
LOG_LEVEL=warning
```

### 2. Remove Development Volumes

Comment out development volume mounts in `docker-compose.yml`:
```yaml
ms2:
  # volumes:
  #   - ./src:/app/src  # Disable for production
```

### 3. Use Production Database

Update DATABASE_URL to point to production PostgreSQL instance.

### 4. Enable HTTPS

Use a reverse proxy (nginx, traefik) for HTTPS:
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs ms2

# Check if port is already in use
lsof -i :8002

# Restart service
docker-compose restart ms2
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U postgres
```

### MS2 Health Check Failing

```bash
# Check MS2 logs
docker-compose logs ms2

# Manually test health endpoint from inside container
docker-compose exec ms2 curl http://localhost:8002/api/ms2/health

# Check if OpenAI API key is set
docker-compose exec ms2 env | grep OPENAI
```

### Out of Memory

```bash
# Check container stats
docker stats

# Increase memory limit in docker-compose.yml
services:
  ms2:
    mem_limit: 2g
    mem_reservation: 1g
```

## Monitoring

### View Service Status
```bash
docker-compose ps
```

### View Resource Usage
```bash
docker stats ms2_service
```

### View Network
```bash
docker network inspect ms2_network
```

## Backup and Restore

### Backup Database
```bash
docker-compose exec postgres pg_dump -U postgres ms2_db > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
cat backup_20241030.sql | docker-compose exec -T postgres psql -U postgres -d ms2_db
```

### Backup Volumes
```bash
docker run --rm -v ms2_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Scaling

To run multiple MS2 instances:

```yaml
ms2:
  deploy:
    replicas: 3
```

Or use docker-compose scale:
```bash
docker-compose up -d --scale ms2=3
```

## Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use secrets management** - Docker secrets or external vault
3. **Run as non-root user** - Already configured in Dockerfile
4. **Keep images updated** - Regularly rebuild with latest base images
5. **Scan for vulnerabilities** - Use `docker scan ms2_service`
6. **Use HTTPS** - Enable TLS in production
7. **Limit resource usage** - Set memory and CPU limits

## Clean Up

### Remove All Containers and Volumes
```bash
docker-compose down -v --remove-orphans
```

### Remove Images
```bash
docker image rm ms2_service
```

### Clean Docker System
```bash
docker system prune -a --volumes
```

## Support

For issues or questions:
- Check logs: `docker-compose logs ms2`
- Review health status: `curl http://localhost:8002/api/ms2/health`
- Verify environment variables are set correctly

## License

[Your License Here]
