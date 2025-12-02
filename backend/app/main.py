from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import engine, Base
from .routers import projects, tasks, comments, timeline, attachments, auth

app = FastAPI(title="FMS API (improved REST)", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers
app.include_router(auth.router, prefix="")        # NEW
app.include_router(projects.router, prefix="")
app.include_router(tasks.router, prefix="")
app.include_router(comments.router, prefix="")
app.include_router(timeline.router, prefix="")
app.include_router(attachments.router, prefix="")

@app.get("/health")                               # NEW
async def health_check():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    pass
