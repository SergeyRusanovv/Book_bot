from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardBuilder


def create_table_keyboard(buttons, current_page=1, total_pages=1, counter=0):
    kb_builder = InlineKeyboardBuilder()

    for button in buttons:
        kb_builder.add(InlineKeyboardButton(
            text=str(counter),
            callback_data=f"page_{current_page}_{button}"
        ))
        counter += 1

    if current_page > 1:
        kb_builder.row(InlineKeyboardButton(
            text="Назад",
            callback_data=f"nav_{current_page - 1}"
        ))
    if current_page < total_pages:
        kb_builder.add(InlineKeyboardButton(
            text="Вперед",
            callback_data=f"nav_{current_page + 1}"
        ))

    return kb_builder.as_markup()
