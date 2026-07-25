import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Токен из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище (в памяти)
users_data = {}

# File ID
PHOTOS = {
    "green": "AgACAgIAAxkBAAMyamShFiwxbpZhaRHxQDy5cBCwhG4AAo0aaxsrRyhLkpEGFvSl09wBAAMCAAN4AAM9BA",
    "yellow": "AgACAgIAAxkBAANOamSlZDv-G0hAjn9yrmt2nGoeOmsAAp4aaxsrRyhLAhFifg1Ip4UBAAMCAAN4AAM9BA",
    "orange": "AgACAgIAAxkBAAMIamSkh-AGoLkFbmdIsDwqwpmNC_gAApkaaxsrRyhLdv3Z62Xo3QIBAAMCAAN4AAM9BA",
    "red": "AgACAgIAAxkBAAM8amSiFvx67cKjR5PaoUHSVcWMBkEAAo4aaxsrRyhLd_4OSx02h0MBAAMCAAN4AAM9BA"
}

TEXTS = {
    "green": "🟢 Готова общаться",
    "yellow": "🟡 Думаю",
    "orange": "🟠 Почти готова",
    "red": "🔴 Не сейчас"
}

def get_status_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🟢 Зелёная", callback_data="green"),
        InlineKeyboardButton(text="🟡 Жёлтая", callback_data="yellow")
    )
    builder.row(
        InlineKeyboardButton(text="🟠 Оранжевая", callback_data="orange"),
        InlineKeyboardButton(text="🔴 Красная", callback_data="red")
    )
    return builder.as_markup()

@dp.message(Command("start_me"))
async def start_me(message: types.Message):
    users_data["boy_chat_id"] = message.chat.id
    await message.answer("✅ Ваш ID сохранён!")
    logger.info(f"Сохранён ID парня: {message.chat.id}")

@dp.message(Command("start"))
async def start_girl(message: types.Message):
    try:
        sent = await bot.send_photo(
            chat_id=message.chat.id,
            photo=PHOTOS["green"],
            caption="Выберите свой статус:",
            reply_markup=get_status_keyboard()
        )
        users_data[f"status_msg_{message.chat.id}"] = sent.message_id
        logger.info(f"Отправлено стартовое фото для {message.chat.id}")
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")
        await message.answer("❌ Ошибка. Попробуйте позже.")

@dp.callback_query(F.data.in_(["green", "yellow", "orange", "red"]))
async def change_status(callback: types.CallbackQuery):
    color = callback.data
    chat_id = callback.message.chat.id
    
    try:
        msg_id = users_data.get(f"status_msg_{chat_id}")
        
        # Пробуем отредактировать
        if msg_id:
            try:
                await bot.edit_message_media(
                    chat_id=chat_id,
                    message_id=msg_id,
                    media=types.InputMediaPhoto(
                        media=PHOTOS[color],
                        caption=TEXTS[color]
                    )
                )
                logger.info(f"Статус обновлён для {chat_id}: {color}")
            except Exception as e:
                logger.warning(f"Редактирование не удалось, отправляю новое: {e}")
                new_msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=PHOTOS[color],
                    caption=TEXTS[color],
                    reply_markup=get_status_keyboard()
                )
                users_data[f"status_msg_{chat_id}"] = new_msg.message_id
        
        # Уведомление парню
        boy_id = users_data.get("boy_chat_id")
        if boy_id:
            try:
                await bot.send_message(
                    chat_id=boy_id,
                    text=f"📱 Статус: {TEXTS[color]}"
                )
            except Exception as e:
                logger.error(f"Не отправлено уведомление: {e}")
        
        await callback.answer("✅", show_alert=False)
        
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("🏓 Понг! Бот работает.")

async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
