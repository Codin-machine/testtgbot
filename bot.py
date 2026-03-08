"""
Telegram Mini App Bot для управления финансами
Использует aiogram 3.x с асинхронным подходом
"""

import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo


# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-username.github.io/finance-mini-app/")

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# =============================================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =============================================================================
# КЛАВИАТУРЫ
# =============================================================================
def get_main_keyboard() -> types.ReplyKeyboardMarkup:
    """
    Создаёт основную клавиатуру с кнопкой для открытия Mini App.
    Кнопка использует WebAppInfo для запуска Mini App внутри Telegram.
    """
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(
                    text="💰 Открыть финансы",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ]
        ],
        resize_keyboard=True,  # Адаптировать размер клавиатуры
        one_time_keyboard=False  # Не скрывать после нажатия
    )
    return keyboard

# =============================================================================
# ОБРАБОТЧИКИ (HANDLERS)
# =============================================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    await message.answer(
        text="Привет! Я твой персональный финансовый помощник. "
             "Нажми на кнопку ниже, чтобы управлять своими доходами и расходами.",
        reply_markup=get_main_keyboard()
    )

# =============================================================================
# ЗАПУСК БОТА
# =============================================================================
async def main() -> None:
    """
    Основная функция запуска бота.
    Удаляет вебхуки и запускает polling.
    """
    await bot.delete_webhook(drop_pending_updates=True)
    print(f"🤖 Бот запущен! Mini App URL: {MINI_APP_URL}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
