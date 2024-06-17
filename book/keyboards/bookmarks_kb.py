from typing import List
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from messages.messages import LEXICON


def create_bookmarks_keyboard(buttons_list: List) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for button in buttons_list:
        callback_data = f"{button[0]}"
        kb_builder.row(InlineKeyboardButton(
            text=f'{button[0]} - {button[1][:100]}',
            callback_data=callback_data
        ))
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='cancel'
        ),
        width=2
    )
    return kb_builder.as_markup()


def create_edit_keyboard(*args) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for button in args:
        kb_builder.row(InlineKeyboardButton(
            text=f'{LEXICON['del']} DELETE {LEXICON['del']}',
            callback_data=f'{button[0]}del'
        ))
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='cancel'
        )
    )
    kb_builder.row(
        InlineKeyboardButton(
            text='Назад к закладкам >>>',
            callback_data="/bookmarks"
        )
    )
    return kb_builder.as_markup()
