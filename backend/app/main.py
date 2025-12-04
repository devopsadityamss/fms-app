# FORCE logger module import so handlers attach
import app.core.logger
from app.core.logger import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import AsyncSessionLocal
from app.core.seed_rbac import seed_rbac
from .core.config import settings
from .core.database import engine, Base

from app.core.request_middleware import RequestLoggingMiddleware
from app.core.error_middleware import ExceptionLoggingMiddleware


# ---------------------------------------------------
# Create FastAPI instance FIRST
# ---------------------------------------------------
app = FastAPI(title="FMS API (improved REST)", version="1.0")


# ---------------------------------------------------
# CORS MUST be added immediately after app creation
# ---------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------
# Logging middlewares
# ---------------------------------------------------
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ExceptionLoggingMiddleware)


# ---------------------------------------------------
# IMPORT ROUTERS AFTER APP IS CREATED
# ---------------------------------------------------
from .routers import projects, tasks, comments, timeline, attachments, auth
from app.api import rbac
from app.api import auth_session


# ---------------------------------------------------
# Include Routers
# ---------------------------------------------------
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(timeline.router)
app.include_router(attachments.router)
app.include_router(rbac.router)
app.include_router(auth_session.router)


# ---------------------------------------------------
# COMBINED startup event (create tables + seed + logs)
# (Fix duplicate startup decorators)
# ---------------------------------------------------
@app.on_event("startup")
async def startup_event():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # RBAC seeding
    async with AsyncSessionLocal() as db:
        await seed_rbac(db)

    # Log startup messages
    logger.info("🔥 Server started with JSON logging")
    logger.info("Backend started with structured JSON logging + audit logs enabled")


# ---------------------------------------------------
# Test + Health endpoints
# ---------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/test-log")
async def test_log():
    logger.info("Test log endpoint triggered", extra={"endpoint": "test-log"})
    return {"message": "logged"}
