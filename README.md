# Null

**Remote dominion over your XCP-ng infrastructure. Minimal. Complete. Unforgiving.**

A lightweight, feature-complete web interface for managing XCP-ng pools —
designed to be self-hosted in Docker, connected to your XCP-ng infrastructure.

![License: AGPL v3](https://img.shields.io/badge/license-AGPL%20v3-blue.svg)
![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)
![Python: 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)
![React: 19](https://img.shields.io/badge/react-19-61dafb.svg)

---

## Overview

Null provides a web-based GUI for managing XCP-ng virtualization
hosts. It communicates directly with the XCP-ng XAPI (XML-RPC over HTTPS),
giving you full control over VMs, storage, networking, and hosts — all from
your browser.

### Why another management tool?

While Xen Orchestra (XO) is excellent, Null is designed for users
who want:
- **Self-contained** — single Docker Compose file, no appliance VM needed
- **Lightweight** — SQLite for persistence, minimal resource footprint
- **Hackable** — clean Python/FastAPI backend + React frontend, easy to extend
- **Multi-pool** — manage multiple XCP-ng pools from one dashboard
- **Documentation-first** — every feature is documented, with built-in help

### Screenshots

*(Coming soon — Phase 1 is backend/API foundation)*

---

## Features

### Phase 1 — Foundation ✅
- [x] Multi-user authentication (JWT + local SQLite user DB)
- [x] Multi-pool connection management (add/edit/delete/test XCP-ng pools)
- [x] User management (create/delete users, role-based access)
- [x] Audit logging (every management action recorded)
- [x] REST API with auto-generated OpenAPI docs
- [x] Dark-themed React dashboard with sidebar navigation
- [x] Docker Compose deployment (backend + frontend)

### Phase 2 — VM Management 🚧
- [ ] VM list with filtering/searching
- [ ] VM create wizard (template-based)
- [ ] VM lifecycle (start, stop, pause, suspend, reboot, force reboot)
- [ ] Live migration between hosts
- [ ] In-browser VNC console (noVNC)
- [ ] VM detail view (disks, NICs, metrics)

### Phase 3 — Storage & Networking 🚧
- [ ] Storage Repository management (create, destroy, rescan)
- [ ] Virtual Disk management (VDI create, resize, attach/detach)
- [ ] Network management (create, destroy, VLAN, bond)
- [ ] Virtual NIC management (VIF attach/detach, IP config)

### Phase 4 — Advanced 🚧
- [ ] Snapshots and snapshot trees
- [ ] Real-time metrics charts
- [ ] WebSocket events (live updates)
- [ ] Advanced audit log viewer

### Phase 5 — Polish 🚧
- [ ] Built-in help & tutorials
- [ ] Tag system for VMs/hosts
- [ ] Diff viewer for configuration changes
- [ ] VM export/import profiles

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                         │
│  ┌────────────────────┐     ┌────────────────────────┐  │
│  │  Frontend (React)  │────▶│  Backend (FastAPI)     │  │
│  │  Vite :3000        │     │  uvicorn :8000         │  │
│  │                    │     │                        │  │
│  │  • Dashboard       │     │  • REST API            │  │
│  │  • VM Manager      │     │  • XAPI XML-RPC client │  │
│  │  • Storage         │     │  • SQLite (users/logs) │──┼──▶ data/xcpng-gui.db
│  │  • Networking      │     │  • JWT Auth            │  │
│  │  • Console (noVNC) │     │  • Plugin system       │  │
│  └────────────────────┘     └───────────┬────────────┘  │
│                                         │               │
└─────────────────────────────────────────┼───────────────┘
                                          │ XML-RPC/HTTPS
                                          ▼
                               ┌─────────────────────┐
                               │  XCP-ng Pool Master │
                               │  XAPI (port 443)    │
                               └─────────────────────┘
```

- **Backend:** Python 3.13, FastAPI, SQLite, xmlrpc.client (stdlib)
- **Frontend:** React 19, Vite 6, custom dark theme CSS
- **Auth:** JWT tokens, bcrypt password hashing
- **XAPI:** XML-RPC over HTTPS to XCP-ng pool master
- **Persistence:** Single-file SQLite database (users, pools, audit log)

See [docs/architecture.md](docs/architecture.md) for detailed design.

---

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose** (for containerized deployment)
- **Node.js 22+** and **Python 3.13+** with `uv` (for local development)
- A running **XCP-ng 8.2 or 8.3** pool (for actual management)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/xcpng-manager.git
cd xcpng-manager

# Copy and edit environment
cp .env.example .env
# Edit .env — set XCPNG_MANAGER_SECRET to a strong random string

# Build and start
docker compose up -d

# Open in browser
open http://localhost:3000
```

Default login: **admin** / **admin** (change immediately).

### Option 2: Local Development

```bash
# Install dependencies
make setup

# Start backend (terminal 1)
make dev-backend
# → http://localhost:8000/docs  (API docs)

# Start frontend (terminal 2)
make dev-frontend
# → http://localhost:3000        (UI)
```

### First Steps

1. Log in at http://localhost:3000 with `admin` / `admin`
2. Go to **Settings** → add your XCP-ng pool (host, username, password)
3. Click **Test** to verify the connection
4. Go to **Dashboard** to see your pool status

See [docs/quickstart.md](docs/quickstart.md) for detailed setup guide.

---

## API Documentation

When the backend is running, interactive API docs are available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Authenticate, get JWT token |
| GET  | `/api/auth/me` | Current user info |
| GET  | `/api/pools` | List configured pools |
| POST | `/api/pools` | Add a new pool |
| POST | `/api/pools/{id}/connect` | Test connection to a pool |
| GET  | `/api/users` | List users (admin only) |
| POST | `/api/users` | Create user (admin only) |
| GET  | `/api/audit` | View audit log |

See [docs/api-reference.md](docs/api-reference.md) for complete API reference.

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `XCPNG_MANAGER_SECRET` | *(required)* | JWT signing secret (use a strong random string) |
| `XCPNG_DB_PATH` | `data/xcpng-gui.db` | SQLite database file path |
| `XCPNG_TOKEN_EXPIRE` | `480` | JWT token expiry in minutes (8 hours) |

---

## Project Structure

```
xcpng-manager/
├── docker-compose.yml       # Docker deployment
├── Makefile                 # Convenience commands
├── README.md                # This file
├── docs/                    # Documentation
│   ├── quickstart.md
│   ├── architecture.md
│   ├── api-reference.md
│   └── contributing.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI entry point
│       ├── config.py        # Settings
│       ├── database.py      # SQLite schema
│       ├── auth.py          # JWT + user management
│       ├── xapi/            # XAPI XML-RPC client
│       │   └── client.py    # Pool connection, XAPI calls
│       ├── routes/          # API route modules
│       │   ├── auth.py      # Login/logout
│       │   ├── users.py     # User CRUD
│       │   ├── pools.py     # Pool management
│       │   ├── health.py    # Health checks
│       │   └── audit.py     # Audit log
│       └── plugins/         # Plugin system
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx          # Root component
│       ├── api/client.js    # API client
│       ├── context/         # React contexts
│       ├── components/      # Reusable UI
│       ├── pages/           # Route pages
│       └── styles/          # CSS
└── data/                    # SQLite database (gitignored)
```

---

## Contributing

See [docs/contributing.md](docs/contributing.md) for guidelines.

## Roadmap

- **v0.1.0** — Phase 1: Auth, multi-pool, dashboard (current)
- **v0.2.0** — Phase 2: VM lifecycle, console
- **v0.3.0** — Phase 3: Storage & networking
- **v0.4.0** — Phase 4: Snapshots, metrics, events
- **v0.5.0** — Phase 5: Polish, docs, tutorial
- **v1.0.0** — Production-ready release

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE) file.

This is a strong copyleft license designed for network-facing software.
If you modify this program and make it available as a service over a
network, you must make your modified source code available to users.

---

Built with ❤️ for the XCP-ng community.
