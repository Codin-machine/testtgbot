"""
Telegram Mini App - Finance Tracker Bot
Backend на aiogram 3.x
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8407776257:AAFDD53rG42kJGCv8q7JLNS3_h1PqEZe7Uk"
# URL замените на ваш ngrok URL (https://xxxx-xxxx.ngrok.io)
MINI_APP_URL = "https://codin-machine.github.io/testtgbot/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== TELEGRAM BOT ====================
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        """Обработка команды /start"""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💰 Open Finance Tracker",
                        web_app=WebAppInfo(url=MINI_APP_URL)
                    )
                ]
            ]
        )

        await message.answer(
            "👋 Welcome to <b>Finance Tracker</b>!\n\n"
            "Track your income and expenses, analyze your finances.\n\n"
            "Click the button below to open the app:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        """Справка"""
        await message.answer(
            "📖 <b>Commands:</b>\n\n"
            "/start - Open Finance Tracker\n"
            "/help - Show this help message"
        )

    logger.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
