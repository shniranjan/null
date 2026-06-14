"""
Null — FastAPI Application Entry Point

Start with:
  uvicorn app.main:app --host 0.0.0.0 --port 8000

API docs at /docs — frontend SPA served at /
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

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

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_admin()
    yield
    from xapi.client import pool_registry
    pool_registry.shutdown_all()


app = FastAPI(
    title="Null",
    description="""
    **Remote dominion over your XCP-ng infrastructure.**

    Single-container Docker deployment — serves the React UI and REST API
    from one process. Communicates with XCP-ng via XAPI XML-RPC over HTTPS.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — local dev only; in Docker the SPA is same-origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ──────────────────────────────────────────────────────

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

# ── Serve frontend (must be after API routes) ───────────────────────

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str = ""):
        """Serve the React SPA — all non-API routes return index.html."""
        index = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index):
            return FileResponse(index)
        return {"service": "Null", "version": "0.1.0", "docs": "/docs"}


@app.get("/api/health")
async def root():
    """Legacy root — the SPA handles / in production."""
    return {"service": "Null", "version": "0.1.0", "docs": "/docs"}
