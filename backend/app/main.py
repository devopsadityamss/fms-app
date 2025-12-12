# backend/app/main.py

# FORCE logger module import so handlers attach

import app.core.logger
from app.core.logger import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.farmer import production_units, stages, tasks, dashboard

from app.core.database import AsyncSessionLocal
from app.core.seed_rbac import seed_rbac
from .core.config import settings
from .core.database import engine, Base

from app.core.request_middleware import RequestLoggingMiddleware
from app.core.error_middleware import ExceptionLoggingMiddleware

from backend.app.api.farmer import production_units as farmer_production
from app.api.farmer import tasks as farmer_tasks
from app.api.farmer import stages as farmer_stages
from app.api.farmer import activity

from app.api.farmer import (
    unit,
    task,
    stage,
    activity,
    weather,
    advisory,
    alert,
    calendar,
    health,
    prediction,
    inventory,
    cost,
    notification,
    # new
    soil,
    irrigation,
    market,
    profitability,
    pest,
    compliance,
    sustainability,
    intelligence,
)

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
from app.api import rbac
from app.api import auth_session


# ---------------------------------------------------
# Include Routers
# ---------------------------------------------------
app.include_router(auth.router)
app.include_router(rbac.router)
app.include_router(auth_session.router)
app.include_router(production_units.router, prefix="/farmer", tags=["farmer-units"])
app.include_router(stages.router, prefix="/farmer", tags=["farmer-stages"])
app.include_router(tasks.router, prefix="/farmer", tags=["farmer-tasks"])
app.include_router(dashboard.router, prefix="/farmer", tags=["farmer-dashboard"])
app.include_router(activity.router)
app.include_router(weather.router, prefix="/farmer/unit")
app.include_router(advisory.router, prefix="/farmer/unit")
app.include_router(alert.router, prefix="/farmer/unit")
app.include_router(calendar.router, prefix="/farmer/unit")
app.include_router(health.router, prefix="/farmer/unit")
app.include_router(prediction.router, prefix="/farmer/unit")
app.include_router(inventory.router, prefix="/farmer/unit")
app.include_router(cost.router, prefix="/farmer/unit")
app.include_router(notification.router, prefix="/farmer/unit")
app.include_router(soil.router, prefix="/farmer/unit")
app.include_router(irrigation.router, prefix="/farmer/unit")
app.include_router(market.router, prefix="/farmer/unit")
app.include_router(profitability.router, prefix="/farmer/unit")
app.include_router(pest.router, prefix="/farmer/unit")
app.include_router(compliance.router, prefix="/farmer/unit")
app.include_router(sustainability.router, prefix="/farmer/unit")
app.include_router(intelligence.router, prefix="/farmer/unit")

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
