# API Reference

Null exposes a REST API at `http://localhost:8000/api/`.

Interactive docs: http://localhost:8000/docs (Swagger) and http://localhost:8000/redoc.

---

## Authentication

All endpoints except `/api/auth/login` require a JWT token in the
`Authorization` header:

```
Authorization: Bearer <token>
```

### POST /api/auth/login

Authenticate and receive a JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2026-06-14T12:00:00+00:00",
    "last_login": null
  }
}
```

**Errors:**
- `401` — Invalid username or password

### POST /api/auth/logout

Log out (client-side — discards the token). No request body needed.

**Response (200):**
```json
{
  "status": "ok",
  "message": "Token discarded — log out on client side"
}
```

### GET /api/auth/me

Get the current authenticated user's profile.

**Response (200):**
```json
{
  "id": 1,
  "username": "admin",
  "role": "admin",
  "created_at": "2026-06-14T12:00:00+00:00",
  "last_login": null
}
```

---

## Health

### GET /api/health

Backend health check (public, no auth required).

**Response (200):**
```json
{
  "status": "ok",
  "service": "xcpng-manager",
  "version": "0.1.0"
}
```

### GET /api/health/xcpng?pool_id=1

Test connectivity to a specific XCP-ng pool.

**Query Parameters:**
- `pool_id` (required) — Pool ID to test

**Response (200):**
```json
{
  "status": "connected",
  "host_count": 3,
  "hosts": {
    "OpaqueRef:abc123": {
      "name_label": "xcp-ng-host-01",
      "address": "192.168.1.101",
      "enabled": true
    }
  }
}
```

**Errors:**
- `404` — Pool not found or not connected
- `503` — Connection failed

---

## Pools

### GET /api/pools

List all configured XCP-ng pools.

**Response (200):**
```json
[
  {
    "id": 1,
    "name": "Production",
    "host": "192.168.1.100",
    "port": 443,
    "verify_ssl": false,
    "username": "root",
    "last_connected": "2026-06-14T12:05:00+00:00",
    "status": "connected"
  }
]
```

### POST /api/pools

Add a new XCP-ng pool configuration.

**Request:**
```json
{
  "name": "Home Lab",
  "host": "10.0.0.50",
  "port": 443,
  "verify_ssl": false,
  "username": "root",
  "password": "secret"
}
```

**Response (201):**
```json
{
  "id": 2,
  "name": "Home Lab",
  "host": "10.0.0.50",
  "port": 443,
  "verify_ssl": false,
  "username": "root",
  "last_connected": null,
  "status": "disconnected"
}
```

### GET /api/pools/{pool_id}

Get details for a specific pool.

### PUT /api/pools/{pool_id}

Update pool configuration. Only include fields you want to change.

**Request:**
```json
{
  "name": "Production (Updated)",
  "password": "new-secret"
}
```

### DELETE /api/pools/{pool_id}

Remove a pool configuration. Disconnects the active session if any.

**Response (200):**
```json
{
  "status": "ok",
  "deleted_id": 1
}
```

### POST /api/pools/{pool_id}/connect

Test and establish a connection to the pool.

**Response (200):**
```json
{
  "status": "connected",
  "host_count": 3,
  "hosts": { ... }
}
```

**Errors:**
- `503` — Connection failed (invalid host, bad credentials, network issue)

### GET /api/pools/{pool_id}/status

Get connection status for a pool (without testing).

**Response (200):**
```json
{
  "pool_id": 1,
  "db_status": "connected",
  "connected": true,
  "last_connected": "2026-06-14T12:05:00+00:00"
}
```

---

## Users

> **⚠️ All user endpoints require admin role.**

### GET /api/users

List all users.

**Response (200):**
```json
[
  {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2026-06-14T12:00:00+00:00",
    "last_login": null
  }
]
```

### POST /api/users

Create a new user.

**Request:**
```json
{
  "username": "operator",
  "password": "secure-pass",
  "role": "admin"
}
```

**Response (201):**
```json
{
  "id": 2,
  "username": "operator",
  "role": "admin",
  "created_at": "2026-06-14T12:10:00+00:00",
  "last_login": null
}
```

**Errors:**
- `409` — Username already exists

### DELETE /api/users/{user_id}

Delete a user. Cannot delete your own account.

**Errors:**
- `400` — Cannot delete your own account
- `404` — User not found

---

## Audit Log

### GET /api/audit

Get paginated audit log entries.

**Query Parameters:**
- `limit` (default 100, max 1000) — Entries per page
- `offset` (default 0) — Offset for pagination

**Response (200):**
```json
{
  "total": 42,
  "limit": 100,
  "offset": 0,
  "entries": [
    {
      "id": 1,
      "user_id": 1,
      "username": "admin",
      "pool_id": 1,
      "pool_name": "Production",
      "action": "pool.connect",
      "target_type": "pool",
      "target_name": "Production",
      "target_ref": null,
      "details": "Connected successfully — 3 hosts found",
      "timestamp": "2026-06-14T12:05:00+00:00"
    }
  ]
}
```

---

## Error Format

All errors follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

HTTP status codes:
- `200` — Success
- `201` — Created
- `400` — Bad request
- `401` — Unauthorized (missing/invalid token)
- `403` — Forbidden (insufficient role)
- `404` — Not found
- `409` — Conflict (duplicate)
- `422` — Validation error
- `503` — Service unavailable (XCP-ng connection failed)

---

## Future Endpoints (Phases 2–5)

| Method | Path | Phase | Description |
|--------|------|-------|-------------|
| GET    | `/api/vms?pool_id=` | 2 | List VMs |
| POST   | `/api/vms` | 2 | Create VM |
| POST   | `/api/vms/{ref}/start` | 2 | Start VM |
| POST   | `/api/vms/{ref}/stop` | 2 | Stop VM |
| GET    | `/api/srs?pool_id=` | 3 | List storage repositories |
| GET    | `/api/networks?pool_id=` | 3 | List networks |
| GET    | `/api/snapshots?pool_id=` | 4 | List snapshots |
| WS     | `/ws/events?pool_id=` | 4 | WebSocket event stream |
