import os
import asyncio
import logging
import random
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InputMediaPhoto, InlineKeyboardButton, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from PIL import Image, ImageDraw
from aiohttp import web  # <-- ВАЖНО: для работы на Render

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище состояний
status_messages = {}  # {chat_id: message_id}
boy_chat_id = None
chat_locks = {}       # <-- ЗАЩИТА от двойных нажатий (блокировки)

COLORS = {
    "green": (0, 200, 0),
    "yellow": (255, 220, 0),
    "orange": (255, 140, 0),
    "red": (220, 0, 0)
}

TEXTS = {
    "green": "💚 Готова общаться",
    "yellow": "🤔 Можно...",
    "orange": "😤 Раздражаюсь...",
    "red": "🔴 Обиделась!"
}

COMMENTS = {
    "green": [
        "💚 Ну наконец-то! Я уже заждалась...",
        "💚 Ладно, я готова тебя выслушать",
        "💚 У меня хорошее настроение, не испорти!",
    ],
    "yellow": [
        "🤨 можно да, чуть выебу",
        "😒 Будем или нет покажет время ",
        "🙄 набери закусимся, иномарка",
    ],
    "orange": [
        "😤 Ты меня уже раздражаешь...",
        "😒 Всё, я начинаю злиться",
        "😡 Серьёзно? Опять это?",
        "😤 Я уже на пределе",
    ],
    "red": [
        "😡 ВСЁ! Я ОБИДЕЛАСЬ!",
        "💢 НЕ БЕСИ МЕНЯ!",
        "😤 Всё, я устала. Отстань.",
        "💔 Ты меня довел. Поздравляю.",
        " Даже не Звони мне сейчас!",
    ]
}

def make_circle(color_name: str) -> BufferedInputFile:
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill=(*COLORS[color_name], 255))
    draw.ellipse([0, 0, size, size], outline=(255, 255, 255, 255), width=12)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename=f"{color_name}_circle.png")

def get_keyboard():
    return InlineKeyboardBuilder(
        [
            [InlineKeyboardButton(text="🟢 Зелёная", callback_data="green"),
             InlineKeyboardButton(text="🟡 Жёлтая", callback_data="yellow")],
            [InlineKeyboardButton(text="🟠 Оранжевая", callback_data="orange"),
             InlineKeyboardButton(text="🔴 Красная", callback_data="red")]
        ]
    ).as_markup()

async def get_lock(chat_id: int):
    """Возвращает асинхронную блокировку для конкретного чата"""
    if chat_id not in chat_locks:
        chat_locks[chat_id] = asyncio.Lock()
    return chat_locks[chat_id]

async def update_girl_photo(chat_id: int, color: str):
    """ГЛАВНАЯ ФУНКЦИЯ: Гарантирует ОДНО сообщение, даже при бешеных кликах"""
    lock = await get_lock(chat_id)
    
    # Блокируем выполнение для этого чата, пока не закончится обработка
    async with lock:
        msg_id = status_messages.get(chat_id)
        photo = make_circle(color)
        caption = TEXTS[color]
        kb = get_keyboard()

        if msg_id:
            try:
                await bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=msg_id,
                    media=InputMediaPhoto(media=photo, caption=caption),
                    reply_markup=kb
                )
                return  # Успех, выходим
            except Exception as e:
                err_str = str(e).lower()
                
                # ЕСЛИ СООБЩЕНИЕ НЕ ИЗМЕНИЛОСЬ (тот же цвет), просто игнорируем ошибку!
                if "not modified" in err_str:
                    logger.info(f"ℹ️ Сообщение не изменено (тот же статус), игнорируем.")
                    return
                
                logger.warning(f"⚠️ Редактирование не удалось ({e}). Пробую удалить и отправить заново.")
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    pass

        # Отправляем новое, только если редактирование реально провалилось
        try:
            photo = make_circle(color)
            sent = await bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                reply_markup=kb
            )
            status_messages[chat_id] = sent.message_id
            logger.info(f"📤 Отправлено новое фото (msg_id: {sent.message_id}) для {chat_id}")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка отправки фото: {e}")

@dp.message(Command("start_me"))
async def start_me(message: types.Message):
    global boy_chat_id
    boy_chat_id = message.chat.id
    await message.answer("✅ Твой ID сохранён! Теперь будешь получать уведомления о её настроении 😏")
    logger.info(f"💾 Сохранён ID парня: {message.chat.id}")

@dp.message(Command("start"))
async def start_girl(message: types.Message):
    await update_girl_photo(message.chat.id, "green")
    logger.info(f"🎬 Девушка запустила бота: {message.chat.id}")

@dp.callback_query(F.data.in_(["green", "yellow", "orange", "red"]))
async def on_color_change(callback: types.CallbackQuery):
    color = callback.data
    chat_id = callback.message.chat.id

    # 1. Обновляем фото (теперь это безопасно от двойных кликов)
    await update_girl_photo(chat_id, color)

    # 2. Отправляем саркастический комментарий парню
    if boy_chat_id:
        try:
            comment = random.choice(COMMENTS[color])
            await bot.send_message(chat_id=boy_chat_id, text=comment)
            logger.info(f"📩 Отправлен комментарий парню: {comment}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить сообщение парню: {e}")

    # 3. Убираем "часики"
    await callback.answer()

@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("🏓 Понг! Бот работает.")

# ==========================================
# ФИКС ДЛЯ RENDER: Фиктивный веб-сервер
# ==========================================
async def handle_health(request):
    return web.Response(text="Bot is running 🟢")

async def init_web_app():
    app = web.Application()
    app.router.add_get('/', handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Веб-сервер запущен на порту {port} (Render happy)")

async def main():
    logger.info("🚀 Запуск бота 'Светофор'...")
    # Запускаем веб-сервер и бота ОДНОВРЕМЕННО
    await asyncio.gather(
        init_web_app(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
