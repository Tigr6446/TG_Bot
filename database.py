import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from dotenv import load_dotenv
from sqlalchemy import select
from models import Base, BotSettings

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не задан!")

# Убираем sslmode из ссылки, так как asyncpg его не понимает
if "?sslmode=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?sslmode=require", "")

for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
    if DATABASE_URL.startswith(prefix):
        DATABASE_URL = "postgresql+asyncpg://" + DATABASE_URL[len(prefix):]
        break

# Создаем асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": "require"},
    pool_pre_ping=True,
    pool_recycle=1800
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def create_table():
    # 1. Создаем таблицы (открываем соединение и закрываем его)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # 2. Проверяем настройки (открываем сессию уже ПОСЛЕ закрытия соединения)
    async with AsyncSessionLocal() as session:
        stmt = select(BotSettings).where(BotSettings.id == 1)
        settings = await session.scalar(stmt)
        if not settings:
            session.add(BotSettings(id=1, is_contest_active=True))
            await session.commit()