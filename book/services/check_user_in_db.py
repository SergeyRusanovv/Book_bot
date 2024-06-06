from sqlalchemy import select

from database.database import async_session
from database.models import User


async def check_user_in_db(message):
    """Функция, которая поверяет есть ли пользователь в БД"""
    async with async_session() as session:
        query = select(User).where(User.user_id == message.from_user.id)
        result = await session.execute(query)
        user = result.scalars().all()
        return len(user) > 0
