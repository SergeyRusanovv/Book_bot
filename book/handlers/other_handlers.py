from aiogram import Router
from aiogram.types import Message
from messages.messages import LEXICON


router = Router()


@router.message()
async def send_echo(message: Message):
    """Хэндлер для отлова некорректных команд"""
    await message.answer(f'{LEXICON["echo"]}')
