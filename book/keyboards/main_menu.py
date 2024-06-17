from aiogram import Bot
from aiogram.types import BotCommand
from messages.messages import LEXICON_COMMANDS


async def set_main_menu(bot: Bot):
    """
    Функция для настройки кнопки Menu бота
    """
    main_menu_commands = [BotCommand(
        command=command,
        description=description
    ) for command,
        description in LEXICON_COMMANDS.items()]
    await bot.set_my_commands(main_menu_commands)
