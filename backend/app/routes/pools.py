"""
Pool connection management.

GET    /api/pools              — list saved pools
POST   /api/pools              — add new pool
GET    /api/pools/{id}         — get pool detail
PUT    /api/pools/{id}         — update pool config
DELETE /api/pools/{id}         — remove pool
POST   /api/pools/{id}/connect — test/establish connection
GET    /api/pools/{id}/status  — connection status
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import UserOut, get_current_user
from app.database import get_db
from app.xapi.client import PoolConnection, pool_registry

router = APIRouter(prefix="/api/pools", tags=["pools"])


class PoolCreate(BaseModel):
    name: str
    host: str
    port: int = 443
    verify_ssl: bool = False
    username: str = "root"
    password: str = ""


class PoolUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    port: int | None = None
    verify_ssl: bool | None = None
    username: str | None = None
    password: str | None = None


class PoolOut(BaseModel):
    id: int
    name: str
    host: str
    port: int
    verify_ssl: bool
    username: str
    last_connected: str | None = None
    status: str


def row_to_pool(row) -> PoolOut:
    d = dict(row)
    # Never expose password to frontend
    d.pop("password_enc", None)
    return PoolOut(**d)


@router.get("", response_model=list[PoolOut])
async def list_pools(current_user: UserOut = Depends(get_current_user)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM pools ORDER BY name").fetchall()
    conn.close()
    return [row_to_pool(r) for r in rows]


@router.post("", response_model=PoolOut, status_code=status.HTTP_201_CREATED)
async def create_pool(body: PoolCreate, current_user: UserOut = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO pools (name, host, port, verify_ssl, username, password_enc, status)
           VALUES (?, ?, ?, ?, ?, ?, 'disconnected')""",
        (body.name, body.host, body.port, int(body.verify_ssl), body.username, body.password),
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM pools WHERE id = ?", (new_id,)).fetchone()
    conn.close()

    # Register in-memory
    pool_registry.register(PoolConnection(
        pool_id=new_id,
        name=body.name,
        host=body.host,
        port=body.port,
        username=body.username,
        password=body.password,
        verify_ssl=body.verify_ssl,
    ))

    return row_to_pool(row)


@router.get("/{pool_id}", response_model=PoolOut)
async def get_pool(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT * FROM pools WHERE id = ?", (pool_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Pool not found")
    return row_to_pool(row)


@router.put("/{pool_id}", response_model=PoolOut)
async def update_pool(
    pool_id: int,
    body: PoolUpdate,
    current_user: UserOut = Depends(get_current_user),
):
    conn = get_db()
    row = conn.execute("SELECT * FROM pools WHERE id = ?", (pool_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Pool not found")

    d = dict(row)
    updates = {}
    for field in ("name", "host", "port", "verify_ssl", "username", "password"):
        val = getattr(body, field, None)
        if val is not None:
            key = "password_enc" if field == "password" else field
            updates[key] = val if field != "verify_ssl" else int(val)

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        conn.execute(
            f"UPDATE pools SET {set_clause} WHERE id = ?",
            (*updates.values(), pool_id),
        )
        conn.commit()

    row = conn.execute("SELECT * FROM pools WHERE id = ?", (pool_id,)).fetchone()
    conn.close()

    # Update in-memory if registered
    existing = pool_registry.get(pool_id)
    if existing:
        existing.disconnect()
        pool_registry.remove(pool_id)
        d2 = dict(row)
        pool_registry.register(PoolConnection(
            pool_id=pool_id,
            name=d2["name"],
            host=d2["host"],
            port=d2["port"],
            username=d2["username"],
            password=d2["password_enc"],
            verify_ssl=bool(d2["verify_ssl"]),
        ))

    return row_to_pool(row)


@router.delete("/{pool_id}")
async def delete_pool(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT id FROM pools WHERE id = ?", (pool_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Pool not found")
    conn.execute("DELETE FROM pools WHERE id = ?", (pool_id,))
    conn.commit()
    conn.close()
    pool_registry.remove(pool_id)
    return {"status": "ok", "deleted_id": pool_id}


@router.post("/{pool_id}/connect")
async def connect_pool(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    """Test and establish a connection to the pool."""
    conn = get_db()
    row = conn.execute("SELECT * FROM pools WHERE id = ?", (pool_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Pool not found")

    d = dict(row)
    pc = PoolConnection(
        pool_id=pool_id,
        name=d["name"],
        host=d["host"],
        port=d["port"],
        username=d["username"],
        password=d["password_enc"],
        verify_ssl=bool(d["verify_ssl"]),
    )

    try:
        pc.connect()
        hosts = pc.get_hosts()
        host_count = len(hosts)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE pools SET last_connected = ?, status = 'connected' WHERE id = ?",
            (now, pool_id),
        )
        conn.commit()

        # Register in registry (replaces any existing)
        pool_registry.register(pc)

        conn.close()
        return {
            "status": "connected",
            "host_count": host_count,
            "hosts": {
                ref: {"name_label": h.get("name_label", ""), "address": h.get("address", "")}
                for ref, h in hosts.items()
            },
        }
    except Exception as e:
        conn.execute(
            "UPDATE pools SET status = 'error' WHERE id = ?",
            (pool_id,),
        )
        conn.commit()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.get("/{pool_id}/status")
async def pool_status(pool_id: int, current_user: UserOut = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute("SELECT id, status, last_connected FROM pools WHERE id = ?", (pool_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Pool not found")

    pc = pool_registry.get(pool_id)
    return {
        "pool_id": pool_id,
        "db_status": row["status"],
        "connected": pc._connected if pc else False,
        "last_connected": row["last_connected"],
    }
