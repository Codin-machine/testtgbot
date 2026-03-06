"""
Telegram Mini App - Finance Tracker Bot
Backend: aiogram 3.x + aiohttp API
"""
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiohttp import web
import aiohttp
import aiosqlite

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
# GitHub Pages URL для Mini App
MINI_APP_URL = "https://yourusername.github.io/tgbot/"

# API сервер
API_HOST = "0.0.0.0"
API_PORT = 8080

DB_PATH = Path("data/finance.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== БАЗА ДАННЫХ ====================
class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(exist_ok=True)

    async def init(self):
        """Инициализация таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Пользователи
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0.0,
                    base_currency TEXT DEFAULT 'USD',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Транзакции
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Курсы валют
            await db.execute("""
                CREATE TABLE IF NOT EXISTS rates (
                    id INTEGER PRIMARY KEY,
                    base TEXT DEFAULT 'USD',
                    rates TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await db.commit()

    async def get_or_create_user(self, telegram_id: int, username: str, first_name: str):
        """Получить или создать пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id, balance, base_currency FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()

            if row:
                return {"id": row[0], "balance": row[1], "base_currency": row[2]}

            await db.execute(
                "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
                (telegram_id, username, first_name)
            )
            await db.commit()

            cursor = await db.execute(
                "SELECT id, balance, base_currency FROM users WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            return {"id": row[0], "balance": row[1], "base_currency": row[2]}

    async def add_transaction(self, user_id: int, tx_type: str, amount: float,
                              category: str = "", description: str = ""):
        """Добавить транзакцию"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO transactions (user_id, type, amount, category, description)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, tx_type, amount, category, description)
            )

            # Обновить баланс
            if tx_type == "income":
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE id = ?",
                    (amount, user_id)
                )
            else:
                await db.execute(
                    "UPDATE users SET balance = balance - ? WHERE id = ?",
                    (amount, user_id)
                )

            await db.commit()

    async def get_balance(self, user_id: int) -> float:
        """Получить баланс"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT balance FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0.0

    async def get_transactions(self, user_id: int, limit: int = 100) -> list:
        """Получить транзакции"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT id, type, amount, category, description, created_at
                   FROM transactions WHERE user_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit)
            )
            rows = await cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "type": r[1],
                    "amount": r[2],
                    "category": r[3],
                    "description": r[4],
                    "created_at": r[5]
                }
                for r in rows
            ]

    async def get_stats(self, user_id: int) -> dict:
        """Получить статистику"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """SELECT category, SUM(amount) FROM transactions
                   WHERE user_id = ? AND type = 'income'
                   GROUP BY category""",
                (user_id,)
            )
            income = {r[0]: r[1] for r in await cursor.fetchall()}

            cursor = await db.execute(
                """SELECT category, SUM(amount) FROM transactions
                   WHERE user_id = ? AND type = 'expense'
                   GROUP BY category""",
                (user_id,)
            )
            expenses = {r[0]: r[1] for r in await cursor.fetchall()}

            return {"income": income, "expenses": expenses}

    async def update_currency(self, user_id: int, currency: str):
        """Обновить базовую валюту"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET base_currency = ? WHERE id = ?",
                (currency, user_id)
            )
            await db.commit()

    async def get_currency(self, user_id: int) -> str:
        """Получить базовую валюту"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT base_currency FROM users WHERE id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else "USD"

    async def save_rates(self, rates: dict, base: str = "USD"):
        """Сохранить курсы валют"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO rates (id, base, rates, updated_at)
                   VALUES (1, ?, ?, ?)""",
                (base, json.dumps(rates), datetime.now().isoformat())
            )
            await db.commit()

    async def get_rates(self) -> dict:
        """Получить сохранённые курсы"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT rates, updated_at FROM rates WHERE id = 1")
            row = await cursor.fetchone()
            if row:
                return {"rates": json.loads(row[0]), "updated_at": row[1]}
            return None


# ==================== HTTP API ====================
class WebAPI:
    def __init__(self, db: Database):
        self.db = db
        self.app = web.Application()
        self.app.router.add_post("/api/auth", self.auth)
        self.app.router.add_get("/api/balance/{user_id}", self.get_balance)
        self.app.router.add_post("/api/transaction", self.add_transaction)
        self.app.router.add_get("/api/transactions/{user_id}", self.get_transactions)
        self.app.router.add_get("/api/stats/{user_id}", self.get_stats)
        self.app.router.add_post("/api/currency/{user_id}", self.update_currency)
        self.app.router.add_get("/api/rates", self.get_rates)
        self.app.router.add_post("/api/rates/fetch", self.fetch_rates)

    async def auth(self, request: web.Request) -> web.Response:
        """Аутентификация"""
        data = await request.json()
        telegram_id = data.get("telegram_id")
        username = data.get("username", "")
        first_name = data.get("first_name", "")

        user = await self.db.get_or_create_user(telegram_id, username, first_name)
        return web.json_response(user)

    async def get_balance(self, request: web.Request) -> web.Response:
        """Баланс"""
        user_id = int(request.match_info["user_id"])
        balance = await self.db.get_balance(user_id)
        currency = await self.db.get_currency(user_id)
        return web.json_response({"balance": balance, "currency": currency})

    async def add_transaction(self, request: web.Request) -> web.Response:
        """Добавить транзакцию"""
        data = await request.json()
        user_id = data.get("user_id")
        tx_type = data.get("type")
        amount = float(data.get("amount", 0))
        category = data.get("category", "")
        description = data.get("description", "")

        if tx_type not in ["income", "expense"]:
            return web.json_response({"error": "Invalid type"}, status=400)

        await self.db.add_transaction(user_id, tx_type, amount, category, description)
        balance = await self.db.get_balance(user_id)

        return web.json_response({"success": True, "balance": balance})

    async def get_transactions(self, request: web.Request) -> web.Response:
        """Транзакции"""
        user_id = int(request.match_info["user_id"])
        transactions = await self.db.get_transactions(user_id)
        return web.json_response({"transactions": transactions})

    async def get_stats(self, request: web.Request) -> web.Response:
        """Статистика"""
        user_id = int(request.match_info["user_id"])
        stats = await self.db.get_stats(user_id)
        return web.json_response(stats)

    async def update_currency(self, request: web.Request) -> web.Response:
        """Обновить валюту"""
        user_id = int(request.match_info["user_id"])
        data = await request.json()
        currency = data.get("currency", "USD")
        await self.db.update_currency(user_id, currency)
        return web.json_response({"success": True, "currency": currency})

    async def get_rates(self, request: web.Request) -> web.Response:
        """Сохранённые курсы"""
        rates = await self.db.get_rates()
        if rates:
            return web.json_response(rates)
        return web.json_response({"error": "No rates cached"}, status=404)

    async def fetch_rates(self, request: web.Request) -> web.Response:
        """Запросить свежие курсы"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.exchangerate-api.com/v4/latest/USD"
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        await self.db.save_rates(data.get("rates", {}))
                        return web.json_response({
                            "success": True,
                            "rates": data.get("rates", {}),
                            "updated_at": data.get("date", "")
                        })
        except Exception as e:
            logger.error(f"Failed to fetch rates: {e}")

        return web.json_response({"error": "Failed to fetch rates"}, status=500)

    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, API_HOST, API_PORT)
        await site.start()
        logger.info(f"🌐 API запущен на http://{API_HOST}:{API_PORT}")


# ==================== TELEGRAM BOT ====================
async def main():
    # Инициализация БД
    db = Database(DB_PATH)
    await db.init()

    # Запуск API
    api = WebAPI(db)
    await api.start()

    # Бот
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
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
        await message.answer(
            "📖 <b>Commands:</b>\n\n"
            "/start - Open Finance Tracker\n"
            "/help - Show this help"
        )

    @dp.message()
    async def echo_handler(message: types.Message):
        if message.web_app_data:
            await message.answer(f"📊 Received data from Mini App")

    logger.info("🤖 Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
