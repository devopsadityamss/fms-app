# app/main.py

from fastapi import FastAPI
from .db import Base, engine
from . import routes

app = FastAPI()

# Include all API routes
app.include_router(routes.router)
