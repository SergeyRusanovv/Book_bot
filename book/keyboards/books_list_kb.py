from typing import List

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from messages.messages import LEXICON


def create_books_list_keyboard(buttons: List[str]) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.row(*[InlineKeyboardButton(
        text=button,
        callback_data=f"read_book_{button}") for button in buttons]
    )
    return kb_builder.as_markup()
