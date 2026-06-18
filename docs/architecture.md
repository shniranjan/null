# Architecture

Null is a single-container application — FastAPI serves both the React SPA
and REST API from one process, communicating with XCP-ng via XAPI XML-RPC.

## High-Level Design

Single container: FastAPI serves the React SPA and REST API from one process. Communicates with XCP-ng hosts via XAPI XML-RPC over HTTPS. SQLite provides persistence for users, pool configs, and audit logs.

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

Every management action (pool add, VM start, etc.) is recorded with user identity, action type, target, and timestamp. This provides a complete, immutable record of who did what, when.

## Data Flow

User actions in the UI trigger API calls to the backend, which translates them into XAPI calls to the XCP-ng pool master. All mutating operations are recorded in the audit log before the UI updates to reflect the new state.

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
| Auth | JWT + bcrypt | Well-audited standard libraries |
