import asyncio
from datetime import datetime
import logging
from typing import List
import httpx
import redis

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from config import (
    TELEGRAM_BOT_TOKEN,
    API_GATEWAY_URL,
    REDIS_HOST,
    REDIS_PORT
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PAGE_COUNT = 5

dp = Dispatcher()
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

redis_client = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=0)

start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Курсы")],
        [KeyboardButton(text="Мои курсы")],
    ],
    resize_keyboard=True
)


def got_exception_handler(func):
    async def wrapper(msg_clbck: Message | CallbackQuery, *args) -> None:
        """
        Обработчик исключений в функциях обработки сообщений и обратных вызовов

        Перехватывает исключения и отправляет пользователю сообщение об ошибке.
        Обрабатываются такие исключения как:
            1.Ошибка подключения
            2.Таймаут
            3.Общие ошибки.
        """
        try:
            return await func(msg_clbck, *args)
        except httpx.ConnectError:
            await _handle_error(msg_clbck, "Ошибка подключения к серверу!")
        except httpx.ReadTimeout:
            await _handle_error(msg_clbck, "Сервер слишком долго отвечает!")
        except Exception as e:
            logging.error(f"Произошла ошибка: {e}")
            await _handle_error(
                msg_clbck,
                "Что-то пошло не так. Попробуйте позже."
            )
    
    return wrapper


async def _handle_error(
    msg_clbck: Message | CallbackQuery, 
    message: str
) -> None:
    """
    Обработчик ошибок.

    Если сообщение или обратный вызов вызывает ошибку, отправляется
    информативное сообщение пользователю. Логи записываются в консоль.
    """
    logging.error(message)
    if isinstance(msg_clbck, Message):
        await msg_clbck.answer(message)
    elif isinstance(msg_clbck, CallbackQuery):
        await msg_clbck.answer(message)
        await msg_clbck.message.edit_text(message)


async def fetch_data_from_api(url: str, params: dict = None) -> dict:
    """
    Обработчик для получения данных с API
    
    Выполняет HTTP GET запрос к указанному URL с переданными параметрами.
    Возвращает результат в формате JSON или пустой словарь в случае ошибки.

    Args:
        url (str): URL для выполнения запроса.
        params (dict, optional): Параметры запроса.

    Returns:
        dict: Ответ от API в формате JSON.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка API: {response.status_code}")
                return {}
    except Exception as e:
        logger.error(f"Ошибка запроса: {e}")
        return {}


def get_courses_from_cache(user_id: int) -> int:
    """
    Получение текущей страницы курсов из кеша
    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        int: Номер текущей страницы, либо 0, если данные отсутствуют.
    """
    page = redis_client.get(f"user:{user_id}:course_page")
    return int(page) if page else 0


def set_courses_page_in_cache(user_id: int, page: int) -> None:
    """
    Установить текущую страницу курсов в кеш
    
    Args:
        user_id (int): Идентификатор пользователя.
        page (int): Номер текущей страницы.
    """
    redis_client.set(f"user:{user_id}:course_page", page)


async def handle_courses_keyboard(
    courses: List[dict], 
    page: int
) -> InlineKeyboardMarkup:
    """
    Формирование клавиатуры для навигации по курсам.

    Создает кнопки с названиями курсов и кнопки для переключения страниц.

    Args:
        courses (List[dict]): Список курсов.
        page (int): Номер текущей страницы.

    Returns:
        InlineKeyboardMarkup: Клавиатура с курсами и навигацией.
    """
    total_pages = (len(courses) - 1) // PAGE_COUNT + 1

    inline_keyboard = [
        [
            InlineKeyboardButton(
                text=course["name"][:30], 
                callback_data=f"course_{course['id']}"
            )
        ]
        for course in courses[page * PAGE_COUNT: (page + 1) * PAGE_COUNT]
    ]

    nav_buttons = [
        InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_page") 
        if page > 0
        else None,

        InlineKeyboardButton(text="Вперед ➡️", callback_data="next_page") 
        if page < total_pages - 1 
        else None,
    ]

    nav_buttons = list(filter(None, nav_buttons))

    if nav_buttons:
        inline_keyboard.append(nav_buttons)

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    
    return keyboard


async def delete_old_message(chat_id, message) -> None:
    """
    Удаление предыдущего сообщения пользователя из кеша.

    Args:
        chat_id (int): Идентификатор чата.
        message (Message): Объект текущего сообщения.
    """
    if redis_client.exists(f"user:{chat_id}:message_id"):
        old_message_id = int(redis_client.get(f"user:{chat_id}:message_id"))
        try:
            await message.bot.delete_message(chat_id, old_message_id)
        except Exception as delete_error:
            logging.warning(
                f"Ошибка удаления старого сообщения: {delete_error}"
            )


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды приветствия
    
    Приветствует пользователя.
    Предлагает использовать бота для получения информации о курсах.
    """
    await message.answer(
        f"Привет, {html.bold(message.from_user.full_name)}!\n"
        f"Используй команду /courses или кнопку ниже, чтобы"
        f"просмотреть доступные курсы.",
        reply_markup=start_keyboard
    )


@dp.message(lambda message: message.text == "Курсы")
@dp.message(Command("courses"))
@got_exception_handler
async def show_courses(message: Message, page: int = 0) -> None:
    """
    Отображение списка доступных курсов.

    Загружает курсы с API, кэширует текущую страницу.
    Формирует клавиатуру для выбора курса.

    Args:
        message (Message): Сообщение пользователя.
        page (int, optional): Номер страницы. По умолчанию 0.
    """
    user_id = message.chat.id
    courses = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/courses", 
        params={"user_id": user_id}
    )

    if courses:
        set_courses_page_in_cache(user_id, page)
        await delete_old_message(user_id, message)
        keyboard = await handle_courses_keyboard(courses, page)
        send_message = await message.answer(
            "Выберите курс:", 
            reply_markup=keyboard
        )

        redis_client.set(
            f"user:{user_id}:message_id", 
            send_message.message_id
        )
    else:
        await message.answer("Ошибка при получении курсов")


@dp.callback_query(
    lambda callback: callback.data in ["prev_page", "next_page"]
)
async def change_page(callback: CallbackQuery) -> None:
    """
    Переключение между страницами курсов.

    Перемещается по страницам в зависимости от нажатой кнопки.
    """
    user_id = callback.message.chat.id
    current_page = get_courses_from_cache(user_id)

    if callback.data == "prev_page":
        page = max(current_page - 1, 0)
    elif callback.data == "next_page":
        page = current_page + 1

    await show_courses(callback.message, page)


@dp.callback_query(lambda callback: callback.data.startswith("course_"))
@got_exception_handler
async def show_course_details(callback: CallbackQuery) -> None:  
    """
    Отображение информации о выбранном курсе.

    Загружает данные курса с API.
    Отправляет загруженные данные пользователю с клавиатурой действий.
    """  
    course_id = callback.data.split("_")[1]
    course = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/courses/{course_id}"
    )
    course = course[0]
    if course:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Записаться на курс", 
                        callback_data=f"enroll_{course_id}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Назад", 
                        callback_data="back_to_courses"
                    )
                ]
            ]
        )
        await callback.message.answer(
            f"Курс: {course['name']}\n"
            f"Описание: {course['description']}\n"
            f"Стоимость: {course['price']}",
            reply_markup=keyboard,
        )
    else:
        await callback.message.answer("Ошибка при получении данных курса.")


@dp.callback_query(lambda callback: callback.data == "back_to_courses")
async def back_to_courses(callback: CallbackQuery) -> None:
    """
    Возврат к списку курсов.

    Загружает и отображает текущую страницу курсов из кеша.
    """
    page = get_courses_from_cache(callback.message.chat.id)
    await show_courses(callback.message, page)


@dp.callback_query(lambda callback: callback.data.startswith("enroll_"))
@got_exception_handler
async def enroll_course(callback: CallbackQuery) -> None:
    """
    Получение списка дат для записи на выбранный курс.

    Отображает пользователю доступные даты для записи.
    """
    course_id = int(callback.data.split("_")[1])
    dates = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/courses/{course_id}/schedule"
    )

    if dates:
        date_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=date, 
                        callback_data=f"date_{course_id}_{date}"
                    )
                ]
                for date in dates["start_date"]
            ] 
            + [
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data=f"course_{course_id}"
                    )
                ]
            ]
        )
        await callback.message.edit_text(
            "📅 Выберите дату:", reply_markup=date_keyboard
        )
    else:
        await callback.message.edit_text("Ошибка при получении доступных дат.")


@dp.callback_query(lambda callback: callback.data.startswith("date_"))
@got_exception_handler
async def select_date(callback: CallbackQuery) -> None:
    """
    Отображение доступного времени для выбранной даты.

    Показывает кнопки с выбором времени для записи на курс.
    """
    _, course_id, selected_date = callback.data.split("_")
    times = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/courses/{course_id}/times", 
        params={"date": selected_date}
    )

    formatted_times = [
        (
            datetime.strptime(
                time['start_time'], "%H:%M:%S"
            ).strftime("%H:%M"), 
            time['id']
        ) 
        for time in times["times"]
    ]
    if times:
        time_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=time[0],
                        callback_data=f"time_{course_id}_{time[1]}"
                    )
                ]
                for time in formatted_times
            ] 
            + [
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад", 
                        callback_data=f"enroll_{course_id}"
                    )
                ]
            ]
        )
        await callback.message.edit_text(
            "⏰ Выберите время:", 
            reply_markup=time_keyboard
        )
    else:
        await callback.message.edit_text(
            "Ошибка при получении доступного времени."
        )


@dp.callback_query(lambda callback: callback.data.startswith("time_"))
@got_exception_handler
async def confirm_selection(callback: CallbackQuery) -> None:
    """
    Подтверждение выбора курса, даты и времени.

    Отображает информацию о курсе, дате начала, окончании и времени занятий.
    """   
    _, course_id, schedule_id = callback.data.split("_") 

    course = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/courses_schedule/{schedule_id}"
    )
    
    start_time = course['start_time']
    end_time = course['end_time']

    formatted_start_time = (
        datetime.strptime(start_time, "%H:%M:%S").
        strftime("%H:%M")
    )
    formatted_end_time = (
        datetime.strptime(end_time, "%H:%M:%S").
        strftime("%H:%M")
    )
    
    confirm_text = (
        f"Вы выбрали курс: {course['course_name']}\n"
        f"Дата начала: {course['start_date']}\n"
        f"Дата окончания: {course['end_date']}\n"
        f"Время занятия (по Екб): "
        f"{formatted_start_time} - {formatted_end_time}\n"
        "Подтвердите запись."
    )
    
    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить", 
                    callback_data=f"confirm_{course_id}_{schedule_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", 
                    callback_data=f"enroll_{course_id}"
                )
            ]
        ]
    )

    await callback.message.answer(confirm_text, reply_markup=confirm_keyboard)


@dp.callback_query(lambda callback: callback.data.startswith("confirm_"))
@got_exception_handler
async def finalize_enrollment(callback: CallbackQuery) -> None:
    """
    Ообработчик подтверждения записи на курс
    
    Отправляет данные на API для завершения записи.
    Проверяет наличие дублирующих записей.
    """
    _, course_id, schedule_id = callback.data.split("_")
    user_id = callback.from_user.id
    course_id = int(course_id)
    enrolls = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/enroll", 
        params={"user_id": user_id}
    )    

    if any(enroll["course_id"] == course_id for enroll in enrolls):
        await callback.message.answer("Вы уже записаны на этот курс.")
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/enroll",  
            json={
                "user_id": user_id,
                "course_id": course_id,  
                "schedule_id": schedule_id   
            }
        )

        if response.status_code == 200:
            await callback.message.edit_text(
                "Вы успешно записаны на курс! "
                "Мы свяжемся с вами в ближайшее время." 
                "Так же за час перед началом курса вам придет уведомление."
            )
        else:
            await callback.message.edit_text(
                "Произошла ошибка при записи на курс."
            )
   

@dp.message(lambda message: message.text == "Мои курсы")
@dp.message(Command('enrolled'))
@got_exception_handler
async def get_enroll_for_user(message: Message, **kwargs) -> None:
    """
    Получение списка курсов, на которые записан пользователь.

    Отображает список с кнопками для просмотра деталей каждого курса.
    """
    user_id = message.chat.id
    enrolls = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/enroll", 
        params={"user_id": user_id}
    )
    if not enrolls:
        await message.answer("Вы пока не записаны на курсы.")
        return
    inline_keyboard = [
            [
                InlineKeyboardButton(
                    text=f"{enroll["course_name"][:30]}",
                    callback_data=(
                        f"courseEnroll_{enroll['course_id']}_{enroll['id']}"
                    )
                )
            ]
            for enroll in enrolls
        ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    await message.answer("Выберите курс:", reply_markup=keyboard)


@dp.callback_query(lambda callback: callback.data.startswith("courseEnroll_"))
@got_exception_handler
async def show_enroll_course_details(callback: CallbackQuery) -> None: 
    """
    Просмотр подробной информации о записанном курсе.

    Отображает название, описание, стоимость и кнопки:
        1.Отписки 
        2.Возврата 
    """   
    _, course_id, enroll_id = callback.data.split("_")

    response = await fetch_data_from_api(
        f"{API_GATEWAY_URL}/courses/{course_id}"
    )
    course = response[0]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отписаться", callback_data=f"unsubscribe_{enroll_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад", callback_data="back_to_enroll"
                )
            ]
        ]
    )
    
    await callback.message.answer(
        f"Курс: {course['name']}\n"
        f"Описание: {course['description']}"
        f"Стоимость: {course['price']}\n",
        reply_markup=keyboard
    )


@dp.callback_query(lambda callback: callback.data == "back_to_enroll")
async def back_to_enrolls(callback: CallbackQuery) -> None:
    """
    Возврат к списку записанных курсов.

    Повторно вызывает обработчик отображения записанных курсов.
    """
    await get_enroll_for_user(callback.message)


@dp.callback_query(lambda callback: callback.data.startswith("unsubscribe_"))
@got_exception_handler
async def unsubscribe_course(callback: CallbackQuery) -> None: 
    """
    Отписка от курса.

    Удаляет запись на курс с сервера.
    Уведомляет пользователя об успешной отписке.
    """   
    enroll_id = callback.data.split("_")[1]
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{API_GATEWAY_URL}/enroll/{enroll_id}"
            )
            
            if response.status_code == 200:
                await callback.message.answer(
                    "Вы успешно отписались от курса"
                )
            else:
                await callback.message.answer(
                    "Ошибка при попытке отписаться от курса"
                )
                
    except Exception:
        await callback.message.answer(
            "Что-то пошло не так. Попробуйте позже."
        )


async def send_notification_to_user(schedule_id: int, course_id: int) -> None:
    """
    Уведомление пользователя о начале курса.

    Отправляет сообщение всем записанным пользователям за час до начала курса.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_GATEWAY_URL}/courses/{course_id}"
            )
            course_name = response.json()[0]["name"]
            response = await client.get(
                f"{API_GATEWAY_URL}/enroll/{schedule_id}"
            )
            users = response.json()["users"]
        message = f"Ровно через час начнется занятие на курсе: {course_name}"
        for user in users:    
            await bot.send_message(
                user, message, parse_mode=ParseMode.MARKDOWN
            )
    except Exception as e:
        logging.error(f"Error sending message: {e}")


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        level=logging.INFO
    )
    asyncio.run(main())
