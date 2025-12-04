import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Required
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str
    SECRET_KEY: str = "super-secret-key-change-in-prod"
    ALGORITHM: str = "HS256"

    # Optional but required for your app/env
    DATABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str


    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()
