import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import create_tables
from handlers import start, registration, order, admin, common

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(registration.router)
dp.include_router(order.router)
dp.include_router(admin.router)
dp.include_router(common.router)

async def main():
    create_tables()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
