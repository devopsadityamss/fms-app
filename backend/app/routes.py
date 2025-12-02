from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from . import models

router = APIRouter()

# -------------------------------
# PROFILES
# -------------------------------
@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db)):
    profiles = db.query(models.Profile).all()
    return profiles

# -------------------------------
# PROJECTS
# -------------------------------
@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).all()
    return projects

# -------------------------------
# TASKS
# -------------------------------
@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    return tasks
