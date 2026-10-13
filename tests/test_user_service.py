import os
import unittest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-user-service-123456")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel

from app.models.user import User
from app.services.user_service import UserService


class UserServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        self.session = self.session_factory()
        self.service = UserService(self.session)

    async def asyncTearDown(self):
        await self.session.close()
        await self.engine.dispose()

    async def test_create_and_fetch_user(self):
        user = await self.service.create_user("alice", "alice@example.com", "password123")

        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.email, "alice@example.com")

        fetched = await self.service.get_by_username("alice")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, user.id)


if __name__ == "__main__":
    unittest.main()
