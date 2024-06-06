from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from database.models import User, Book, BookPage

from filters.filters import IsDelBookmarkCallbackData, IsDigitCallbackData
# from keyboards.bookmarks_kb import (create_bookmarks_keyboard,
#                                     create_edit_keyboard)
from keyboards.books_list_kb import create_books_list_keyboard
from keyboards.pagination_kb import create_pagination_keyboard

from messages.messages import LEXICON

from sqlalchemy import insert, select
from services.check_user_in_db import check_user_in_db
from services.write_book_in_db import BookWriter


router = Router()


@router.message(CommandStart())
async def process_start_command(message: Message):
    """
    Этот хэндлер будет срабатывать на команду "/start" -
    добавлять пользователя в базу данных, если его там еще не было
    и отправлять ему приветственное сообщение
    """
    bw = BookWriter()
    await bw.run()
    if await check_user_in_db(message=message):
        await message.answer("Вы уже зарегистрированы, продолжим?")
    else:
        async with async_session() as session:
            new_user = insert(User).values(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )
            await session.execute(new_user)
            await session.commit()
            await message.answer("Поздравляю вас с регистрацией!")
    await message.answer(LEXICON[message.text])


@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    """
    Этот хэндлер будет срабатывать на команду "/help"
    и отправлять пользователю сообщение со списком доступных команд в боте
    """
    await message.answer(LEXICON[message.text])


@router.message(Command(commands='books_list'))
async def process_get_books_list(message: Message):
    """
    Этот хэндлер показывает список доступных книг
    """
    async with async_session() as session:
        query = select(Book)
        result = await session.execute(query)
        all_books = result.scalars().all()
        books = [book.name for book in all_books]

    await message.answer(
        text=LEXICON["books_list"],
        reply_markup=create_books_list_keyboard(books)
    )


@router.callback_query(lambda c: c.data and c.data.startswith('read_book_'))
async def process_book_selection(callback_query: CallbackQuery):
    book_title = callback_query.data[len('read_book_'):]

    async with async_session() as session:
        query = select(Book).where(Book.name == book_title)
        result = await session.execute(query)
        book = result.scalars().first()

        query_page = select(BookPage).where(BookPage.book_id == book.id)
        result_out = await session.execute(query_page)
        pages = result_out.scalars().all()

        page = pages[0]

    await callback_query.message.answer(
        text=page.text,
        reply_markup=create_pagination_keyboard(
            "before",
            f"1 / {len(pages)}",
            "after"
        )
    )

# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки "вперед"
# во время взаимодействия пользователя с сообщением-книгой
@router.callback_query(F.data == 'after')
async def process_forward_press(callback: CallbackQuery):
        await callback.message.edit_text(
            text=text,
            reply_markup=create_pagination_keyboard(
                'backward',
                f'{users_db[callback.from_user.id]["page"]}/{len(book)}',
                'forward'
            )
        )
    await callback.answer()


@router.callback_query(F.data == 'before')
async def process_backward_press(callback: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки "назад"
    во время взаимодействия пользователя с сообщением-книгой
    """
    if users_db[callback.from_user.id]['page'] > 1:
        users_db[callback.from_user.id]['page'] -= 1
        text = book[users_db[callback.from_user.id]['page']]
        await callback.message.edit_text(
            text=text,
            reply_markup=create_pagination_keyboard(
                'backward',
                f'{users_db[callback.from_user.id]["page"]}/{len(book)}',
                'forward'
            )
        )
    await callback.answer()


# @router.message(Command(commands='beginning'))
# async def process_reading(message: Message):
#     """
#     Этот хэндлер будет срабатывать на команду "/beginning"
#     и отправлять пользователю первую страницу книги с кнопками пагинации
#     """
#     users_db[message.from_user.id]['page'] = 1
#     text = book[users_db[message.from_user.id]['page']]
#     await message.answer(
#         text=text,
#         reply_markup=create_pagination_keyboard(
#             'before',
#             f'{users_db[message.from_user.id]["page"]}/{len(book)}',
#             'after'
#         )
#     )


# Этот хэндлер будет срабатывать на команду "/continue"
# и отправлять пользователю страницу книги, на которой пользователь
# остановился в процессе взаимодействия с ботом
# @router.message(Command(commands='continue'))
# async def process_continue_command(message: Message):
#     text = book[users_db[message.from_user.id]['page']]
#     await message.answer(
#         text=text,
#         reply_markup=create_pagination_keyboard(
#             'backward',
#             f'{users_db[message.from_user.id]["page"]}/{len(book)}',
#             'forward'
#         )
#     )


# Этот хэндлер будет срабатывать на команду "/bookmarks"
# и отправлять пользователю список сохраненных закладок,
# если они есть или сообщение о том, что закладок нет
# @router.message(Command(commands='bookmarks'))
# async def process_bookmarks_command(message: Message):
#     if users_db[message.from_user.id]["bookmarks"]:
#         await message.answer(
#             text=LEXICON[message.text],
#             reply_markup=create_bookmarks_keyboard(
#                 *users_db[message.from_user.id]["bookmarks"]
#             )
#         )
#     else:
#         await message.answer(text=LEXICON['no_bookmarks'])


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# с номером текущей страницы и добавлять текущую страницу в закладки
@router.callback_query(lambda x: '/' in x.data and x.data.replace('/', '').isdigit())
async def process_page_press(callback: CallbackQuery):
    users_db[callback.from_user.id]['bookmarks'].add(
        users_db[callback.from_user.id]['page']
    )
    await callback.answer('Страница добавлена в закладки!')


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# с закладкой из списка закладок
@router.callback_query(IsDigitCallbackData())
async def process_bookmark_press(callback: CallbackQuery):
    text = book[int(callback.data)]
    users_db[callback.from_user.id]['page'] = int(callback.data)
    await callback.message.edit_text(
        text=text,
        reply_markup=create_pagination_keyboard(
            'backward',
            f'{users_db[callback.from_user.id]["page"]}/{len(book)}',
            'forward'
        )
    )


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# "редактировать" под списком закладок
@router.callback_query(F.data == 'edit_bookmarks')
async def process_edit_press(callback: CallbackQuery):
    await callback.message.edit_text(
        text=LEXICON[callback.data],
        reply_markup=create_edit_keyboard(
            *users_db[callback.from_user.id]["bookmarks"]
        )
    )


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# "отменить" во время работы со списком закладок (просмотр и редактирование)
@router.callback_query(F.data == 'cancel')
async def process_cancel_press(callback: CallbackQuery):
    await callback.message.edit_text(text=LEXICON['cancel_text'])


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# с закладкой из списка закладок к удалению
@router.callback_query(IsDelBookmarkCallbackData())
async def process_del_bookmark_press(callback: CallbackQuery):
    users_db[callback.from_user.id]['bookmarks'].remove(
        int(callback.data[:-3])
    )
    if users_db[callback.from_user.id]['bookmarks']:
        await callback.message.edit_text(
            text=LEXICON['/bookmarks'],
            reply_markup=create_edit_keyboard(
                *users_db[callback.from_user.id]["bookmarks"]
            )
        )
    else:
        await callback.message.edit_text(text=LEXICON['no_bookmarks'])
