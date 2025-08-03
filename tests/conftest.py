import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from api import app
from database import Base, get_async_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def override_get_async_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        await db.close()

app.dependency_overrides[get_async_db] = override_get_async_db

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac