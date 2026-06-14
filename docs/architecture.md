# Architecture

Null is a two-tier web application that bridges a modern React
frontend with XCP-ng's XAPI management protocol.

## High-Level Design

```
                     Browser (https://localhost:8000)
                              │
                              │ HTTPS (dev) / HTTP
                              ▼
              ┌───────────────────────────────┐
              │     Frontend (React 19)       │
              │     Vite Dev Server :8000     │
              │                              │
              │  ┌────────────────────────┐  │
              │  │ Pages:                 │  │
              │  │  Dashboard, VMs, SRs,  │  │
              │  │  Networks, Snaps, etc. │  │
              │  └────────────────────────┘  │
              │  ┌────────────────────────┐  │
              │  │ API Client:            │  │
              │  │  JWT attach, 401 retry │  │
              │  └───────────┬────────────┘  │
              └──────────────┼───────────────┘
                             │ REST (JSON)
                             │ /api/*
                             ▼
              ┌───────────────────────────────┐
              │     Backend (FastAPI)         │
              │     uvicorn :8000             │
              │                              │
              │  ┌────────────────────────┐  │
              │  │ Auth Layer:            │  │
              │  │  JWT verify → UserOut  │  │
              │  └────────────────────────┘  │
              │  ┌────────────────────────┐  │
              │  │ Route Handlers:        │  │
              │  │  /auth, /pools, /users │  │
              │  │  /vms, /storage, etc.  │  │
              │  └────────────────────────┘  │
              │  ┌────────────────────────┐  │
              │  │ XAPI Client Layer:     │  │
              │  │  PoolConnection        │  │
              │  │  PoolRegistry          │  │
              │  └───────────┬────────────┘  │
              │              │               │
              │  ┌───────────▼────────────┐  │
              │  │ SQLite                 │  │
              │  │  users, pools,         │  │
              │  │  audit_log, prefs      │  │
              │  └────────────────────────┘  │
              └──────────────┼───────────────┘
                             │ XML-RPC over HTTPS
                             │ (session.login_with_password)
                             ▼
              ┌───────────────────────────────┐
              │     XCP-ng Pool Master        │
              │     XAPI (xapi) :443          │
              │                              │
              │  ┌────────────────────────┐  │
              │  │ Xen Hypervisor         │  │
              │  └────────────────────────┘  │
              │  ┌────────────────────────┐  │
              │  │ state.db (XML)         │  │
              │  └────────────────────────┘  │
              └───────────────────────────────┘
```

## Key Components

### 1. Backend (FastAPI + SQLite)

The backend is a Python FastAPI application that serves as a REST API gateway
between the frontend and XCP-ng's XAPI.

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

### 2. Frontend (React + Vite)

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

### 4. Authentication Flow

```
[Browser]                    [Backend]                   [SQLite]
    │                            │                          │
    │  POST /api/auth/login      │                          │
    │  {username, password}      │                          │
    │ ──────────────────────────▶│                          │
    │                            │  SELECT * FROM users     │
    │                            │  WHERE username = ?      │
    │                            │ ─────────────────────────▶│
    │                            │  {id, hash, role}        │
    │                            │ ◀─────────────────────────│
    │                            │                          │
    │                            │  bcrypt.verify(pw, hash) │
    │                            │  JWT.sign({sub: id, role})│
    │                            │                          │
    │  {access_token, user}      │                          │
    │ ◀──────────────────────────│                          │
    │                            │                          │
    │  GET /api/pools            │                          │
    │  Authorization: Bearer ... │                          │
    │ ──────────────────────────▶│                          │
    │                            │  JWT.decode(token)       │
    │                            │  verify sub exists       │
    │                            │                          │
    │  [{pool1}, {pool2}]        │                          │
    │ ◀──────────────────────────│                          │
```

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
- **Pool passwords** stored in SQLite (encrypted-at-rest planned for v1.0)
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
