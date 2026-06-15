# Quick Start Guide

This guide walks you through setting up Null from zero to managing your first pool.

## Prerequisites

### For Docker deployment (recommended)
- Docker Engine 24+ and Docker Compose v2
- 512 MB RAM, 1 GB disk space for the containers
- Network access to your XCP-ng pool master (port 443)

### For local development
- Python 3.13+ with [uv](https://github.com/astral-sh/uv)
- Node.js 22+ with npm
- Network access to your XCP-ng pool master

### XCP-ng requirements
- XCP-ng 8.2 LTS or 8.3 LTS
- Pool master accessible over HTTPS (port 443)
- Root or admin credentials for XAPI access
- SSL certificate verification can be disabled for self-signed certs

---

## Option 1: Docker Deployment

### 1. Clone the repository

```bash
git clone https://github.com/shniranjan/null.git
cd null
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set a strong secret:

```bash
# Generate a random secret
openssl rand -hex 32
# Paste the output into .env
XCPNG_MANAGER_SECRET=<your-random-hex>
```

### 3. Build and start

```bash
docker compose up -d
```

This builds and starts a single container:
- `null` — serves the UI and REST API

### 4. Open the UI

Navigate to **http://localhost:8000**

Default login: `admin` / `admin`

**⚠️ Change the admin password immediately** (Settings → Users).

### 5. Add your XCP-ng pool

1. Go to **Settings** (⚙ in sidebar)
2. Under "XCP-ng Pools", click **+ Add Pool**
3. Fill in:
   - **Pool Name:** e.g., "Production" or "Home Lab"
   - **Host:** IP or hostname of your XCP-ng pool master
   - **Port:** 443 (default)
   - **Username:** `root` (or your XAPI user)
   - **Password:** XCP-ng root password
   - **Verify SSL:** Uncheck if using self-signed certificates (common in homelabs)
4. Click **Save Pool**
5. Click **Test** to verify the connection

If successful, you'll see the host count. Your pool is now connected!

### 6. Explore

- **Dashboard** — Pool overview and quick actions
- **Virtual Machines** — (Coming in Phase 2)
- **Audit Log** — All management actions are logged here

---

## Option 2: Local Development

### 1. Clone and install

```bash
git clone https://github.com/shniranjan/null.git
cd null
make setup
```

This installs:
- Python virtual environment with FastAPI + dependencies
- Node.js dependencies for the React frontend

### 2. Start the backend

```bash
make dev-backend
```

The backend starts on **http://localhost:8000**.

API docs available at http://localhost:8000/docs (Swagger UI).

### 3. Start the frontend (separate terminal)

```bash
make dev-frontend
```

The frontend starts on **http://localhost:8000**.

Vite proxies `/api` requests to the backend automatically.

### 4. Login and configure

Same as Docker steps 4–6 above.

---

## Troubleshooting

### "Connection failed" when testing pool

1. **Verify network:** Can you reach the XCP-ng host from the Docker container?
   ```bash
   docker exec null curl -k https://<xcpng-host>/
   ```

2. **Self-signed certificates:** Uncheck "Verify SSL" in pool settings. XCP-ng
   installations use self-signed certs by default.

3. **Firewall:** Ensure port 443 is open on the XCP-ng host.

4. **XAPI status:** On the XCP-ng host, restart the toolstack:
   ```bash
   xe-toolstack-restart
   ```

### "Module not found" when starting backend locally

```bash
cd backend && source .venv/bin/activate && uv pip install -r requirements.txt
```

### Database issues

Reset the database (⚠️ destructive — removes all users and pool configs):
```bash
make db-reset
# Restart backend to recreate with default admin/admin
```

### Frontend can't reach backend (Docker)

By default, the frontend proxies `/api` to `http://backend:8000` (Docker
internal DNS). If you're accessing the frontend directly on the host, ensure:
- The backend port 8000 is exposed
- Set `VITE_API_URL=http://localhost:8000` in the frontend environment

---

## Next Steps

- [Architecture Overview](architecture.md) — understand how the system works
- [API Reference](api-reference.md) — full REST API documentation
- [Contributing](contributing.md) — how to help develop
