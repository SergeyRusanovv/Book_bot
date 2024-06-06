import os
import asyncio
import fitz
import aiofiles
from database.database import async_session
from database.models import Book, BookPage


class BookWriter:
    folder_path = "books"

    async def store_pdf_content(self, pdf_path):
        async with aiofiles.open(pdf_path, 'rb') as file:
            pdf_reader = fitz.open(pdf_path)
            text = ""
            for page_num in range(pdf_reader.page_count):
                page = pdf_reader[page_num]
                text += page.get_text()

        async with async_session() as session:
            file_name = pdf_path.split("/")[-1]
            write_file_name = file_name.split(".")[0]
            new_book = Book(name=write_file_name)
            text_dict = await self._get_part_text(text=text)

            async with session.begin():
                session.add(new_book)
                await session.flush()
                mappings = [{'text': value, 'book_id': new_book.id} for key, value in text_dict.items()]
                await session.run_sync(
                    lambda sync_session: sync_session.bulk_insert_mappings(BookPage, mappings)
                )
                await session.commit()

    async def store_txt_content(self, file_path):
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            text = await file.read()
        file_name = file_path.split("/")[-1]
        write_file_name = file_name.split(".")[0]
        new_book = Book(name=write_file_name)
        text_dict = await self._get_part_text(text=text)

        async with async_session() as session:
            async with session.begin():
                session.add(new_book)
                await session.flush()
                mappings = [{'text': value, 'book_id': new_book.id} for key, value in text_dict.items()]
                await session.run_sync(
                    lambda sync_session: sync_session.bulk_insert_mappings(BookPage, mappings)
                )
                await session.commit()

    async def check_books_folder(self):
        tasks = []
        for file_name in os.listdir(self.folder_path):
            if file_name.endswith('.txt'):
                task = asyncio.create_task(self.store_txt_content(os.path.join(self.folder_path, file_name)))
                tasks.append(task)
            elif file_name.endswith('.pdf'):
                task = asyncio.create_task(self.store_pdf_content(os.path.join(self.folder_path, file_name)))
                tasks.append(task)
        await asyncio.gather(*tasks)

    @staticmethod
    async def _get_part_text(text: str, maxsize: int = 4000):
        counter = 1
        result_dict = dict()
        text_to_dict = ''

        for index, letter in enumerate(text):
            text_to_dict += letter
            if (index + 1) % maxsize == 0 or index == len(text) - 1:
                result_dict[counter] = text_to_dict
                counter += 1
                text_to_dict = ''

        return result_dict

    async def run(self):
        await self.check_books_folder()
