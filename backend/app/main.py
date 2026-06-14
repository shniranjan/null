"""
Null — FastAPI Application Entry Point

Start with:
  cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

API docs available at:
  http://localhost:8000/docs       (Swagger UI)
  http://localhost:8000/redoc      (ReDoc)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from auth import ensure_default_admin

from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.pools import router as pools_router
from routes.health import router as health_router
from routes.audit import router as audit_router
from routes.vms import router as vms_router
from routes.storage import router as storage_router
from routes.network import router as network_router
from routes.snapshots import router as snapshots_router
from routes.events import router as events_router
from routes.metrics import router as metrics_router
from routes.docs_api import router as docs_router
from routes.passthrough import router as passthrough_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Startup
    init_db()
    ensure_default_admin()

    # TODO: Load saved pools from DB into pool_registry

    yield

    # Shutdown
    from xapi.client import pool_registry
    pool_registry.shutdown_all()


app = FastAPI(
    title="Null",
    description="""
    **Docker-based remote management GUI for XCP-ng virtualization hosts.**

    ## Features

    - Multi-pool management (connect to multiple XCP-ng pools)
    - Full VM lifecycle (create, start, stop, migrate, snapshot, clone)
    - Storage management (SR, VDI, attach/detach)
    - Network management (networks, VLANs, bonds, VIFs)
    - Real-time metrics and performance charts
    - In-browser VNC console
    - Multi-user with role-based access
    - Audit logging

    ## Architecture

    This backend communicates with XCP-ng hosts via the XAPI XML-RPC protocol
    over HTTPS. It provides a REST API consumed by the React frontend.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server and Docker internal
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(pools_router)
app.include_router(health_router)
app.include_router(audit_router)
app.include_router(vms_router)
app.include_router(storage_router)
app.include_router(network_router)
app.include_router(snapshots_router)
app.include_router(events_router)
app.include_router(metrics_router)
app.include_router(docs_router)
app.include_router(passthrough_router)


@app.get("/")
async def root():
    return {
        "service": "Null",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "auth": "/api/auth/login",
            "pools": "/api/pools",
            "users": "/api/users",
            "audit": "/api/audit",
        },
    }
