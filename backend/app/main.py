# FORCE logger module import so handlers attach
import app.core.logger
from app.core.logger import logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



from .core.config import settings
from .core.database import engine, Base
from .routers import projects, tasks, comments, timeline, attachments, auth


app = FastAPI(title="FMS API (improved REST)", version="1.0")

from app.core.request_middleware import RequestLoggingMiddleware
from app.core.error_middleware import ExceptionLoggingMiddleware


# Logging middlewares (MUST COME BEFORE CORS)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ExceptionLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(comments.router)
app.include_router(timeline.router)
app.include_router(attachments.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    logger.info("🔥 Server started with JSON logging")
    logger.info("Backend started with structured JSON logging + audit logs enabled")

@app.get("/test-log")
async def test_log():
    logger.info("Test log endpoint triggered", extra={"endpoint": "test-log"})
    return {"message": "logged"}

