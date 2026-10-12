import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from dotenv import load_dotenv
from models import Base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не задан!")

for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL[len(prefix):]
        break

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def create_table():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)