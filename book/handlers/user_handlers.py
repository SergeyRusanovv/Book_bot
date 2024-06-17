from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from database.database import async_session
from database.models import User, Book, BookPage, UserProgress

from filters.filters import IsDelBookmarkCallbackData, IsDigitCallbackData
from keyboards.bookmarks_kb import create_bookmarks_keyboard, create_edit_keyboard
from keyboards.books_list_kb import create_books_list_keyboard
from keyboards.pagination_kb import create_pagination_keyboard
from keyboards.table_kb import create_table_keyboard

from messages.messages import LEXICON

from sqlalchemy import select, text

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
            query = text(
                "INSERT INTO users (user_id, username, first_name, last_name) "
                "VALUES (:user_id, :username, :first_name, :last_name)"
            )
            await session.execute(query, {
                'user_id': message.from_user.id, "username": message.from_user.username,
                "first_name": message.from_user.first_name, "last_name": message.from_user.last_name
                })
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
        books = [book.id for book in all_books]

    await message.answer(
        text=LEXICON["books_list"],
        reply_markup=create_books_list_keyboard(books)
    )


@router.callback_query(lambda c: c.data and c.data.startswith('read_book_'))
async def process_book_selection(callback_query: CallbackQuery):
    _, book_id, page_number = callback_query.data.split('_')

    async with async_session() as session:
        query = select(Book).where(Book.id == book_id)
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
        book_id = progress.book_id

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
        book_id = progress.book_id

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
            "/bookmarks",
        )
    )


@router.callback_query(lambda x: '/' in x.data and x.data.replace(' / ', '').isdigit())
async def process_page_press(callback: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
    с номером текущей страницы и добавлять текущую страницу в закладки
    """
    page_text = callback.message.text[:60]
    user_id = callback.from_user.id
    async with async_session() as session:
        query = text(
            "SELECT b_p.id, b_p.book_id "
            "FROM book_page AS b_p "
            "WHERE b_p.text LIKE :page_text "
        )
        result = await session.execute(query, {'page_text': f'%{page_text}%'})
        result_info = result.fetchone()
        query = text(
            "INSERT INTO bookmarks (user_id, book_id, book_page)"
            "VALUES (:user_id, :book_id, :book_page)"
        )
        await session.execute(query, {'user_id': user_id, 'book_id': result_info[1], 'book_page' : result_info[0]})
        await session.commit()

    await callback.answer('Страница добавлена в закладки!')


@router.message(Command(commands="bookmarks"))
async def process_bookmarks_command(message: Message):
    """
    Этот хэндлер будет срабатывать на команду "/bookmarks"
    и отправлять пользователю список сохраненных закладок,
    если они есть или сообщение о том, что закладок нет
    """
    user_id = message.from_user.id
    async with async_session() as session:
        query = text(
            "SELECT b_m.bookmark_id, b_p.text "
            "FROM bookmarks AS b_m "
            "INNER JOIN book_page AS b_p ON b_p.id = b_m.book_page "
            "WHERE b_m.user_id = :user_id "
        )
        result = await session.execute(query, {'user_id': user_id})
        bookmarks = result.all()
        if len(bookmarks) > 0:
            await message.answer(
                text=LEXICON['/bookmarks'],
                reply_markup=create_bookmarks_keyboard(
                    bookmarks
                )
            )
        else:
            await message.answer(text=LEXICON['no_bookmarks'])


@router.callback_query(IsDigitCallbackData())
async def process_bookmark_press(callback: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
    с закладкой из списка закладок
    """
    bookmark_id = int(callback.data)

    async with async_session() as session:
        query = text(
            "SELECT b_p.text "
            "FROM book_page AS b_p "
            "WHERE b_p.id = :bookmark_id "
        )
        result = await session.execute(query, {'bookmark_id': bookmark_id})
        info = result.fetchone()
        page_text = str(info)

    buttons = [bookmark_id, page_text]

    await callback.message.answer(
        text=page_text,
        reply_markup=create_edit_keyboard(
            buttons,
        )
    )


@router.callback_query(F.data == 'cancel')
async def process_cancel_press(callback: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
    "отменить" во время работы со списком закладок (просмотр и редактирование)
    """
    await callback.message.edit_text(text=LEXICON['cancel_text'])


@router.callback_query(IsDelBookmarkCallbackData())
async def process_del_bookmark_press(callback: CallbackQuery):
    """
    Этот хэндлер будет срабатывать на нажатие инлайн-кнопки
    с закладкой из списка закладок к удалению
    """
    bookmark_id = int(callback.data[:-3])
    async with async_session() as session:
        query = text(
            "DELETE FROM bookmarks WHERE bookmark_id = :bookmark_id "
        )
        await session.execute(query, {'bookmark_id': bookmark_id})
        await session.commit()
    await callback.answer('Запись удалена!')


@router.callback_query(F.data.startswith('nav_'))
async def navigate_pages(callback: CallbackQuery):
    _, page = callback.data.split('_')
    page = int(page)
    print(page)
    page_text = callback.message.text[:60]
    async with async_session() as session:
        query = text(
            "SELECT b_p.id FROM book_page AS b_p "
            "WHERE b_p.book_id IN "
                "(SELECT b_p.book_id "
                "FROM book_page AS b_p "
                "WHERE b_p.text LIKE :page_text)"
        )
        result = await session.execute(query, {'page_text': f'%{page_text}%'})
        book_page_ids = result.scalars().all()
    total_pages = (len(book_page_ids) // 98) + 1
    counter = (page * 99) - 98
    if page > 1:
        buttons = book_page_ids[page * 99:]
    else:
        buttons = book_page_ids[:page * 99]
    await callback.message.answer(
        text=LEXICON['table'],
        reply_markup=create_table_keyboard(
            buttons=buttons, current_page=page, total_pages=total_pages, counter=counter
        )
    )
