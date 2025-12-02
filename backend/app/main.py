from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import engine, Base
from .routers import projects, tasks, comments, timeline, attachments

app = FastAPI(title="FMS API (improved REST)", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include routers at root for improved REST paths
app.include_router(projects.router, prefix="")
app.include_router(tasks.router, prefix="")
app.include_router(comments.router, prefix="")
app.include_router(timeline.router, prefix="")
app.include_router(attachments.router, prefix="")

@app.on_event("startup")
async def startup():
    # Optionally create metadata locally if using a dev DB
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    pass
