from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in environment")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
