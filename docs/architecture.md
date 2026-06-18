# Architecture

Null is a single-container application — FastAPI serves both the React SPA
and REST API from one process, communicating with XCP-ng via XAPI XML-RPC.

## High-Level Design

```
                     Browser (http://localhost:8000)
                              │
                              ▼
              ┌───────────────────────────────┐
              │     Null (single container)    │
              │     FastAPI + uvicorn :8000    │
              │                              │
              │  ┌────────────────────────┐  │
              │  │ React SPA (static)     │  │
              │  │ served at /            │  │
              │  └────────────────────────┘  │
              │  ┌────────────────────────┐  │
              │  │ REST API (/api/*)      │  │
              │  │  Auth, Pools, VMs,     │  │
              │  │  Storage, Network, etc │  │
              │  └────────────────────────┘  │
              │  ┌────────────────────────┐  │
              │  │ XAPI Client Layer      │  │
              │  │ PoolConnection         │  │
              │  │ PoolRegistry           │  │
              │  └───────────┬────────────┘  │
              │              │               │
              │  ┌───────────▼────────────┐  │
              │  │ SQLite (null.db)       │  │
              │  │ users, pools, audit    │  │
              │  └────────────────────────┘  │
              └──────────────┼───────────────┘
                             │ XML-RPC / HTTPS
                             ▼
              ┌───────────────────────────────┐
              │     XCP-ng Pool Master        │
              │     XAPI :443                 │
              └───────────────────────────────┘
```

## Deployment

**Single image, single port, zero internal networking.**

```bash
docker run -p 8000:8000 ghcr.io/shniranjan/null:latest
```

Multi-arch: `linux/amd64` and `linux/arm64` (Raspberry Pi, AWS Graviton).

## Key Components

### 1. FastAPI Application

The single process serves both the React SPA (static files at `/`) and the
REST API (`/api/*`). In development, Vite dev server proxies `/api` to the
backend. In production, the built frontend is served by FastAPI's StaticFiles.

**Why FastAPI?**
- Native async support (WebSocket for real-time events)
- Automatic OpenAPI docs (/docs, /redoc)
- Pydantic models for request/response validation
- Fast, lightweight, well-documented

**Why SQLite?**
- Zero configuration — single file, no daemon
- Sufficient for management tool scale (not handling VM I/O)
- Easy backup (copy the .db file)
- Built into Python stdlib

**XAPI Communication:**
- Uses Python's `xmlrpc.client` (stdlib, zero dependencies)
- XAPI sessions are established per-pool via `session.login_with_password()`
- Session refs are cached in-memory in `PoolConnection` objects
- Failed calls trigger auto-reconnect (session expiry handling)


Simple React SPA with:
- **State-based routing** (no react-router needed at this scale)
- **AuthContext** wrapping the entire app for auth state
- **apiFetch** wrapper that auto-attaches JWT and handles 401
- **CSS custom properties** for dark theme consistency

### 3. Multi-Pool Architecture

The backend maintains `PoolRegistry` — an in-memory dict of
`PoolConnection` instances, keyed by pool ID from the database.

```
PoolRegistry {
  1 → PoolConnection(pool_id=1, host="prod-pool.local", ...)
  2 → PoolConnection(pool_id=2, host="lab-pool.local", ...)
}
```

Each `PoolConnection` manages its own XAPI session independently.
Pools can be added/removed without affecting others.

### 4. Authentication

Authentication uses JWT tokens with bcrypt password hashing. Tokens expire after a configurable duration. All API requests (except login) require a valid token.

### 5. Audit Logging

Every management action (pool add, VM start, etc.) writes to `audit_log`:

```sql
INSERT INTO audit_log (user_id, username, pool_id, action, target_type, ...)
```

This provides a complete, immutable record of who did what, when.

## Data Flow: VM Operation Example

```
User clicks "Start VM" in UI
         │
         ▼
Frontend: api.post("/vms/{ref}/start")
         │
         ▼
Backend: pool.call("VM.start", vm_ref)
         │
         ▼
XAPI: VM.start(session_ref, vm_ref)
         │
         ▼
Xen Hypervisor: boots the VM
         │
         ▼
Backend: INSERT INTO audit_log (...)
         │
         ▼
Frontend: updates VM state to "Running"
```

## Security Considerations

- **JWT tokens** expire after 8 hours (configurable)
- **bcrypt** for password hashing (never stored in plaintext)
- **Pool passwords** stored securely (encrypted-at-rest coming in v1.0)
- **HTTPS** between backend and XCP-ng (SSL verification optional)
- **CORS** restricted to known frontend origins
- **No default exposed ports** beyond 8000/8000 (use reverse proxy for production)

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State management | React Context | Simple, no Redux overhead needed |
| Routing | State-based switch | 8 pages, react-router is overkill |
| API client | Custom fetch wrapper | Lightweight, full control over auth |
| CSS | Plain CSS with variables | No Tailwind, no CSS-in-JS overhead |
| Build tool | Vite | Fastest dev server, ES modules native |
| Backend framework | FastAPI | Async, OpenAPI auto-docs, WebSocket |
| Database | SQLite | Single file, zero config, sufficient scale |
| XAPI transport | xmlrpc.client | Python stdlib, no external SDK |
| Auth | python-jose + passlib | Well-audited JWT + bcrypt |
