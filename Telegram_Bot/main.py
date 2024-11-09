import asyncio
import logging
import traceback 
import httpx
import redis
import requests
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import TELEGRAM_BOT_TOKEN, API_GATEWAY_URL, REDIS_HOST, REDIS_PORT

PAGE_SIZE = 5
dp = Dispatcher()

redis_client = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=0)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}!\n"
        f"Используй команду /courses, чтобы просмотреть доступные курсы."
    )

@dp.message(Command("courses"))
async def show_courses(message: Message, page: int = 0) -> None:
    
    try:
        response = requests.get(f"{API_GATEWAY_URL}/courses")
        if response.status_code == 200:
            courses = response.json()
            total_pages = (len(courses) - 1) // PAGE_SIZE + 1
            chat_id = message.chat.id
            #user_course_pages[message.chat.id] = page
            redis_client.set(f"user:{chat_id}:course_page", page)
            inline_keyboard = [
                [
                    InlineKeyboardButton(
                        text=course["name"][:30],
                        callback_data=f"course_{course['id']}"
                    )
                ]
                for course in courses[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]
            ]

            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_page"))
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data="next_page"))

            if nav_buttons:
                inline_keyboard.append(nav_buttons)

            keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
            
            if redis_client.exists(f"user:{chat_id}:message_id"):
                try:          
                    sent_message = await message.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=redis_client.get(f"user:{chat_id}:message_id"),
                        text="Выберите курс:",
                        reply_markup=keyboard
                    )
                except:
                    try:
                        await message.bot.delete_message(message.chat.id, redis_client.get(f"user:{chat_id}:message_id"))
                        # sent_message = await message.answer(f"Выберите курс:", reply_markup=keyboard)
                    except:
                        logging.error("asfasdf")
                    sent_message = await message.answer(f"Выберите курс:", reply_markup=keyboard)
            else:
                sent_message = await message.answer(f"Выберите курс:", reply_markup=keyboard)
            
            redis_client.set(f"user:{chat_id}:message_id", sent_message.message_id)
        else:
            await message.answer(
                f"Ошибка при получении курсов: {response.status_code}"
            )
    except Exception as e:
        error_message = f"Произошла ошибка при загрузке курсов:\n{str(e)}\n\n{traceback.format_exc()}"
        logging.error(error_message)
        


@dp.callback_query(lambda callback: callback.data == "prev_page")
async def prev_page(callback: CallbackQuery):
    user_id = callback.message.chat.id
    page = max(int(redis_client.get(f"user:{user_id}:course_page")) - 1, 0)
    await show_courses(callback.message, page)

@dp.callback_query(lambda callback: callback.data == "next_page")
async def next_page(callback: CallbackQuery):
    user_id = callback.message.chat.id
    page = int(redis_client.get(f"user:{user_id}:course_page")) + 1
    await show_courses(callback.message, page)

@dp.callback_query(lambda callback: callback.data.startswith("course_"))
async def show_course_details(callback: CallbackQuery):
    
    course_id = callback.data.split("_")[1]
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_GATEWAY_URL}/courses/{course_id}")
            if response.status_code == 200:
                course = response.json()

                # Создание клавиатуры с использованием inline_keyboard как списка списков
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="Записаться на курс", callback_data=f"enroll_{course_id}")],
                        [InlineKeyboardButton(text="Назад", callback_data="back_to_courses")]
                    ]
                )

                # Отправка сообщения с клавиатурой
                await callback.message.answer(
                    f"Курс: {course['name']}\n"
                    f"Продолжительность: {course['duration']}\n"
                    f"Стоимость: {course['price']}\n"
                    f"Описание: {course['description']}",
                    reply_markup=keyboard
                )
            else:
                await callback.message.answer(f"Ошибка при получении данных курса: {response.status_code}")
    except Exception as e:
        error_message = f"Произошла ошибка при загрузке данных курса: {str(e)}\n\n{traceback.format_exc()}"
        logging.error(error_message)
        await callback.message.answer(error_message)


@dp.callback_query(lambda callback: callback.data == "back_to_courses")
async def back_to_courses(callback: CallbackQuery):

    #page = user_course_pages.get(callback.from_user.id, 0)
    #!!!!!
    page = redis_client.get(f"user:{callback.message.chat.id}:course_page")
    # Проверяем, есть ли message_id сообщения со списком курсов
    if redis_client.exists(f"user:{callback.message.chat.id}:message_id"):
        try:
            # Удаляем сообщение со списком курсов
            #await callback.message.bot.delete_message(callback.message.chat.id, user_course_message_id[callback.from_user.id])
            await callback.message.bot.delete_message(callback.message.chat.id, redis_client.get(f"user:{callback.message.chat.id}:message_id"))
            # Сбрасываем сохраненный message_id, чтобы избежать повторного удаления
            #del user_course_message_id[callback.from_user.id]
            redis_client.delete(f"user:{callback.message.chat.id}:message_id")
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение: {e}")
    
    logging.warning(page)

    # Отправляем обновленный список курсов на нужной странице
    await show_courses(callback.message, page)


@dp.callback_query(lambda callback: callback.data.startswith("enroll_"))
async def enroll_course(callback: CallbackQuery):
    course_id = int(callback.data.split("_")[1])
    user_name = callback.from_user.full_name
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/signup",
            params={"course_id": course_id},
            json={"message": f"Пользователь {user_name} записался на курс {course_id}!", "user_name": user_name}
        )
        
        if response.status_code == 200:
            await callback.message.answer("Вы успешно записаны на курс!")
        else:
            await callback.message.answer("Произошла ошибка при записи на курс.")

async def main() -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    asyncio.run(main())
