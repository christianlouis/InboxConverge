# Deployment Guide

This guide walks you through deploying **POP3 to Gmail Forwarder** from scratch — whether you just want a single container pulling emails, a full multi-service SaaS stack with Docker Compose, or a production-grade Kubernetes setup.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options at a Glance](#deployment-options-at-a-glance)
- [Option 1 — Legacy Single-Container Deployment](#option-1--legacy-single-container-deployment)
- [Option 2 — Full SaaS Stack with Docker Compose](#option-2--full-saas-stack-with-docker-compose)
- [Option 3 — Kubernetes Deployment](#option-3--kubernetes-deployment)
- [Google OAuth and Gmail API Setup](#google-oauth-and-gmail-api-setup)
- [Reverse Proxy and TLS](#reverse-proxy-and-tls)
- [Environment Variable Reference](#environment-variable-reference)
- [Upgrading](#upgrading)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Minimum | Recommended |
|---|---|---|
| **Docker** | 20.10+ | Latest stable |
| **Docker Compose** | v2.0+ | Latest stable |
| **RAM** | 1 GB (legacy) / 4 GB (SaaS) | 8 GB (SaaS) |
| **Disk** | 10 GB (legacy) / 40 GB (SaaS) | 80 GB (SaaS) |
| **CPU** | 1 vCPU (legacy) / 2 vCPU (SaaS) | 4 vCPU (SaaS) |

You will also need:

- A **Gmail account** with [2-Step Verification](https://myaccount.google.com/signinoptions/two-step-verification) enabled and an [App Password](https://myaccount.google.com/apppasswords) generated (for SMTP delivery).
- Credentials for one or more **POP3 mailboxes** you want to pull email from.
- *(SaaS stack only)* A **Google Cloud project** with OAuth 2.0 credentials if you want Google sign-in or Gmail API injection (see [Google OAuth and Gmail API Setup](#google-oauth-and-gmail-api-setup)).

---

## Deployment Options at a Glance

| | Legacy | SaaS (Docker Compose) | SaaS (Kubernetes) |
|---|---|---|---|
| **Services** | 1 container | 6 containers | 6+ pods |
| **Database** | None | PostgreSQL | PostgreSQL |
| **Queue** | None | Redis + Celery | Redis + Celery |
| **Web UI** | None | Next.js frontend | Next.js frontend |
| **Multi-user** | No | Yes | Yes |
| **Best for** | Personal / single mailbox | Small teams / self-hosted | Production / scale |

---

## Option 1 — Legacy Single-Container Deployment

The legacy mode runs a single Python script (`pop3_forwarder.py`) that polls POP3 mailboxes and forwards email via SMTP. No database, no web UI — just a container and an `.env` file.

### 1. Create the environment file

```bash
git clone https://github.com/christianlouis/pop_puller_to_gmail.git
cd pop_puller_to_gmail
cp .env.example .env
```

Edit `.env` with your credentials:

```ini
# POP3 source mailbox
POP3_ACCOUNT_1_HOST=pop.example.com
POP3_ACCOUNT_1_PORT=995
POP3_ACCOUNT_1_USER=user@example.com
POP3_ACCOUNT_1_PASSWORD=your_password
POP3_ACCOUNT_1_USE_SSL=true

# Gmail SMTP destination
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password
SMTP_USE_TLS=true
GMAIL_DESTINATION=you@gmail.com

# Tuning (optional)
CHECK_INTERVAL_MINUTES=5
MAX_EMAILS_PER_RUN=50
THROTTLE_EMAILS_PER_MINUTE=10
LOG_LEVEL=INFO
```

> **Tip:** Add more accounts by duplicating the `POP3_ACCOUNT_*` block with an incremented number (`POP3_ACCOUNT_2_*`, `POP3_ACCOUNT_3_*`, etc.).

### 2. Docker Compose file

The repository ships `docker-compose.yml` for this mode. Here is the content for reference:

```yaml
version: "3.8"

services:
  pop3-forwarder:
    # Build from source
    build: .
    # Or use the pre-built image:
    # image: ghcr.io/christianlouis/pop_puller_to_gmail:latest
    container_name: pop3-gmail-forwarder
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - CHECK_INTERVAL_MINUTES=${CHECK_INTERVAL_MINUTES:-5}
      - MAX_EMAILS_PER_RUN=${MAX_EMAILS_PER_RUN:-50}
      - THROTTLE_EMAILS_PER_MINUTE=${THROTTLE_EMAILS_PER_MINUTE:-10}
    volumes:
      - ./logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. Start

```bash
docker compose up -d
docker compose logs -f    # watch the output
```

The forwarder will check for new mail every 5 minutes (configurable) and forward messages to your Gmail inbox.

---

## Option 2 — Full SaaS Stack with Docker Compose

The SaaS stack gives you a multi-user web application with a React frontend, FastAPI backend, PostgreSQL database, Redis cache, and Celery workers for background email processing.

### 1. Generate secrets

```bash
# Generate a 64-character hex secret for JWT signing
openssl rand -hex 32
# Generate a separate key for encrypting stored credentials
openssl rand -hex 32
```

Save both values — you will need them below.

### 2. Create the backend environment file

```bash
cd pop_puller_to_gmail
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```ini
# ── Database ──────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://postgres:change-me@postgres:5432/pop3_forwarder

# ── Security (paste the values you generated above) ──────
SECRET_KEY=<your-64-char-hex-secret>
ENCRYPTION_KEY=<your-64-char-hex-encryption-key>

# ── Redis / Celery ───────────────────────────────────────
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ── Google OAuth (optional — see setup section below) ────
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# GOOGLE_REDIRECT_URI=https://your-domain.com/auth/callback/google

# ── CORS (include your frontend URL) ────────────────────
CORS_ORIGINS=http://localhost:3000

# ── Admin account (created on first startup) ─────────────
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-to-a-strong-password

# ── Application ─────────────────────────────────────────
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
```

### 3. Production Docker Compose file

Below is a production-ready `docker-compose.prod.yml`. It is based on the `docker-compose.new.yml` that ships with the repository, hardened for production use:

```yaml
version: "3.8"

services:
  # ── PostgreSQL ───────────────────────────────────────────
  postgres:
    image: postgres:15-alpine
    container_name: pop3-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: change-me          # must match DATABASE_URL
      POSTGRES_DB: pop3_forwarder
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    # Do NOT expose the port in production unless you need
    # external access — keep it on the internal network only.
    # ports:
    #   - "5432:5432"

  # ── Redis ────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: pop3-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── FastAPI Backend ──────────────────────────────────────
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: pop3-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  # ── Celery Worker ────────────────────────────────────────
  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: pop3-celery-worker
    restart: unless-stopped
    env_file:
      - ./backend/.env
    depends_on:
      - backend
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  # ── Celery Beat (scheduler) ─────────────────────────────
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: pop3-celery-beat
    restart: unless-stopped
    env_file:
      - ./backend/.env
    depends_on:
      - backend
    command: celery -A app.workers.celery_app beat --loglevel=info
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  # ── Next.js Frontend ────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: pop3-frontend
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

### 4. Build and start

```bash
# Build all images
docker compose -f docker-compose.prod.yml build

# Start in detached mode
docker compose -f docker-compose.prod.yml up -d

# Verify all services are healthy
docker compose -f docker-compose.prod.yml ps
```

### 5. Verify

```bash
# Backend health check
curl http://localhost:8000/health

# Open the frontend
open http://localhost:3000

# Watch logs
docker compose -f docker-compose.prod.yml logs -f
```

### 6. Create the first admin account

If you set `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `backend/.env`, an admin account is created automatically on first startup. Otherwise you can register via the API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your-password","full_name":"Your Name"}'
```

---

## Option 3 — Kubernetes Deployment

Below is a set of example Kubernetes manifests to get you started. Adapt namespaces, resource limits, and Ingress rules to your cluster.

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pop3-forwarder
```

### Secrets

Store sensitive values in a Kubernetes Secret. In production, consider using an external secret manager (e.g., HashiCorp Vault, AWS Secrets Manager, or Sealed Secrets).

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pop3-forwarder-secrets
  namespace: pop3-forwarder
type: Opaque
stringData:
  SECRET_KEY: "<your-64-char-hex-secret>"
  ENCRYPTION_KEY: "<your-64-char-hex-encryption-key>"
  DATABASE_URL: "postgresql+asyncpg://postgres:change-me@postgres:5432/pop3_forwarder"
  REDIS_URL: "redis://redis:6379/0"
  CELERY_BROKER_URL: "redis://redis:6379/0"
  CELERY_RESULT_BACKEND: "redis://redis:6379/0"
  ADMIN_EMAIL: "admin@example.com"
  ADMIN_PASSWORD: "change-this-to-a-strong-password"
  POSTGRES_PASSWORD: "change-me"
  # Optional
  # GOOGLE_CLIENT_ID: ""
  # GOOGLE_CLIENT_SECRET: ""
```

### PostgreSQL

For production, consider a managed database (RDS, Cloud SQL, etc.) or an operator such as [CloudNativePG](https://cloudnative-pg.io/). The manifest below is a simple single-instance deployment for getting started:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: pop3-forwarder
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_USER
              value: postgres
            - name: POSTGRES_DB
              value: pop3_forwarder
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: pop3-forwarder-secrets
                  key: POSTGRES_PASSWORD
          volumeMounts:
            - name: pgdata
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "postgres"]
            initialDelaySeconds: 5
            periodSeconds: 10
      volumes:
        - name: pgdata
          persistentVolumeClaim:
            claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: pop3-forwarder
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
      targetPort: 5432
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: pop3-forwarder
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

### Redis

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: pop3-forwarder
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command: ["redis-server", "--appendonly", "yes"]
          ports:
            - containerPort: 6379
          readinessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: pop3-forwarder
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
```

### Backend API

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: pop3-forwarder
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      initContainers:
        - name: run-migrations
          image: ghcr.io/christianlouis/pop_puller_to_gmail-backend:latest
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - secretRef:
                name: pop3-forwarder-secrets
          env:
            - name: DEBUG
              value: "false"
      containers:
        - name: backend
          image: ghcr.io/christianlouis/pop_puller_to_gmail-backend:latest
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: pop3-forwarder-secrets
          env:
            - name: HOST
              value: "0.0.0.0"
            - name: PORT
              value: "8000"
            - name: DEBUG
              value: "false"
            - name: LOG_LEVEL
              value: "INFO"
            - name: CORS_ORIGINS
              value: "https://your-domain.com"
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: pop3-forwarder
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
```

### Celery Worker

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
  namespace: pop3-forwarder
spec:
  replicas: 2
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
        - name: worker
          image: ghcr.io/christianlouis/pop_puller_to_gmail-backend:latest
          command:
            - celery
            - -A
            - app.workers.celery_app
            - worker
            - --loglevel=info
            - --concurrency=2
          envFrom:
            - secretRef:
                name: pop3-forwarder-secrets
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 512Mi
```

### Celery Beat (scheduler)

Only one replica should run Celery Beat at a time:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-beat
  namespace: pop3-forwarder
spec:
  replicas: 1          # Must be exactly 1
  strategy:
    type: Recreate     # Avoid two schedulers running simultaneously
  selector:
    matchLabels:
      app: celery-beat
  template:
    metadata:
      labels:
        app: celery-beat
    spec:
      containers:
        - name: beat
          image: ghcr.io/christianlouis/pop_puller_to_gmail-backend:latest
          command:
            - celery
            - -A
            - app.workers.celery_app
            - beat
            - --loglevel=info
          envFrom:
            - secretRef:
                name: pop3-forwarder-secrets
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 250m
              memory: 256Mi
```

### Frontend

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: pop3-forwarder
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: ghcr.io/christianlouis/pop_puller_to_gmail-frontend:latest
          ports:
            - containerPort: 3000
          env:
            - name: NEXT_PUBLIC_API_URL
              value: "https://api.your-domain.com"
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: pop3-forwarder
spec:
  selector:
    app: frontend
  ports:
    - port: 3000
      targetPort: 3000
```

### Ingress

The Ingress below assumes you have an Ingress controller installed (e.g., [ingress-nginx](https://kubernetes.github.io/ingress-nginx/)) and [cert-manager](https://cert-manager.io/) for automatic TLS certificates:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pop3-forwarder-ingress
  namespace: pop3-forwarder
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - your-domain.com
        - api.your-domain.com
      secretName: pop3-forwarder-tls
  rules:
    - host: your-domain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
    - host: api.your-domain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
```

### Helm chart idea

If you manage many environments (staging, production, etc.) consider wrapping the manifests above into a Helm chart:

```text
helm/pop3-forwarder/
├── Chart.yaml
├── values.yaml            # defaults for all environments
├── values-staging.yaml
├── values-production.yaml
└── templates/
    ├── namespace.yaml
    ├── secret.yaml
    ├── postgres.yaml
    ├── redis.yaml
    ├── backend-deployment.yaml
    ├── backend-service.yaml
    ├── celery-worker.yaml
    ├── celery-beat.yaml
    ├── frontend-deployment.yaml
    ├── frontend-service.yaml
    └── ingress.yaml
```

Key values to parameterize in `values.yaml`:

```yaml
replicaCount:
  backend: 2
  celeryWorker: 2
  frontend: 2

image:
  backend: ghcr.io/christianlouis/pop_puller_to_gmail-backend
  frontend: ghcr.io/christianlouis/pop_puller_to_gmail-frontend
  tag: latest

ingress:
  enabled: true
  host: your-domain.com
  apiHost: api.your-domain.com
  tls: true
  clusterIssuer: letsencrypt-prod

resources:
  backend:
    requests: { cpu: 250m, memory: 256Mi }
    limits:   { cpu: "1",  memory: 512Mi }

postgres:
  # Set to false when using an external/managed database
  enabled: true
  storage: 10Gi

redis:
  enabled: true
```

---

## Google OAuth and Gmail API Setup

If you want Google sign-in or direct Gmail API email injection (instead of SMTP), follow these steps:

### 1. Create a Google Cloud project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Navigate to **APIs & Services → Library**.
4. Enable the **Gmail API**.

### 2. Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External** (or **Internal** if you have a Google Workspace org).
3. Fill in the required fields (app name, user-support email, developer contact).
4. Under **Scopes**, add:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/gmail.insert` *(for Gmail API injection)*
   - `https://www.googleapis.com/auth/gmail.labels`

### 3. Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. Application type: **Web application**.
4. Add **Authorized redirect URIs**:
   - Development: `http://localhost:3000/auth/callback/google`
   - Production: `https://your-domain.com/auth/callback/google`
5. Copy the **Client ID** and **Client Secret**.

### 4. Configure the application

Add these to `backend/.env`:

```ini
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-domain.com/auth/callback/google
GMAIL_API_ENABLED=true
```

---

## Reverse Proxy and TLS

In production you should place a reverse proxy in front of the backend and frontend to handle TLS termination.

### Example: nginx

```nginx
# /etc/nginx/sites-available/pop3-forwarder

# Frontend
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Backend API
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Generate certificates with Let's Encrypt:

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d api.your-domain.com
```

### Example: Traefik (Docker Compose add-on)

If you prefer Traefik, add it as a service in your Compose file and use labels on the `backend` and `frontend` services. Traefik handles TLS via Let's Encrypt automatically.

---

## Environment Variable Reference

### Legacy mode (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `POP3_ACCOUNT_N_HOST` | Yes | — | POP3 server hostname (N = 1, 2, 3…) |
| `POP3_ACCOUNT_N_PORT` | No | `995` | POP3 server port |
| `POP3_ACCOUNT_N_USER` | Yes | — | POP3 username |
| `POP3_ACCOUNT_N_PASSWORD` | Yes | — | POP3 password |
| `POP3_ACCOUNT_N_USE_SSL` | No | `true` | Use SSL for POP3 |
| `SMTP_HOST` | Yes | — | SMTP server (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | Yes | — | SMTP port (e.g., `587`) |
| `SMTP_USER` | Yes | — | SMTP username |
| `SMTP_PASSWORD` | Yes | — | SMTP password / App Password |
| `SMTP_USE_TLS` | No | `true` | Use TLS for SMTP |
| `GMAIL_DESTINATION` | Yes | — | Destination Gmail address |
| `CHECK_INTERVAL_MINUTES` | No | `5` | Minutes between polling cycles |
| `MAX_EMAILS_PER_RUN` | No | `50` | Max emails forwarded per cycle |
| `THROTTLE_EMAILS_PER_MINUTE` | No | `10` | Rate limit |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `POSTMARK_API_TOKEN` | No | — | Postmark token for error alerts |
| `POSTMARK_FROM_EMAIL` | No | — | Sender for error alerts |
| `POSTMARK_TO_EMAIL` | No | — | Recipient for error alerts |

### SaaS mode (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `SECRET_KEY` | Yes | — | JWT signing key (≥ 32 chars) |
| `ENCRYPTION_KEY` | Yes | — | Credential encryption key (≥ 32 chars) |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection string |
| `CELERY_BROKER_URL` | Yes | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | Yes | `redis://localhost:6379/0` | Celery result backend URL |
| `CORS_ORIGINS` | Yes | `http://localhost:3000` | Comma-separated allowed origins |
| `ADMIN_EMAIL` | No | — | Auto-created admin email |
| `ADMIN_PASSWORD` | No | — | Auto-created admin password |
| `GOOGLE_CLIENT_ID` | No | — | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | — | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | No | `http://localhost:3000/auth/callback/google` | OAuth redirect URI |
| `GMAIL_API_ENABLED` | No | `true` | Enable Gmail API injection |
| `DEBUG` | No | `false` | Enable debug mode |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `HOST` | No | `0.0.0.0` | Bind address |
| `PORT` | No | `8000` | Bind port |
| `STRIPE_API_KEY` | No | — | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | No | — | Stripe webhook secret |
| `MAX_EMAILS_PER_RUN` | No | `50` | Max emails per account per cycle |
| `CHECK_INTERVAL_MINUTES` | No | `5` | Minutes between polling cycles |
| `THROTTLE_EMAILS_PER_MINUTE` | No | `10` | Rate limit |

---

## Upgrading

```bash
cd pop_puller_to_gmail

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# The backend init container / startup command runs migrations automatically.
# To run them manually:
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs for the failing service
docker compose -f docker-compose.prod.yml logs backend

# Common causes:
# - DATABASE_URL is wrong or PostgreSQL isn't ready yet
# - SECRET_KEY or ENCRYPTION_KEY is shorter than 32 characters
# - Port conflict on the host
```

### Frontend can't reach the backend (CORS errors)

1. Ensure `CORS_ORIGINS` in `backend/.env` includes the frontend URL exactly (protocol + host + port).
2. Verify the backend is reachable from the frontend container: `docker compose exec frontend wget -qO- http://backend:8000/health`.

### Emails aren't being forwarded

1. Check Celery worker logs: `docker compose -f docker-compose.prod.yml logs celery-worker`.
2. Verify Redis is running: `docker compose -f docker-compose.prod.yml exec redis redis-cli ping`.
3. Confirm POP3 credentials are correct by testing manually.

### Database migration errors

```bash
# Check current migration state
docker compose -f docker-compose.prod.yml exec backend alembic current

# Show migration history
docker compose -f docker-compose.prod.yml exec backend alembic history

# If stuck, you may need to stamp the current head
docker compose -f docker-compose.prod.yml exec backend alembic stamp head
```

### OAuth redirect mismatch

The `GOOGLE_REDIRECT_URI` in `backend/.env` must **exactly** match one of the authorized redirect URIs configured in the Google Cloud Console (including protocol, host, port, and path).

---

## Further Reading

- [QUICKSTART.md](QUICKSTART.md) — Get running in under 10 minutes (legacy mode)
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) — Pre-deployment and post-deployment checklists
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture and component overview
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) — Upgrading from v1 (legacy) to v2 (SaaS)
- [SECURITY_SUMMARY.md](SECURITY_SUMMARY.md) — Security best practices
