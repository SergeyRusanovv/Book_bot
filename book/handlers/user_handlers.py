import re

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from database.models import User, Book, BookPage, UserProgress

from filters.filters import IsDelBookmarkCallbackData, IsDigitCallbackData
# from keyboards.bookmarks_kb import (create_bookmarks_keyboard,
#                                     create_edit_keyboard)
from keyboards.books_list_kb import create_books_list_keyboard
from keyboards.pagination_kb import create_pagination_keyboard

from messages.messages import LEXICON

from sqlalchemy import insert, select, text
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

        if not book:
            await callback_query.message.answer("Sorry, couldn't find that book.")
            return

        user = await session.get(User, callback_query.from_user.id)

        if not user:
            await callback_query.message.answer("You haven't registered yet. Use /start")
            return

        query_page = select(BookPage).where(BookPage.book_id == book.id)
        result_out = await session.execute(query_page)
        pages = result_out.scalars().all()

        progress_result = await session.execute(
            select(UserProgress)
            .where(UserProgress.book_id == book.id and UserProgress.user_id == user.id))
        current_progress = progress_result.scalars().first()

        if current_progress is None:
            current_progress = UserProgress(last_read_page=0, book_id=book.id, user_id=user.user_id)
            session.add(current_progress)

        await session.commit()

    page_text = pages[current_progress.last_read_page].text

    await callback_query.message.answer(
        text=page_text,
        reply_markup=create_pagination_keyboard(
            "before" if current_progress.last_read_page > 0 else "...",
            f"{current_progress.last_read_page + 1} / {len(pages)}",
            "after" if current_progress.last_read_page < len(pages) - 1 else "...",
            "bookmarks",
            "table"
        )
    )


@router.message(Command(commands="users_books"))
async def process_continue_reading(message: Message):
    """
    Этот хэндлер будет срабатывать на команду "/continue"
    и отправлять пользователю страницу книги, на которой пользователь
    остановился в процессе взаимодействия с ботом
    """
    async with async_session() as session:
        user_id = message.from_user.id
        query = text(
            f"""
            SELECT b.name
            FROM user_progress AS u_p
            INNER JOIN books AS b ON b.id = u_p.book_id
            WHERE u_p.user_id = {user_id}
            """
        )
        result = await session.execute(query)
        books = result.scalars().all()

        await message.answer(
            text=LEXICON["users_books"],
            reply_markup=create_books_list_keyboard(books)
        )


@router.callback_query(F.data == 'after')
async def process_forward_press(callback_query: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки "вперед"
    во время взаимодействия пользователя с сообщением-книгой
    """
    async with async_session() as session:
        result = await session.execute(
            select(BookPage)
            .where(BookPage.text.contains(callback_query.message.text[:30]))
        )
        current_page = result.scalars().first()

        progress_result = await session.execute(
            select(UserProgress).
            where(UserProgress.user_id == callback_query.from_user.id,
                  UserProgress.book_id == current_page.book_id)
        )
        progress = progress_result.scalars().first()

        pages_list = await session.execute(
            select(BookPage)
            .where(BookPage.book_id == current_page.book_id)
        )
        pages = pages_list.scalars().all()

        page = progress.last_read_page
        if page < len(pages) - 1:
            current_page = pages[page + 1]

            progress.last_read_page += 1
            session.add(progress)
        else:
            current_page = pages[page]

        await session.commit()

    await callback_query.message.answer(
        text=current_page.text,
        reply_markup=create_pagination_keyboard(
            "before" if page > 0 else '...',
            f"{page + 1} / {len(pages)}",
            "after" if page < len(pages) - 1 else '...',
            "bookmarks",
            "table"
        )
    )


@router.callback_query(F.data == 'before')
async def process_backward_press(callback_query: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки "назад"
    во время взаимодействия пользователя с сообщением-книгой
    """
    async with async_session() as session:
        result = await session.execute(
            select(BookPage)
            .where(BookPage.text.contains(callback_query.message.text[:30]))
        )
        current_page = result.scalars().first()

        progress_result = await session.execute(
            select(UserProgress).
            where(UserProgress.user_id == callback_query.from_user.id,
                  UserProgress.book_id == current_page.book_id)
        )
        progress = progress_result.scalars().first()

        pages_list = await session.execute(
            select(BookPage)
            .where(BookPage.book_id == current_page.book_id)
        )
        pages = pages_list.scalars().all()

        page = progress.last_read_page
        if page > 0:
            current_page = pages[page - 1]

            progress.last_read_page -= 1
            session.add(progress)
        else:
            current_page = pages[page]

        await session.commit()

    await callback_query.message.answer(
        text=current_page.text,
        reply_markup=create_pagination_keyboard(
            "before" if page > 0 else '...',
            f"{page - 1} / {len(pages)}",
            "after" if page < len(pages) - 1 else '...',
            "bookmarks",
            "table"
        )
    )


@router.callback_query(lambda x: '/' in x.data and x.data.replace(' / ', '').isdigit())
async def process_page_press(callback: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
    с номером текущей страницы и добавлять текущую страницу в закладки
    """
    page = int(re.search(r"^\d+", callback.data)[0]) - 1

    await callback.answer('Страница добавлена в закладки!')

# @router.message(Command(commands='bookmarks'))
# async def process_bookmarks_command(message: Message):
#     """
#     Этот хэндлер будет срабатывать на команду "/bookmarks"
#     и отправлять пользователю список сохраненных закладок,
#     если они есть или сообщение о том, что закладок нет
#     """
#     if users_db[message.from_user.id]["bookmarks"]:
#         await message.answer(
#             text=LEXICON[message.text],
#             reply_markup=create_bookmarks_keyboard(
#                 *users_db[message.from_user.id]["bookmarks"]
#             )
#         )
#     else:
#         await message.answer(text=LEXICON['no_bookmarks'])


# # Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# # с закладкой из списка закладок
# @router.callback_query(IsDigitCallbackData())
# async def process_bookmark_press(callback: CallbackQuery):
#     text = book[int(callback.data)]
#     users_db[callback.from_user.id]['page'] = int(callback.data)
#     await callback.message.edit_text(
#         text=text,
#         reply_markup=create_pagination_keyboard(
#             'backward',
#             f'{users_db[callback.from_user.id]["page"]}/{len(book)}',
#             'forward'
#         )
#     )


# Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# "редактировать" под списком закладок
# @router.callback_query(F.data == 'edit_bookmarks')
# async def process_edit_press(callback: CallbackQuery):
#     await callback.message.edit_text(
#         text=LEXICON[callback.data],
#         reply_markup=create_edit_keyboard(
#             *users_db[callback.from_user.id]["bookmarks"]
#         )
#     )
#
#
# # Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# # "отменить" во время работы со списком закладок (просмотр и редактирование)
# @router.callback_query(F.data == 'cancel')
# async def process_cancel_press(callback: CallbackQuery):
#     await callback.message.edit_text(text=LEXICON['cancel_text'])
#
#
# # Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
# # с закладкой из списка закладок к удалению
# @router.callback_query(IsDelBookmarkCallbackData())
# async def process_del_bookmark_press(callback: CallbackQuery):
#     users_db[callback.from_user.id]['bookmarks'].remove(
#         int(callback.data[:-3])
#     )
#     if users_db[callback.from_user.id]['bookmarks']:
#         await callback.message.edit_text(
#             text=LEXICON['/bookmarks'],
#             reply_markup=create_edit_keyboard(
#                 *users_db[callback.from_user.id]["bookmarks"]
#             )
#         )
#     else:
#         await callback.message.edit_text(text=LEXICON['no_bookmarks'])
